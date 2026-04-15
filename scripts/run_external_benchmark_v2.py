from __future__ import annotations

import argparse
import sys
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the City1 v2 external benchmark comparison against WorldPop and GHS-POP."
    )
    parser.add_argument(
        "--inference-runs-dir",
        default="data/processed/inference_runs",
        help="Directory with City1 inference GeoJSON outputs to compare.",
    )
    parser.add_argument(
        "--output-dir",
        default="reports/external_benchmark_v2",
        help="Directory where the external benchmark report package should be written.",
    )
    parser.add_argument(
        "--city-slugs",
        nargs="+",
        default=["almaty", "astana", "shymkent"],
        help="City slugs to compare. Defaults to the three anchor benchmark cities.",
    )
    return parser


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    from src.city1.external_benchmark import ExternalBenchmarkConfig, run_external_benchmark_batch

    parser = build_parser()
    args = parser.parse_args()

    config = ExternalBenchmarkConfig(
        inference_runs_dir=root / args.inference_runs_dir,
        output_dir=root / args.output_dir,
        city_slugs=tuple(args.city_slugs),
    )

    try:
        outputs = run_external_benchmark_batch(config)
    except ImportError as exc:
        raise SystemExit(
            "External benchmark pipeline requires rasterio. "
            "Run this script with an interpreter where rasterio is installed "
            "(for example the system Python on this machine), or install rasterio "
            "into the active environment.\n"
            f"Original error: {exc}"
        ) from exc

    print("External benchmark comparison completed.")
    print(f"metrics_path: {outputs['metrics_path']}")
    print(f"summary_path: {outputs['summary_path']}")
    print(f"report_path: {outputs['report_path']}")
    print(f"pearson_figure_path: {outputs['pearson_figure_path']}")
    print(f"hotspot_figure_path: {outputs['hotspot_figure_path']}")


if __name__ == "__main__":
    main()
