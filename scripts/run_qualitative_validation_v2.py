from __future__ import annotations

import argparse
import sys
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the City1 v2 Day 4 qualitative validation layer.")
    parser.add_argument("--stage", choices=["scaffold", "render"], required=True)
    parser.add_argument("--full-inference-dir", default="data/processed/inference_runs")
    parser.add_argument(
        "--built-form-inference-dir",
        default="reports/ablation_v2/selected_extras/external_benchmark_inputs/built_form_only",
    )
    parser.add_argument("--completeness-csv", default="reports/osm_completeness_v2/osm_completeness_summary.csv")
    parser.add_argument("--registry-csv", default="data/external/qualitative_validation_case_registry_v2.csv")
    parser.add_argument("--output-dir", default="reports/qualitative_validation_v2")
    parser.add_argument("--city-slugs", nargs="+", default=["almaty", "astana"])
    return parser


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    from src.city1.qualitative_validation import (
        QualitativeValidationConfig,
        run_qualitative_render,
        run_qualitative_scaffold,
    )

    parser = build_parser()
    args = parser.parse_args()

    config = QualitativeValidationConfig(
        full_inference_dir=root / args.full_inference_dir,
        built_form_inference_dir=root / args.built_form_inference_dir,
        completeness_csv=root / args.completeness_csv,
        registry_csv=root / args.registry_csv,
        output_dir=root / args.output_dir,
        city_slugs=tuple(args.city_slugs),
    )

    if args.stage == "scaffold":
        outputs = run_qualitative_scaffold(config)
        print("Qualitative validation scaffold completed.")
    else:
        outputs = run_qualitative_render(config)
        print("Qualitative validation render completed.")

    for name, path in outputs.items():
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
