from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import geopandas as gpd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from shapely import make_valid
from scipy.spatial import cKDTree


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from db import read_predictions


BOUNDS = {
    "lon_min": 119.0,
    "lon_max": 123.0,
    "lat_min": 21.5,
    "lat_max": 25.7,
}


def choose_value_column(df: pd.DataFrame, preferred: str) -> str:
    candidates = (
        [preferred, "fusion_pred", "fixed_half_pred", "ml_pred", "kriging_pred"]
        if preferred != "auto"
        else ["fusion_pred", "fixed_half_pred", "ml_pred", "kriging_pred", "ar_pred"]
    )
    for column in candidates:
        if column in df.columns and df[column].notna().any():
            return column
    raise ValueError("No usable prediction column found.")


def idw_grid(points: pd.DataFrame, value_column: str, grid_size: int = 180):
    x = points["lon"].to_numpy(float)
    y = points["lat"].to_numpy(float)
    z = points[value_column].to_numpy(float)
    grid_x = np.linspace(BOUNDS["lon_min"], BOUNDS["lon_max"], grid_size)
    grid_y = np.linspace(BOUNDS["lat_min"], BOUNDS["lat_max"], grid_size)
    xx, yy = np.meshgrid(grid_x, grid_y)

    tree = cKDTree(np.c_[x, y])
    distances, indexes = tree.query(np.c_[xx.ravel(), yy.ravel()], k=min(8, len(points)))
    distances = np.maximum(distances, 1e-9)
    weights = 1.0 / distances**2
    weights = weights / weights.sum(axis=1, keepdims=True)
    grid_z = np.sum(z[indexes] * weights, axis=1).reshape(xx.shape)
    return grid_x, grid_y, xx, yy, grid_z


def make_land_mask(xx: np.ndarray, yy: np.ndarray, boundary: gpd.GeoDataFrame) -> np.ndarray:
    grid_points = gpd.GeoSeries(gpd.points_from_xy(xx.ravel(), yy.ravel()), crs="EPSG:4326")
    return grid_points.within(boundary.geometry.union_all()).to_numpy().reshape(xx.shape)


def mask_grid_to_boundary(grid_z: np.ndarray, land_mask: np.ndarray) -> np.ndarray:
    return np.where(land_mask, grid_z, np.nan)


def read_boundary(boundary_path: Path) -> gpd.GeoDataFrame:
    boundary = gpd.read_file(boundary_path, on_invalid="fix").to_crs(epsg=4326)
    boundary = boundary[boundary.geometry.notna()].copy()
    if "COUNTYNAME" in boundary.columns:
        boundary = boundary.drop_duplicates(subset=["COUNTYNAME"])
    boundary["geometry"] = boundary.geometry.map(make_valid)
    boundary = boundary[~boundary.geometry.is_empty].copy()
    land = boundary.geometry.union_all()
    return gpd.GeoDataFrame({"name": ["Taiwan land"]}, geometry=[land], crs="EPSG:4326")


def render_frames(
    variable: str,
    value_column: str,
    boundary_path: Path,
    output_dir: Path,
    max_frames: int | None,
    clean_output: bool,
) -> None:
    predictions = read_predictions(variable)
    if predictions.empty:
        raise ValueError(f"No predictions found for variable={variable}")

    predictions["target_datetime"] = pd.to_datetime(predictions["target_datetime"])
    value_column = choose_value_column(predictions, value_column)
    predictions = predictions.dropna(subset=["lat", "lon", value_column]).copy()

    boundary = read_boundary(boundary_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    if clean_output:
        for old_frame in output_dir.glob("frame_*.png"):
            old_frame.unlink()

    grouped_predictions = dict(tuple(predictions.groupby("target_datetime", sort=True)))
    times = sorted(grouped_predictions)
    if max_frames is not None:
        times = times[:max_frames]

    vmin = float(predictions[value_column].quantile(0.02))
    vmax = float(predictions[value_column].quantile(0.98))
    frames = []
    land_mask = None

    for index, target_time in enumerate(times):
        frame_df = grouped_predictions[target_time].copy()
        if len(frame_df) < 3:
            continue

        grid_x, grid_y, xx, yy, grid_z = idw_grid(frame_df, value_column=value_column)
        if land_mask is None:
            land_mask = make_land_mask(xx, yy, boundary)
        masked_grid_z = mask_grid_to_boundary(grid_z, land_mask)

        fig, ax = plt.subplots(figsize=(7.2, 8), dpi=140)
        boundary.plot(ax=ax, color="#cfcfcf", edgecolor="none", zorder=1)
        ax.imshow(
            masked_grid_z,
            extent=[grid_x.min(), grid_x.max(), grid_y.min(), grid_y.max()],
            origin="lower",
            cmap="turbo",
            alpha=0.72,
            vmin=vmin,
            vmax=vmax,
            zorder=2,
        )
        boundary.boundary.plot(ax=ax, color="black", linewidth=1.05, zorder=4)
        ax.scatter(
            frame_df["lon"],
            frame_df["lat"],
            s=7,
            c=frame_df[value_column],
            cmap="turbo",
            vmin=vmin,
            vmax=vmax,
            edgecolors="none",
            linewidths=0,
            alpha=1.0,
            zorder=5,
        )
        ax.set_xlim(BOUNDS["lon_min"], BOUNDS["lon_max"])
        ax.set_ylim(BOUNDS["lat_min"], BOUNDS["lat_max"])
        ax.set_aspect("equal", adjustable="box")
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        ax.grid(True, color="#9aa0a6", alpha=0.35, linewidth=0.6)
        ax.set_title(f"{variable} prediction surface", fontsize=12, pad=8)
        ax.text(
            0.02,
            0.96,
            pd.Timestamp(target_time).strftime("%Y-%m-%d %H:%M"),
            transform=ax.transAxes,
            fontsize=15,
            color="#202020",
            weight="bold",
            bbox={"facecolor": "white", "alpha": 0.55, "edgecolor": "none", "pad": 4},
        )
        sm = plt.cm.ScalarMappable(cmap="turbo", norm=plt.Normalize(vmin=vmin, vmax=vmax))
        colorbar = fig.colorbar(sm, ax=ax, fraction=0.028, pad=0.02)
        colorbar.set_label(variable)

        file_name = f"frame_{index:04d}.png"
        fig.savefig(output_dir / file_name, bbox_inches="tight", pad_inches=0.02)
        plt.close(fig)
        frames.append(
            {
                "time": pd.Timestamp(target_time).strftime("%Y-%m-%d %H:%M:%S"),
                "src": f"/assets/frames/{variable}/{file_name}",
            }
        )
        if index == 0 or (index + 1) % 25 == 0 or index == len(times) - 1:
            print(f"rendered {index + 1}/{len(times)} {file_name} {target_time}")

    manifest = {
        "variable": variable,
        "value_column": value_column,
        "frames": frames,
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {len(frames)} frame(s) to {output_dir}")


def parse_args():
    parser = argparse.ArgumentParser(description="Render prediction surface frames with GeoPandas boundary overlay.")
    parser.add_argument("--variable", default="temperature")
    parser.add_argument("--value-column", default="fusion_pred")
    parser.add_argument("--boundary", type=Path, default=ROOT / "frontend" / "assets" / "taiwan.geojson")
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--max-frames", type=int, default=None)
    parser.add_argument("--keep-old-frames", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    output = args.output_dir or ROOT / "frontend" / "assets" / "frames" / args.variable
    render_frames(
        variable=args.variable,
        value_column=args.value_column,
        boundary_path=args.boundary,
        output_dir=output,
        max_frames=args.max_frames,
        clean_output=not args.keep_old_frames,
    )
