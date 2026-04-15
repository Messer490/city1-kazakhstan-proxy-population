from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower())
    return cleaned.strip("_") or "city"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate City1 v2 feature dataset for a city.")
    parser.add_argument("place_name", help="City name to geocode via OSM, for example 'Almaty, Kazakhstan'")
    parser.add_argument(
        "--cell-size",
        type=int,
        default=500,
        help="Grid cell size in meters for the working projected CRS.",
    )
    parser.add_argument(
        "--csv-out",
        type=str,
        default=None,
        help="Optional output CSV path for model-ready feature table.",
    )
    parser.add_argument(
        "--geojson-out",
        type=str,
        default=None,
        help="Optional output GeoJSON path for display geometry with feature columns.",
    )
    return parser


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    from src.city1.config import FeaturePipelineConfig, GridConfig
    from src.city1.pipeline import generate_city_features
    from src.city1.validation import validate_feature_output

    parser = build_parser()
    args = parser.parse_args()

    slug = slugify(args.place_name)
    csv_out = Path(args.csv_out) if args.csv_out else root / "data" / "interim" / f"{slug}_features.csv"
    geojson_out = (
        Path(args.geojson_out)
        if args.geojson_out
        else root / "data" / "interim" / f"{slug}_features.geojson"
    )

    csv_out.parent.mkdir(parents=True, exist_ok=True)
    geojson_out.parent.mkdir(parents=True, exist_ok=True)

    config = FeaturePipelineConfig(grid=GridConfig(cell_size_meters=args.cell_size))
    artifacts = generate_city_features(args.place_name, config=config)

    report = validate_feature_output(artifacts.features.feature_frame, dataset_name=args.place_name)
    print("\n".join(report.to_lines()))

    if artifacts.layers.warnings:
        print("OSM warnings:")
        for warning in artifacts.layers.warnings:
            print(f"  - {warning}")

    artifacts.features.feature_frame.to_csv(csv_out, index=False)
    artifacts.features.display_gdf.to_file(geojson_out, driver="GeoJSON")

    print(f"Saved CSV: {csv_out}")
    print(f"Saved GeoJSON: {geojson_out}")


if __name__ == "__main__":
    main()
