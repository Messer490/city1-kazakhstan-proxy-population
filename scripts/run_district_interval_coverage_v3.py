from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build City1 v3 Phase 6 district interval coverage outputs from frozen v2 district benchmark tables."
    )
    parser.add_argument("--run-id", type=str, required=True, help="Frozen v3 run id.")
    parser.add_argument(
        "--district-report-root",
        type=str,
        default="reports/district_benchmark_v2",
        help="Root containing frozen v2 district benchmark tables.",
    )
    parser.add_argument(
        "--output-root",
        type=str,
        default="reports/district_interval_coverage_v3",
        help="Root for v3 district interval coverage outputs.",
    )
    parser.add_argument(
        "--city-status-csv",
        type=str,
        default="data/external/city_status_registry_v2.csv",
        help="City status registry for city display names.",
    )
    parser.add_argument(
        "--cities",
        nargs="+",
        default=["almaty", "astana", "shymkent"],
        help="Benchmark-city slugs to include.",
    )
    return parser


def _add_run_id(frame, run_id: str):
    if frame.empty:
        return frame
    output = frame.copy()
    output.insert(0, "run_id", run_id)
    return output


def run_district_interval_coverage(
    *,
    project_root: Path,
    run_id: str,
    district_report_root: str,
    output_root: str,
    city_status_csv: str,
    cities: list[str],
) -> dict[str, object]:
    from src.city1.uncertainty_validation import (
        build_partial_district_interval_coverage,
        load_city_display_lookup,
    )

    output_dir = project_root / output_root / run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    display_lookup = load_city_display_lookup(project_root / city_status_csv)
    detail, summary = build_partial_district_interval_coverage(
        run_id=run_id,
        district_report_root=project_root / district_report_root,
        cities=cities,
        display_lookup=display_lookup,
    )
    detail = _add_run_id(detail, run_id)
    summary = _add_run_id(summary, run_id)

    detail_path = output_dir / "district_interval_coverage.csv"
    summary_path = output_dir / "district_interval_city_summary.csv"
    detail.to_csv(detail_path, index=False)
    summary.to_csv(summary_path, index=False)

    manifest_path = output_dir / "run_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "run_id": run_id,
                "phase": "phase6_district_interval_coverage",
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
                "district_report_root": district_report_root,
                "output_root": str(output_dir),
                "cities": cities,
                "generated_outputs": {
                    "district_interval_coverage": str(detail_path),
                    "district_interval_city_summary": str(summary_path),
                },
                "status": "partial",
                "blocker_note": (
                    "District interval coverage is partial because frozen district polygon/cell assignment "
                    "artifacts are not available in the light package. The output carries forward p50-only "
                    "district comparison from the v2 benchmark."
                ),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    return {
        "output_dir": str(output_dir),
        "detail_path": str(detail_path),
        "summary_path": str(summary_path),
        "manifest_path": str(manifest_path),
        "detail": detail,
        "summary": summary,
        "partial": True,
    }


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    parser = build_parser()
    args = parser.parse_args()
    result = run_district_interval_coverage(
        project_root=project_root,
        run_id=args.run_id,
        district_report_root=args.district_report_root,
        output_root=args.output_root,
        city_status_csv=args.city_status_csv,
        cities=list(args.cities),
    )
    print("City1 v3 district interval coverage outputs generated.")
    print(f"run_id: {args.run_id}")
    print(f"output_dir: {result['output_dir']}")
    print(f"  - detail: {result['detail_path']}")
    print(f"  - summary: {result['summary_path']}")
    print(f"  - manifest: {result['manifest_path']}")
    print("  - status: partial (p50-only carry-forward from v2 district benchmark)")


if __name__ == "__main__":
    main()
