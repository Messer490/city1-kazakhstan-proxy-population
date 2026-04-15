from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CityGenerationSpec:
    output_name: str
    place_queries: tuple[str, ...]


DEFAULT_CITY_BATCH: tuple[CityGenerationSpec, ...] = (
    CityGenerationSpec("almaty", ("Almaty, Kazakhstan",)),
    CityGenerationSpec("astana", ("Astana, Kazakhstan",)),
    CityGenerationSpec("shymkent", ("Shymkent, Kazakhstan",)),
    CityGenerationSpec("semey", ("Semey, Kazakhstan",)),
    CityGenerationSpec("taraz", ("Taraz, Kazakhstan",)),
    CityGenerationSpec("petropavlovsk", ("Petropavl, Kazakhstan", "Petropavlovsk, Kazakhstan")),
    CityGenerationSpec("uralsk", ("Oral, Kazakhstan", "Uralsk, Kazakhstan")),
    CityGenerationSpec("ust_kamenogorsk", ("Oskemen, Kazakhstan", "Ust-Kamenogorsk, Kazakhstan")),
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate City1 v2 features for a predefined batch of cities.")
    parser.add_argument(
        "--cell-size",
        type=int,
        default=500,
        help="Grid cell size in meters for feature generation.",
    )
    parser.add_argument(
        "--csv-dir",
        type=str,
        default="data/processed/features_v2",
        help="Directory to store model-ready feature CSV files.",
    )
    parser.add_argument(
        "--geojson-dir",
        type=str,
        default="data/processed/features_v2_geojson",
        help="Directory to store GeoJSON display outputs.",
    )
    parser.add_argument(
        "--cities",
        nargs="*",
        default=None,
        help="Optional subset of output city names, for example: semey taraz uralsk",
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

    csv_dir = root / args.csv_dir
    geojson_dir = root / args.geojson_dir
    csv_dir.mkdir(parents=True, exist_ok=True)
    geojson_dir.mkdir(parents=True, exist_ok=True)

    selected = {name.strip().lower() for name in args.cities} if args.cities else None
    specs = [spec for spec in DEFAULT_CITY_BATCH if selected is None or spec.output_name in selected]
    if not specs:
        raise ValueError("No city specs were selected for generation.")

    config = FeaturePipelineConfig(grid=GridConfig(cell_size_meters=args.cell_size))
    failures: list[str] = []

    for spec in specs:
        last_error: Exception | None = None
        print(f"\n=== {spec.output_name} ===")

        for place_query in spec.place_queries:
            print(f"Trying query: {place_query}")
            try:
                artifacts = generate_city_features(place_query, config=config)
                report = validate_feature_output(
                    artifacts.features.feature_frame,
                    dataset_name=spec.output_name,
                )
                print("\n".join(report.to_lines()))

                csv_path = csv_dir / f"{spec.output_name}.csv"
                geojson_path = geojson_dir / f"{spec.output_name}.geojson"
                artifacts.features.feature_frame.to_csv(csv_path, index=False)
                artifacts.features.display_gdf.to_file(geojson_path, driver="GeoJSON")

                print(f"Saved CSV: {csv_path}")
                print(f"Saved GeoJSON: {geojson_path}")
                if artifacts.layers.warnings:
                    print("OSM warnings:")
                    for warning in artifacts.layers.warnings:
                        print(f"  - {warning}")
                last_error = None
                break
            except Exception as exc:  # pragma: no cover - depends on network/OSM service
                last_error = exc
                print(f"Failed query {place_query!r}: {exc}")

        if last_error is not None:
            failures.append(f"{spec.output_name}: {last_error}")

    if failures:
        print("\nBatch completed with failures:")
        for failure in failures:
            print(f"  - {failure}")
        raise SystemExit(1)

    print("\nBatch completed successfully.")


if __name__ == "__main__":
    main()
