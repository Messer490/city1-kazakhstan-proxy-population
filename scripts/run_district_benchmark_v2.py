from __future__ import annotations

import argparse
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a district-level benchmark for a City1 v2 inference output.")
    parser.add_argument("--city-name", required=True, help='Example: "Almaty"')
    parser.add_argument(
        "--prediction-geojson",
        required=True,
        help="Path to a saved City1 v2 inference GeoJSON file.",
    )
    parser.add_argument(
        "--district-reference-csv",
        required=True,
        help="Path to the district population reference CSV.",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory where the district benchmark outputs will be saved.",
    )
    return parser.parse_args()


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    from src.city1.district_benchmark import run_district_benchmark

    args = parse_args()
    outputs = run_district_benchmark(
        city_name=args.city_name,
        prediction_geojson=root / args.prediction_geojson,
        district_reference_csv=root / args.district_reference_csv,
        output_dir=root / args.output_dir,
    )

    print("District benchmark completed.")
    print(f"city_name: {outputs['city_name']}")
    print(f"boundary_warning_count: {outputs['boundary_warning_count']}")
    print(f"metrics_path: {outputs['metrics_path']}")
    print(f"district_table_path: {outputs['district_table_path']}")
    print(f"report_path: {outputs['report_path']}")
    print(f"figure_bar_path: {outputs['figure_bar_path']}")
    print(f"figure_scatter_path: {outputs['figure_scatter_path']}")


if __name__ == "__main__":
    main()
