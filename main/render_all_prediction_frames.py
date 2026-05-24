from __future__ import annotations

from render_prediction_frames import ROOT, render_frames


VARIABLES = ["temperature", "humidity", "wind_speed", "pressure"]


def main() -> None:
    for variable in VARIABLES:
        output_dir = ROOT / "frontend" / "assets" / "frames" / variable
        print(f"\n=== rendering {variable} ===")
        try:
            render_frames(
                variable=variable,
                value_column="fusion_pred",
                boundary_path=ROOT / "frontend" / "assets" / "taiwan.geojson",
                output_dir=output_dir,
                max_frames=None,
                clean_output=True,
            )
        except ValueError as exc:
            print(f"skip {variable}: {exc}")


if __name__ == "__main__":
    main()
