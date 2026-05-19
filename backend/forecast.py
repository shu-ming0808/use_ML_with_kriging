from __future__ import annotations

import json
from datetime import timedelta

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error

try:
    from pykrige.ok import OrdinaryKriging
except ImportError:
    OrdinaryKriging = None


def _idw_predict(train_xy: np.ndarray, train_y: np.ndarray, target_xy: np.ndarray, k: int = 8):
    tree = cKDTree(train_xy)
    k = min(k, len(train_xy))
    distances, indexes = tree.query(target_xy, k=k)

    if k == 1:
        distances = distances[:, None]
        indexes = indexes[:, None]

    distances = np.maximum(distances, 1e-9)
    weights = 1.0 / np.square(distances)
    weights = weights / weights.sum(axis=1, keepdims=True)
    predictions = np.sum(train_y[indexes] * weights, axis=1)
    variance = np.average(np.square(train_y[indexes] - predictions[:, None]), axis=1, weights=weights)
    return predictions, variance


def _kriging_predict(train_xy: np.ndarray, train_y: np.ndarray, target_xy: np.ndarray):
    if OrdinaryKriging is None or len(train_xy) < 4:
        predictions, variance = _idw_predict(train_xy, train_y, target_xy)
        return predictions, variance, "IDW fallback"

    try:
        model = OrdinaryKriging(
            train_xy[:, 0],
            train_xy[:, 1],
            train_y,
            variogram_model="spherical",
            verbose=False,
            enable_plotting=False,
        )
        predictions, variance = model.execute("points", target_xy[:, 0], target_xy[:, 1])
        return np.asarray(predictions, dtype=float), np.asarray(variance, dtype=float), "OrdinaryKriging"
    except Exception:
        predictions, variance = _idw_predict(train_xy, train_y, target_xy)
        return predictions, variance, "IDW fallback"


def _select_ar_lag(series: pd.Series, max_lag: int) -> tuple[int, float]:
    values = series.dropna().astype(float).to_numpy()
    max_lag = min(max_lag, max(1, len(values) // 3))
    if len(values) < 6:
        return 1, float(values[-1]) if len(values) else 0.0

    best_lag = 1
    best_rmse = float("inf")
    for lag in range(1, max_lag + 1):
        x_rows = []
        y_rows = []
        for idx in range(lag, len(values)):
            x_rows.append(values[idx - lag:idx])
            y_rows.append(values[idx])

        if len(x_rows) < 3:
            continue

        x = np.asarray(x_rows)
        y = np.asarray(y_rows)
        split = max(1, int(len(y) * 0.8))
        model = LinearRegression()
        model.fit(x[:split], y[:split])
        pred = model.predict(x[split:]) if split < len(y) else model.predict(x[:split])
        truth = y[split:] if split < len(y) else y[:split]
        rmse = mean_squared_error(truth, pred) ** 0.5
        if rmse < best_rmse:
            best_rmse = rmse
            best_lag = lag

    return best_lag, best_rmse


def _forecast_ar(series: pd.Series, steps: int, max_lag: int) -> tuple[list[float], dict]:
    values = series.dropna().astype(float).to_numpy()
    if len(values) == 0:
        return [0.0] * steps, {"lag": 1, "rmse": None, "fallback": "empty_series"}
    if len(values) < 6:
        return [float(values[-1])] * steps, {"lag": 1, "rmse": None, "fallback": "last_value"}

    lag, rmse = _select_ar_lag(series, max_lag)
    x_rows = []
    y_rows = []
    for idx in range(lag, len(values)):
        x_rows.append(values[idx - lag:idx])
        y_rows.append(values[idx])

    model = LinearRegression()
    model.fit(np.asarray(x_rows), np.asarray(y_rows))

    history = values.tolist()
    output = []
    for _ in range(steps):
        x = np.asarray(history[-lag:]).reshape(1, -1)
        next_value = float(model.predict(x)[0])
        history.append(next_value)
        output.append(next_value)

    return output, {"lag": lag, "rmse": rmse}


def build_forecast_rows(df: pd.DataFrame, variable: str, hours: int, ar_max_lag: int) -> list[dict]:
    if df.empty:
        return []

    df = df.dropna(subset=["lat", "lon", "datetime", "value"]).copy()
    df["datetime"] = pd.to_datetime(df["datetime"])
    latest_time = df["datetime"].max()
    latest = df[df["datetime"] == latest_time].copy()

    train_xy = latest[["lon", "lat"]].to_numpy(dtype=float)
    train_y = latest["value"].to_numpy(dtype=float)
    target_xy = train_xy.copy()

    kriging_pred, kriging_var, kriging_method = _kriging_predict(train_xy, train_y, target_xy)

    ml = RandomForestRegressor(n_estimators=150, random_state=42, min_samples_leaf=2)
    spatial_features = latest[["lon", "lat"]].to_numpy(dtype=float)
    ml.fit(spatial_features, train_y)
    ml_pred = ml.predict(target_xy)

    scaled_var = kriging_var / max(float(np.max(kriging_var)), 1e-9)
    fusion_weight = np.clip(scaled_var, 0.0, 1.0)
    fusion_pred = fusion_weight * ml_pred + (1.0 - fusion_weight) * kriging_pred

    station_ar = {}
    for station_id, group in df.groupby("station_id"):
        ordered = group.sort_values("datetime")
        station_ar[station_id] = _forecast_ar(ordered["value"], hours, ar_max_lag)

    rows = []
    for station_idx, row in latest.reset_index(drop=True).iterrows():
        ar_values, ar_info = station_ar.get(row["station_id"], ([float(fusion_pred[station_idx])] * hours, {"lag": 1}))

        for step in range(hours):
            target_time = latest_time + timedelta(hours=step + 1)
            rows.append(
                {
                    "target_datetime": target_time.to_pydatetime(),
                    "lat": float(row["lat"]),
                    "lon": float(row["lon"]),
                    "variable_name": variable,
                    "kriging_pred": float(kriging_pred[station_idx]),
                    "ml_pred": float(ml_pred[station_idx]),
                    "fusion_pred": float(fusion_pred[station_idx]),
                    "ar_pred": float(ar_values[step]),
                    "kriging_variance": float(kriging_var[station_idx]),
                    "model_name": f"{kriging_method}+RandomForest+AutoAR",
                    "model_info": json.dumps(
                        {
                            "kriging_method": kriging_method,
                            "ar": ar_info,
                        },
                        ensure_ascii=False,
                    ),
                }
            )

    return rows
