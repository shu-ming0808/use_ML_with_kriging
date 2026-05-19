from __future__ import annotations

from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from config import settings
from db import read_observations, read_predictions, upsert_predictions
from forecast import build_forecast_rows


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"

app = Flask(__name__, static_folder=str(FRONTEND), static_url_path="")


@app.get("/")
def index():
    return send_from_directory(FRONTEND, "index.html")


@app.get("/api/health")
def health():
    return jsonify({"ok": True, "database": settings.db_name})


@app.post("/api/forecast/run")
def run_forecast():
    variable = request.json.get("variable", settings.forecast_variable) if request.is_json else settings.forecast_variable
    hours = int(request.json.get("hours", settings.forecast_hours)) if request.is_json else settings.forecast_hours
    training_hours = int(request.json.get("training_hours", settings.training_hours)) if request.is_json else settings.training_hours
    df = read_observations(variable, limit_hours=training_hours)
    rows = build_forecast_rows(df, variable, hours, settings.ar_max_lag)
    affected = upsert_predictions(rows)
    return jsonify(
        {
            "variable": variable,
            "training_hours": training_hours,
            "forecast_hours": hours,
            "rows": len(rows),
            "affected": affected,
        }
    )


@app.get("/api/predictions")
def predictions():
    variable = request.args.get("variable", settings.forecast_variable)
    df = read_predictions(variable)
    if df.empty:
        return jsonify({"variable": variable, "times": [], "points": []})

    df["target_datetime"] = df["target_datetime"].astype(str)
    return jsonify(
        {
            "variable": variable,
            "times": sorted(df["target_datetime"].unique().tolist()),
            "points": df.to_dict(orient="records"),
        }
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
