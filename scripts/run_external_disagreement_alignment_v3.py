from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build City1 v3 Phase 6 external disagreement alignment outputs from frozen v2 external benchmark alignment tables."
    )
    parser.add_argument("--run-id", type=str, required=True, help="Frozen v3 run id.")
    parser.add_argument(
        "--inference-root",
        type=str,
        default="outputs/v3_uncertainty",
        help="Root containing frozen v3 Phase 4 outputs.",
    )
    parser.add_argument(
        "--external-report-root",
        type=str,
        default="reports/external_benchmark_v2",
        help="Root containing frozen v2 external benchmark alignment CSV files.",
    )
    parser.add_argument(
        "--output-root",
        type=str,
        default="reports/external_disagreement_alignment_v3",
        help="Root for v3 external disagreement alignment outputs.",
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


def run_external_disagreement_alignment(
    *,
    project_root: Path,
    run_id: str,
    inference_root: str,
    external_report_root: str,
    output_root: str,
    city_status_csv: str,
    cities: list[str],
) -> dict[str, object]:
    from src.city1.uncertainty_validation import (
        build_external_disagreement_alignment_from_v2_reports,
        load_city_display_lookup,
    )

    output_dir = project_root / output_root / run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    display_lookup = load_city_display_lookup(project_root / city_status_csv)
    detail = build_external_disagreement_alignment_from_v2_reports(
        run_id=run_id,
        inference_root=project_root / inference_root,
        external_report_root=project_root / external_report_root,
        cities=cities,
        display_lookup=display_lookup,
    )

    if detail.empty:
        summary = _add_run_id(
            pd.DataFrame(
                [
                    {
                        "city_or_scope": "phase6_external_alignment",
                        "benchmark_product": "not_available",
                        "available_metric": "no_cell_level_alignment",
                        "relation_to_uncertainty": "",
                        "limitation_note": "No cell-level external alignment tables were available.",
                        "interpretation_note": "External disagreement alignment could not be computed.",
                    }
                ]
            ),
            run_id,
        )
        summary_path = output_dir / "external_disagreement_alignment_summary.csv"
        summary.to_csv(summary_path, index=False)
        manifest_outputs = {"external_disagreement_alignment_summary": str(summary_path)}
        detail_path = None
    else:
        detail = _add_run_id(detail, run_id)
        detail_path = output_dir / "external_disagreement_alignment.csv"
        detail.to_csv(detail_path, index=False)
        summary_path = None
        manifest_outputs = {"external_disagreement_alignment": str(detail_path)}

    manifest_path = output_dir / "run_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "run_id": run_id,
                "phase": "phase6_external_disagreement_alignment",
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
                "inference_root": inference_root,
                "external_report_root": external_report_root,
                "output_root": str(output_dir),
                "cities": cities,
                "generated_outputs": manifest_outputs,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    return {
        "output_dir": str(output_dir),
        "detail_path": str(detail_path) if detail_path else "",
        "summary_path": str(summary_path) if summary_path else "",
        "manifest_path": str(manifest_path),
        "detail": detail if not detail.empty else None,
    }


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    parser = build_parser()
    args = parser.parse_args()
    result = run_external_disagreement_alignment(
        project_root=project_root,
        run_id=args.run_id,
        inference_root=args.inference_root,
        external_report_root=args.external_report_root,
        output_root=args.output_root,
        city_status_csv=args.city_status_csv,
        cities=list(args.cities),
    )
    print("City1 v3 external disagreement alignment outputs generated.")
    print(f"run_id: {args.run_id}")
    print(f"output_dir: {result['output_dir']}")
    if result["detail_path"]:
        print(f"  - detail: {result['detail_path']}")
    if result["summary_path"]:
        print(f"  - summary: {result['summary_path']}")
    print(f"  - manifest: {result['manifest_path']}")


if __name__ == "__main__":
    main()
