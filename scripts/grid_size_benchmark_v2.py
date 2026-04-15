from __future__ import annotations

import argparse
import sys
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a grid-size benchmark for City1 v2.")
    parser.add_argument(
        "--cities",
        nargs="+",
        required=True,
        help='City queries, for example "Almaty, Kazakhstan" "Astana, Kazakhstan".',
    )
    parser.add_argument(
        "--cell-sizes",
        nargs="+",
        type=int,
        default=[250, 500, 1000],
        help="Grid cell sizes in meters.",
    )
    parser.add_argument(
        "--model-path",
        type=str,
        default=None,
        help="Optional saved model artifact path. Defaults to the preferred v2 model.",
    )
    parser.add_argument(
        "--totals-csv",
        type=str,
        default="data/external/city_population_reference_v2.csv",
        help="Structured totals reference CSV.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="reports/grid_size_benchmark_v2",
        help="Directory where benchmark CSV and report outputs should be written.",
    )
    parser.add_argument(
        "--save-city-outputs",
        action="store_true",
        help="Also save per-city benchmark inference outputs under the benchmark output directory.",
    )
    return parser


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    from src.city1.grid_size_benchmark import (
        GridBenchmarkConfig,
        run_grid_size_benchmark,
        save_grid_size_benchmark,
    )

    parser = build_parser()
    args = parser.parse_args()

    config = GridBenchmarkConfig(
        place_names=tuple(args.cities),
        cell_sizes=tuple(args.cell_sizes),
        model_path=(root / args.model_path) if args.model_path else None,
        totals_csv=root / args.totals_csv,
        save_city_outputs=bool(args.save_city_outputs),
    )
    result = run_grid_size_benchmark(config, output_dir=root / args.output_dir)
    output_paths = save_grid_size_benchmark(result, root / args.output_dir)

    print("Grid-size benchmark completed.")
    print("Run results:")
    print(result.run_results.to_string(index=False))
    print("\nCell-size summary:")
    print(result.cell_size_summary.to_string(index=False))
    print("\nCity recommendations:")
    if result.city_recommendations.empty:
        print("No successful city recommendations were produced.")
    else:
        print(result.city_recommendations.to_string(index=False))
    if result.global_recommendation:
        print("\nGlobal recommendation:")
        print(result.global_recommendation)
    print("\nSaved outputs:")
    for name, path in output_paths.items():
        print(f"  - {name}: {path}")


if __name__ == "__main__":
    main()
