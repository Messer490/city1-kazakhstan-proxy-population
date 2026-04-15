from __future__ import annotations

import argparse
import sys
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build the OSM completeness report for City1 v2.")
    parser.add_argument(
        "--features-dir",
        type=str,
        default="data/processed/features_v2_batch1",
        help="Directory with feature CSV files.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="reports/osm_completeness_v2",
        help="Directory for the completeness report outputs.",
    )
    return parser


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    from src.city1.osm_completeness import build_osm_completeness_batch, save_osm_completeness_report

    parser = build_parser()
    args = parser.parse_args()

    summary = build_osm_completeness_batch(root / args.features_dir)
    outputs = save_osm_completeness_report(summary, root / args.output_dir)

    print("OSM completeness report completed.")
    print(summary.to_string(index=False))
    for name, path in outputs.items():
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
