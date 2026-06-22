from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build City1 v3 Phase 5 hotspot prioritization package from canonical Phase 4 uncertainty CSV outputs."
    )
    parser.add_argument(
        "--run-id",
        type=str,
        required=True,
        help="Frozen v3 run id, e.g. city1_v3_rf500m_e20_20260618T040646Z.",
    )
    parser.add_argument(
        "--input-root",
        type=str,
        default="outputs/v3_uncertainty",
        help="Root containing Phase 4 uncertainty outputs, with files under <input-root>/<run-id>/.",
    )
    parser.add_argument(
        "--output-root",
        type=str,
        default="reports/hotspot_prioritization_v3",
        help="Root for Phase 5 hotspot prioritization reports, written under <output-root>/<run-id>/.",
    )
    parser.add_argument(
        "--cities",
        nargs="+",
        default=["almaty", "astana", "semey", "shymkent"],
        help="City slugs to include. Defaults to the initial v3 freeze cities.",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=25,
        help="Number of top priority hotspot rows to export per city.",
    )
    parser.add_argument(
        "--no-figures",
        action="store_true",
        help="Skip lightweight non-map figures.",
    )
    return parser


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    from src.city1.hotspot_prioritization import generate_phase5_hotspot_package

    parser = build_parser()
    args = parser.parse_args()

    result = generate_phase5_hotspot_package(
        run_id=args.run_id,
        input_root=root / args.input_root,
        output_root=root / args.output_root,
        cities=args.cities,
        top_n=args.top_n,
        create_figures=not args.no_figures,
    )

    output_root = Path(result["output_root"])
    manifest = {
        "run_id": args.run_id,
        "phase": "phase5_hotspot_prioritization",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_root": str(root / args.input_root / args.run_id),
        "output_root": str(output_root),
        "cities": args.cities,
        "top_n": args.top_n,
        "figures_enabled": not args.no_figures,
        "generated_outputs": result["outputs"],
        "stable_hotspot_row_count": result["stable_count"],
        "caution_hotspot_row_count": result["caution_count"],
    }
    manifest_path = output_root / "run_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print("City1 v3 Phase 5 hotspot prioritization completed.")
    print(f"run_id: {args.run_id}")
    print(f"output_root: {output_root}")
    for name, path in result["outputs"].items():
        print(f"  - {name}: {path}")
    print(f"  - run_manifest: {manifest_path}")


if __name__ == "__main__":
    main()
