from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    from src.city1.kazakhstan_official_totals import build_verified_kazakhstan_city_records

    official_records, official_warnings = build_verified_kazakhstan_city_records(
        root / "data" / "external" / "region_population_tables"
    )

    frame = pd.DataFrame(official_records)
    if frame.empty:
        raise SystemExit("No verified official city totals were built. Refresh the source tables and try again.")

    column_order = [
        "city_name",
        "normalized_city_name",
        "country",
        "population",
        "reference_date",
        "source_tier",
        "verified",
        "source_name",
        "source_url",
        "notes",
    ]
    frame = frame[column_order].sort_values(["verified", "normalized_city_name"], ascending=[False, True])
    output_path = root / "data" / "external" / "city_population_reference_v2.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_path, index=False)

    print(f"Saved cleaned reference: {output_path}")
    if official_warnings:
        print("Official-source warnings:")
        for warning in official_warnings:
            print(f"  - {warning}")
    print(frame.to_string(index=False))


if __name__ == "__main__":
    main()
