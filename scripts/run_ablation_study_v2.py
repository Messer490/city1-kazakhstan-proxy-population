from __future__ import annotations

import argparse
import sys
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the City1 v2 Day 3 ablation study.")
    parser.add_argument("--features-dir", default="data/processed/features_v2_batch1")
    parser.add_argument("--feature-geojson-dir", default="data/processed/features_v2_batch1_geojson")
    parser.add_argument("--totals-csv", default="data/external/city_population_reference_v2.csv")
    parser.add_argument("--models-root", default="models/ablation_v2")
    parser.add_argument("--reports-root", default="reports/ablation_v2")
    parser.add_argument("--city-slugs", nargs="+", default=["almaty", "astana", "shymkent"])
    parser.add_argument("--external-benchmark-python", default=None)
    parser.add_argument("--report-only-summary-csv", default=None)
    parser.add_argument("--report-only-selected-extras-csv", default=None)
    return parser


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    from src.city1.ablation_study import AblationStudyConfig, build_report_only, run_ablation_study

    parser = build_parser()
    args = parser.parse_args()

    if args.report_only_summary_csv or args.report_only_selected_extras_csv:
        if not (args.report_only_summary_csv and args.report_only_selected_extras_csv):
            raise SystemExit(
                "Report-only mode requires both --report-only-summary-csv and "
                "--report-only-selected-extras-csv."
            )
        outputs = build_report_only(
            summary_csv=root / args.report_only_summary_csv,
            selected_extras_csv=root / args.report_only_selected_extras_csv,
            output_dir=root / args.reports_root,
        )
        print("Ablation report-only build completed.")
        for name, path in outputs.items():
            print(f"{name}: {path}")
        return

    config = AblationStudyConfig(
        features_dir=root / args.features_dir,
        feature_geojson_dir=root / args.feature_geojson_dir,
        totals_csv=root / args.totals_csv,
        models_root=root / args.models_root,
        reports_root=root / args.reports_root,
        city_slugs=tuple(args.city_slugs),
        external_benchmark_python=(Path(args.external_benchmark_python) if args.external_benchmark_python else None),
    )
    outputs = run_ablation_study(config)
    print("Ablation study completed.")
    print(f"winner_name: {outputs['winner_name']}")
    print(f"summary_csv_path: {outputs['summary_csv_path']}")
    print(f"selected_extras_csv_path: {outputs['selected_extras_csv_path']}")
    print(f"report_path: {outputs['report_path']}")
    print(f"figure_path: {outputs['figure_path']}")


if __name__ == "__main__":
    main()
