from __future__ import annotations

import argparse
import sys
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run City1 v2 inference for a single city.")
    parser.add_argument("place_name", help="City query, for example 'Semey, Kazakhstan'")
    parser.add_argument(
        "--model-path",
        type=str,
        default=None,
        help="Optional path to a saved v2 model artifact. Defaults to the best known model.",
    )
    parser.add_argument(
        "--totals-csv",
        type=str,
        default="data/external/city_population_reference_v2.csv",
        help="Structured totals reference CSV.",
    )
    parser.add_argument(
        "--cell-size",
        type=int,
        default=500,
        help="Grid cell size in meters.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/processed/inference_runs",
        help="Directory where CSV and GeoJSON outputs should be saved.",
    )
    return parser


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    from src.city1.config import FeaturePipelineConfig, GridConfig
    from src.city1.inference import CityInferenceError, run_city_inference, save_city_inference_outputs

    parser = build_parser()
    args = parser.parse_args()

    pipeline_config = FeaturePipelineConfig(grid=GridConfig(cell_size_meters=args.cell_size))
    try:
        result = run_city_inference(
            place_name=args.place_name,
            model_path=(root / args.model_path) if args.model_path else None,
            totals_csv=root / args.totals_csv,
            pipeline_config=pipeline_config,
        )
    except CityInferenceError as exc:
        raise SystemExit(str(exc)) from exc
    saved = save_city_inference_outputs(result, root / args.output_dir)

    print("\n".join(result.feature_validation_report.to_lines()))
    print("\n".join(result.output_validation_report.to_lines()))
    print(f"Model: {result.model.model_name}")
    print(f"Official population: {result.official_population}")
    print(f"Raw prediction sum: {result.raw_prediction_sum:.3f}")
    print(f"Calibration factor: {result.calibration_factor:.6f}")
    print(f"Final population sum: {result.output_frame['Population_Estimate_Final'].sum():.3f}")
    if result.feature_artifacts.layers.warnings:
        print("OSM warnings:")
        for warning in result.feature_artifacts.layers.warnings:
            print(f"  - {warning}")
    if not result.qa_flags.empty:
        print("QA flags:")
        print(result.qa_flags.to_string(index=False))
    print(f"Saved CSV: {saved['csv_path']}")
    print(f"Saved GeoJSON: {saved['geojson_path']}")


if __name__ == "__main__":
    main()
