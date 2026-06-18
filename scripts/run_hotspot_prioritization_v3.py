from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build City1 v3 hotspot prioritization outputs from a canonical v3 GeoJSON file.")
    parser.add_argument("prediction_geojson", type=str, help="Path to a saved City1 v3 inference GeoJSON file.")
    parser.add_argument(
        "--output-root",
        type=str,
        default="reports/hotspot_prioritization_v3",
        help="Root directory for hotspot prioritization artifacts.",
    )
    parser.add_argument(
        "--run-id",
        type=str,
        required=True,
        help="Frozen run id used to place outputs under reports/hotspot_prioritization_v3/<run_id>/.",
    )
    parser.add_argument(
        "--hotspot-quantile",
        type=float,
        default=0.90,
        help="Quantile threshold used to select hotspot cells from p50.",
    )
    return parser


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    import geopandas as gpd

    from src.city1.hotspot_prioritization import build_hotspot_priority_table, save_hotspot_prioritization_outputs

    parser = build_parser()
    args = parser.parse_args()

    gdf = gpd.read_file(root / args.prediction_geojson)
    hotspots, summary = build_hotspot_priority_table(gdf, hotspot_quantile=args.hotspot_quantile)
    output_dir = root / args.output_root / args.run_id
    outputs = save_hotspot_prioritization_outputs(hotspots, summary, output_dir)
    manifest_path = output_dir / "run_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "run_id": args.run_id,
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
                "prediction_geojson": args.prediction_geojson,
                "hotspot_quantile": float(args.hotspot_quantile),
                "generated_files": [path.name for path in outputs.values()],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print("City1 v3 hotspot prioritization completed.")
    print(summary)
    for name, path in outputs.items():
        print(f"  - {name}: {path}")
    print(f"  - run_manifest_path: {manifest_path}")


if __name__ == "__main__":
    main()
