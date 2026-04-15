from __future__ import annotations

import argparse
import sys
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run an end-to-end City1 v2 smoke test for one city.")
    parser.add_argument(
        "--place-name",
        type=str,
        default="Semey, Kazakhstan",
        help="City query to use for the smoke test.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/processed/smoke_tests",
        help="Directory where smoke test outputs should be saved.",
    )
    parser.add_argument(
        "--cell-size",
        type=int,
        default=500,
        help="Grid cell size in meters.",
    )
    return parser


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    from src.city1.config import FeaturePipelineConfig, GridConfig
    from src.city1.inference import run_city_inference, save_city_inference_outputs

    parser = build_parser()
    args = parser.parse_args()

    result = run_city_inference(
        place_name=args.place_name,
        pipeline_config=FeaturePipelineConfig(grid=GridConfig(cell_size_meters=args.cell_size)),
    )
    saved = save_city_inference_outputs(result, root / args.output_dir, stem="smoke_test_output")
    final_sum = float(result.output_frame["Population_Estimate_Final"].sum())

    if result.feature_validation_report.has_errors:
        raise SystemExit("Smoke test failed: feature validation returned errors.")
    if result.output_validation_report.has_errors:
        raise SystemExit("Smoke test failed: output validation returned errors.")
    if abs(final_sum - float(result.official_population)) > 1e-6:
        raise SystemExit(
            "Smoke test failed: calibrated output sum does not match the official city total."
        )

    print("Smoke test completed.")
    print(f"Place: {args.place_name}")
    print(f"Rows: {len(result.output_frame)}")
    print(f"Official population: {result.official_population}")
    print(f"Final sum: {final_sum:.3f}")
    if result.feature_artifacts.layers.warnings:
        print("OSM warnings:")
        for warning in result.feature_artifacts.layers.warnings:
            print(f"  - {warning}")
    print(f"CSV: {saved['csv_path']}")
    print(f"GeoJSON: {saved['geojson_path']}")


if __name__ == "__main__":
    main()
