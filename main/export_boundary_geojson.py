from __future__ import annotations

import argparse
from pathlib import Path

import geopandas as gpd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "frontend" / "assets" / "taiwan.geojson"


def export_boundary(
    input_path: Path,
    output_path: Path = DEFAULT_OUTPUT,
    filter_column: str | None = None,
    filter_value: str | None = None,
    simplify_tolerance: float = 0.0,
) -> None:
    gdf = gpd.read_file(input_path)

    if filter_column and filter_value:
        if filter_column not in gdf.columns:
            raise ValueError(f"Column not found: {filter_column}")
        gdf = gdf[gdf[filter_column].astype(str).str.contains(filter_value, case=False, na=False)]

    if gdf.empty:
        raise ValueError("No geometries remained after filtering.")

    gdf = gdf.to_crs(epsg=4326)
    gdf = gdf[["geometry"]].copy()
    gdf["name"] = "Taiwan boundary"

    if simplify_tolerance > 0:
        gdf["geometry"] = gdf.geometry.simplify(simplify_tolerance, preserve_topology=True)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_file(output_path, driver="GeoJSON")
    print(f"Exported {len(gdf)} feature(s) to {output_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert an official boundary file to frontend/assets/taiwan.geojson."
    )
    parser.add_argument("input", type=Path, help="Input .shp, .geojson, or .gpkg path.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--filter-column", default=None)
    parser.add_argument("--filter-value", default=None)
    parser.add_argument(
        "--simplify-tolerance",
        type=float,
        default=0.0,
        help="Optional simplification tolerance in degrees after EPSG:4326 conversion.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    export_boundary(
        input_path=args.input,
        output_path=args.output,
        filter_column=args.filter_column,
        filter_value=args.filter_value,
        simplify_tolerance=args.simplify_tolerance,
    )
