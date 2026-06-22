from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the full City1 v3 Phase 6 uncertainty validation stack for a frozen run id."
    )
    parser.add_argument("--run-id", type=str, required=True, help="Frozen v3 run id.")
    parser.add_argument("--features-dir", type=str, default="data/processed/features_v2_batch1")
    parser.add_argument("--totals-csv", type=str, default="data/external/city_population_reference_v2.csv")
    parser.add_argument("--city-status-csv", type=str, default="data/external/city_status_registry_v2.csv")
    parser.add_argument("--osm-summary-csv", type=str, default="reports/osm_completeness_v2/osm_completeness_summary.csv")
    parser.add_argument("--inference-root", type=str, default="outputs/v3_uncertainty")
    parser.add_argument("--hotspot-root", type=str, default="reports/hotspot_prioritization_v3")
    parser.add_argument("--uncertainty-output-root", type=str, default="reports/uncertainty_validation_v3")
    parser.add_argument("--district-output-root", type=str, default="reports/district_interval_coverage_v3")
    parser.add_argument("--external-output-root", type=str, default="reports/external_disagreement_alignment_v3")
    parser.add_argument("--district-report-root", type=str, default="reports/district_benchmark_v2")
    parser.add_argument("--external-report-root", type=str, default="reports/external_benchmark_v2")
    parser.add_argument("--ensemble-size", type=int, default=20)
    parser.add_argument("--rf-n-estimators", type=int, default=150)
    parser.add_argument("--no-figures", action="store_true")
    return parser


def _mean_or_nan(frame: pd.DataFrame, column: str) -> float:
    if frame.empty or column not in frame.columns:
        return float("nan")
    return float(pd.to_numeric(frame[column], errors="coerce").mean())


def _phase6_status(core_blockers: list[str], district_partial: bool) -> str:
    if core_blockers or district_partial:
        return "partially completed"
    return "completed"


def _build_phase6_report(
    *,
    run_id: str,
    core_result: dict[str, object],
    district_result: dict[str, object],
    external_result: dict[str, object],
    output_dir: Path,
) -> Path:
    interval_frame = core_result["interval_coverage"]
    error_frame = core_result["error_alignment"]
    confidence_frame = core_result["confidence_summary"]
    hotspot_frame = core_result["hotspot_stability_summary"]
    blockers = list(core_result["blocker_notes"])
    district_partial = bool(district_result.get("partial", False))
    status = _phase6_status(blockers, district_partial)

    strongest = []
    if not error_frame.empty:
        strongest.append("error-vs-uncertainty alignment is available at least for inference-only proxy checks")
    if not interval_frame.empty:
        strongest.append("interval coverage against weak targets is explicitly reported")
    if not hotspot_frame.empty:
        strongest.append("hotspot stability summary is available by priority class")
    if not strongest:
        strongest.append("only minimal Phase 6 outputs were generated")

    weakest = []
    if blockers:
        weakest.extend(blockers)
    if district_partial:
        weakest.append("district interval coverage remains partial because frozen district assignment artifacts are unavailable offline")
    if not external_result.get("detail_path"):
        weakest.append("external disagreement alignment could not be computed at cell level")

    lines = [
        "# PHASE 6 Uncertainty Validation Report",
        "",
        f"- run_id: `{run_id}`",
        f"- status: **{status}**",
        "- interpretation discipline: Phase 6 evaluates whether v3 uncertainty behaves meaningfully within the calibrated proxy-target framework.",
        f"- LOCO-like reconstruction config used in this run: ensemble_size=`{core_result['loco_ensemble_size']}`, rf_n_estimators=`{core_result['loco_rf_n_estimators']}`",
        "",
        "## Inputs used",
    ]
    for path in (
        core_result["outputs"].get("phase6_input_validation"),
        core_result["outputs"].get("uncertainty_diagnostics_loco_like"),
        core_result["outputs"].get("uncertainty_diagnostics_inference_only_proxy_check"),
        district_result.get("detail_path"),
        external_result.get("detail_path") or external_result.get("summary_path"),
    ):
        if path:
            lines.append(f"- `{path}`")

    lines.extend(
        [
            "",
            "## Outputs generated",
        ]
    )
    for _, path in sorted(core_result["outputs"].items()):
        lines.append(f"- `{path}`")
    if core_result["figures"]:
        for path in core_result["figures"]:
            lines.append(f"- `{path}`")
    for key in ("detail_path", "summary_path", "manifest_path"):
        path = district_result.get(key)
        if path:
            lines.append(f"- `{path}`")
    for key in ("detail_path", "summary_path", "manifest_path"):
        path = external_result.get(key)
        if path:
            lines.append(f"- `{path}`")

    lines.extend(
        [
            "",
            "## Interval coverage results",
            "",
        ]
    )
    if interval_frame.empty:
        lines.append("- No interval coverage table was generated.")
    else:
        for row in interval_frame.to_dict(orient="records"):
            lines.append(
                f"- {row['city']} [{row['protocol']}]: coverage={row['coverage_p10_p90']:.3f}, "
                f"below_p10={row['below_p10_share']:.3f}, above_p90={row['above_p90_share']:.3f}. "
                f"{row['interpretation_note']}"
            )

    lines.extend(
        [
            "",
            "## Error-vs-uncertainty results",
            "",
        ]
    )
    if error_frame.empty:
        lines.append("- No error-vs-uncertainty alignment table was generated.")
    else:
        for row in error_frame.to_dict(orient="records"):
            lines.append(
                f"- {row['city']} [{row['protocol']}]: spearman(error, relative_uncertainty)={row['spearman_error_vs_relative_uncertainty']:.3f}, "
                f"spearman(error, confidence_score)={row['spearman_error_vs_confidence_score']:.3f}. "
                f"{row['interpretation_note']}"
            )

    lines.extend(
        [
            "",
            "## District interval coverage results or blocker",
            "",
        ]
    )
    district_summary_path = district_result.get("summary_path")
    if district_summary_path:
        district_summary = pd.read_csv(district_summary_path)
        for row in district_summary.to_dict(orient="records"):
            lines.append(
                f"- {row['city']}: compared_districts={row['n_districts_compared']}, "
                f"mean_absolute_error_p50={row['mean_absolute_error_p50']}. "
                f"{row['interpretation_note']}"
            )
    else:
        lines.append("- District interval coverage output is missing.")

    lines.extend(
        [
            "",
            "## External disagreement alignment results or blocker",
            "",
        ]
    )
    if external_result.get("detail_path"):
        external_detail = pd.read_csv(external_result["detail_path"])
        for row in external_detail.to_dict(orient="records"):
            lines.append(
                f"- {row['city']} vs {row['benchmark_product']}: spearman(disagreement, uncertainty)={row['spearman_disagreement_vs_uncertainty']:.3f}. "
                f"{row['interpretation_note']}"
            )
    elif external_result.get("summary_path"):
        external_summary = pd.read_csv(external_result["summary_path"])
        for row in external_summary.to_dict(orient="records"):
            lines.append(
                f"- {row['benchmark_product']}: {row['limitation_note']} {row['interpretation_note']}"
            )
    else:
        lines.append("- External disagreement alignment output is missing.")

    lines.extend(
        [
            "",
            "## Hotspot stability results",
            "",
        ]
    )
    if hotspot_frame.empty:
        lines.append("- No hotspot stability summary was generated.")
    else:
        for row in hotspot_frame.to_dict(orient="records"):
            lines.append(
                f"- {row['city']} / {row['hotspot_priority_class']}: mean_stability={row['mean_stability_metric']:.3f}, "
                f"mean_confidence={row['mean_confidence_score']:.3f}. {row['interpretation_note']}"
            )

    lines.extend(
        [
            "",
            "## Confidence-band validation summary",
            "",
        ]
    )
    if confidence_frame.empty:
        lines.append("- No confidence-band validation summary was generated.")
    else:
        for row in confidence_frame.to_dict(orient="records"):
            lines.append(
                f"- {row['city']} / {row['confidence_band']}: share_cells={row['share_cells']:.3f}, "
                f"median_relative_uncertainty={row['median_relative_uncertainty']:.3f}, "
                f"mean_error_if_available={row['mean_error_if_available']:.3f}. {row['interpretation_note']}"
            )

    lines.extend(
        [
            "",
            "## Strongest evidence that uncertainty is meaningful",
            "",
        ]
    )
    for item in strongest:
        lines.append(f"- {item}")

    lines.extend(
        [
            "",
            "## Weakest evidence or unresolved uncertainty",
            "",
        ]
    )
    for item in weakest:
        lines.append(f"- {item}")

    lines.extend(
        [
            "",
            "## Limitations",
            "",
            "- uncertainty remains a confidence layer around a calibrated proxy surface, not true census uncertainty",
            "- weak-target checks are not cell-level census validation",
            "- external products provide structural comparison context, not ground truth",
            "- district support remains partial where frozen district assignment artifacts are unavailable",
            "",
            "## What Phase 6 does not prove",
            "",
            "- it does not validate true population uncertainty",
            "- it does not prove cell-level census correctness",
            "- it does not convert confidence_score into truth probability",
            "",
            "## Readiness for Phase 7",
            "",
            f"- Phase 7 can start conditionally: {status}. "
            "A paper-facing package can begin if the current partial district limitation is accepted explicitly; "
            "otherwise Phase 7 should wait for frozen district assignment artifacts.",
        ]
    )

    report_path = output_dir / "PHASE_6_UNCERTAINTY_VALIDATION_REPORT.md"
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_path


def _update_completion_plan(project_root: Path, *, phase6_status: str, run_id: str) -> None:
    plan_path = project_root / "docs" / "V3_COMPLETION_PLAN.md"
    content = """# City1 v3 Completion Plan

## Objective

Complete `City1 v3` as an **uncertainty-aware extension of City1 v2** without redesigning the v2 science.

`v2` builds the calibrated proxy population surface.  
`v3` adds bounded reliability information around that surface.

## Phase Status

- Phase 1: **completed** - audit and repo status check
- Phase 2: **completed** - data contract and directory conventions frozen
- Phase 3: **completed** - v3 uncertainty ensemble trained
- Phase 4: **completed** - v3 uncertainty inference generated for Almaty, Astana, Semey, and Shymkent
- Phase 5: **completed** - hotspot prioritization evidence package generated
- Phase 6: **%PHASE6_STATUS%** - uncertainty validation evidence stack for `%RUN_ID%`
- Phase 7: **not started** - paper-facing v3 package
- Phase 8: **not started** - manuscript package

## Current frozen evidence roots

- `outputs/v3_uncertainty/%RUN_ID%/`
- `reports/hotspot_prioritization_v3/%RUN_ID%/`
- `reports/uncertainty_validation_v3/%RUN_ID%/`
- `reports/district_interval_coverage_v3/%RUN_ID%/`
- `reports/external_disagreement_alignment_v3/%RUN_ID%/`

## Phase 6 outcome

- core weak-target interval coverage and error-alignment outputs generated under `reports/uncertainty_validation_v3/%RUN_ID%/`
- hotspot stability and confidence-band summaries generated under `reports/uncertainty_validation_v3/%RUN_ID%/`
- district interval coverage is currently partial and rooted in `reports/district_interval_coverage_v3/%RUN_ID%/`
- external disagreement alignment generated under `reports/external_disagreement_alignment_v3/%RUN_ID%/`

## Phase 7 start condition

Phase 7 may start only after the author accepts one of the following:

- proceed with the current explicit partial district-coverage limitation, or
- add frozen offline district assignment artifacts that allow true district interval aggregation.
"""
    content = content.replace("%PHASE6_STATUS%", phase6_status).replace("%RUN_ID%", run_id)
    plan_path.write_text(content, encoding="utf-8")


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    from scripts.run_district_interval_coverage_v3 import run_district_interval_coverage
    from scripts.run_external_disagreement_alignment_v3 import run_external_disagreement_alignment
    from scripts.run_uncertainty_validation_v3 import run_core_uncertainty_validation

    parser = build_parser()
    args = parser.parse_args()

    core_result = run_core_uncertainty_validation(
        project_root=project_root,
        run_id=args.run_id,
        features_dir=args.features_dir,
        totals_csv=args.totals_csv,
        city_status_csv=args.city_status_csv,
        osm_summary_csv=args.osm_summary_csv,
        inference_root=args.inference_root,
        hotspot_root=args.hotspot_root,
        output_root=args.uncertainty_output_root,
        cities=["almaty", "astana", "semey", "shymkent"],
        ensemble_size=int(args.ensemble_size),
        rf_n_estimators=int(args.rf_n_estimators),
        create_figures=not args.no_figures,
    )

    district_result = run_district_interval_coverage(
        project_root=project_root,
        run_id=args.run_id,
        district_report_root=args.district_report_root,
        output_root=args.district_output_root,
        city_status_csv=args.city_status_csv,
        cities=["almaty", "astana", "shymkent"],
    )

    external_result = run_external_disagreement_alignment(
        project_root=project_root,
        run_id=args.run_id,
        inference_root=args.inference_root,
        external_report_root=args.external_report_root,
        output_root=args.external_output_root,
        city_status_csv=args.city_status_csv,
        cities=["almaty", "astana", "shymkent"],
    )

    phase6_output_dir = project_root / args.uncertainty_output_root / args.run_id
    report_path = _build_phase6_report(
        run_id=args.run_id,
        core_result=core_result,
        district_result=district_result,
        external_result=external_result,
        output_dir=phase6_output_dir,
    )

    phase6_status = _phase6_status(list(core_result["blocker_notes"]), bool(district_result.get("partial", False)))
    _update_completion_plan(project_root, phase6_status=phase6_status, run_id=args.run_id)

    top_manifest = {
        "run_id": args.run_id,
        "phase": "phase6_uncertainty_validation",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": phase6_status,
        "core_output_dir": core_result["output_dir"],
        "district_output_dir": district_result["output_dir"],
        "external_output_dir": external_result["output_dir"],
        "phase6_report": str(report_path),
        "core_blockers": list(core_result["blocker_notes"]),
        "district_partial": bool(district_result.get("partial", False)),
    }
    manifest_path = phase6_output_dir / "phase6_orchestration_manifest.json"
    manifest_path.write_text(json.dumps(top_manifest, indent=2), encoding="utf-8")

    print(f"Phase 6 uncertainty validation {phase6_status}.")
    print(f"run_id: {args.run_id}")
    print(f"core_output_dir: {core_result['output_dir']}")
    print(f"district_output_dir: {district_result['output_dir']}")
    print(f"external_output_dir: {external_result['output_dir']}")
    print(f"phase6_report: {report_path}")
    print(f"orchestration_manifest: {manifest_path}")


if __name__ == "__main__":
    main()
