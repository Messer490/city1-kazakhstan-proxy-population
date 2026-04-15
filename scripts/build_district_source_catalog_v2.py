from __future__ import annotations

import argparse
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the official district population table catalog from stat.gov.kz for City1 v2."
    )
    parser.add_argument(
        "--output-csv",
        default="data/external/district_population_table_catalog_v2.csv",
        help="Path to the output CSV catalog.",
    )
    return parser.parse_args()


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    from src.city1.district_source_catalog import (
        build_district_population_source_catalog,
        save_district_population_source_catalog,
    )

    args = parse_args()
    catalog = build_district_population_source_catalog()
    output_path = save_district_population_source_catalog(catalog, output_path=root / args.output_csv)

    print(f"rows={len(catalog)}")
    print(f"output_csv={output_path}")


if __name__ == "__main__":
    main()
