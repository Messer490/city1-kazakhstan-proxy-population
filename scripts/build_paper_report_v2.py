from __future__ import annotations

import argparse
import sys
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build the City1 v2 paper/report artifact package.")
    parser.add_argument(
        "--output-dir",
        type=str,
        default="reports/paper_v2_baseline",
        help="Directory where the paper report package should be written.",
    )
    parser.add_argument(
        "--example-city-slugs",
        nargs="+",
        default=["almaty", "semey"],
        help="Inference-run city slugs to render as example static figures.",
    )
    return parser


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    from src.city1.paper_report import PaperReportConfig, build_paper_report

    parser = build_parser()
    args = parser.parse_args()

    config = PaperReportConfig(
        output_dir=root / args.output_dir,
        example_city_slugs=tuple(args.example_city_slugs),
    )
    outputs = build_paper_report(config)

    print("Paper/report package completed.")
    for name, path in outputs.items():
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
