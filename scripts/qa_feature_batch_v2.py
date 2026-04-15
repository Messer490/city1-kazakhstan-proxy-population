from __future__ import annotations

import argparse
import sys
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run QA checks for a directory of City1 v2 feature CSV files.")
    parser.add_argument(
        "--features-dir",
        type=str,
        required=True,
        help="Directory with feature CSV files to analyze.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="reports/feature_qa",
        help="Directory where QA CSV reports should be written.",
    )
    return parser


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    from src.city1.feature_qa import run_feature_qa, summarize_feature_qa

    parser = build_parser()
    args = parser.parse_args()

    bundle = run_feature_qa(root / args.features_dir)
    output_dir = root / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    city_summary_path = output_dir / "city_summary.csv"
    feature_summary_path = output_dir / "feature_summary.csv"
    flags_path = output_dir / "flags.csv"

    bundle.city_summary.to_csv(city_summary_path, index=False)
    bundle.feature_summary.to_csv(feature_summary_path, index=False)
    bundle.flags.to_csv(flags_path, index=False)

    for line in summarize_feature_qa(bundle):
        print(line)
    print(f"Saved city summary: {city_summary_path}")
    print(f"Saved feature summary: {feature_summary_path}")
    print(f"Saved flags: {flags_path}")


if __name__ == "__main__":
    main()
