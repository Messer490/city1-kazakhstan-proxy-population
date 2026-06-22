from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run City1 v3 Phase 6 core uncertainty validation against weak targets and frozen Phase 4/5 artifacts."
    )
    parser.add_argument("--run-id", type=str, required=True, help="Frozen v3 run id.")
    parser.add_argument(
        "--features-dir",
        type=str,
        default="data/processed/features_v2_batch1",
        help="Directory with frozen feature CSV files.",
    )
    parser.add_argument(
        "--totals-csv",
        type=str,
        default="data/external/city_population_reference_v2.csv",
        help="Official city totals CSV.",
    )
    parser.add_argument(
        "--city-status-csv",
        type=str,
        default="data/external/city_status_registry_v2.csv",
        help="City status registry used for display and support lookups.",
    )
    parser.add_argument(
        "--osm-summary-csv",
        type=str,
        default="reports/osm_completeness_v2/osm_completeness_summary.csv",
        help="OSM completeness summary used for bounded support context.",
    )
    parser.add_argument(
        "--inference-root",
        type=str,
        default="outputs/v3_uncertainty",
        help="Root containing frozen Phase 4 uncertainty outputs.",
    )
    parser.add_argument(
        "--hotspot-root",
        type=str,
        default="reports/hotspot_prioritization_v3",
        help="Root containing frozen Phase 5 hotspot outputs.",
    )
    parser.add_argument(
        "--output-root",
        type=str,
        default="reports/uncertainty_validation_v3",
        help="Root for core Phase 6 validation outputs.",
    )
    parser.add_argument(
        "--cities",
        nargs="+",
        default=["almaty", "astana", "semey", "shymkent"],
        help="Freeze-city slugs required for the Phase 4/5 input check.",
    )
    parser.add_argument(
        "--ensemble-size",
        type=int,
        default=20,
        help="Temporary ensemble size used if LOCO-like reconstruction is available.",
    )
    parser.add_argument(
        "--rf-n-estimators",
        type=int,
        default=150,
        help="Random forest tree count for bounded LOCO-like reconstruction.",
    )
    parser.add_argument(
        "--no-figures",
        action="store_true",
        help="Skip lightweight Phase 6 figures.",
    )
    return parser


def _add_run_id(frame: pd.DataFrame, run_id: str) -> pd.DataFrame:
    if frame.empty:
        return frame
    output = frame.copy()
    if "run_id" in output.columns:
        output["run_id"] = run_id
        ordered = ["run_id"] + [column for column in output.columns if column != "run_id"]
        output = output[ordered]
    else:
        output.insert(0, "run_id", run_id)
    return output


def _save_csv(frame: pd.DataFrame, path: Path) -> None:
    frame.to_csv(path, index=False)


def _save_optional_figures(
    *,
    output_dir: Path,
    interval_frame: pd.DataFrame,
    inference_frame: pd.DataFrame,
    confidence_summary: pd.DataFrame,
    hotspot_summary: pd.DataFrame,
) -> list[str]:
    try:
        import matplotlib.pyplot as plt
    except Exception:
        return []

    figures_dir = output_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    generated: list[str] = []

    if not interval_frame.empty:
        plot_df = interval_frame.copy()
        plot_df["city_protocol"] = plot_df["city"].astype(str) + " | " + plot_df["protocol"].astype(str)
        ax = plot_df.plot.bar(x="city_protocol", y="coverage_p10_p90", figsize=(11, 5), legend=False)
        ax.set_ylim(0, 1)
        ax.set_title("Interval coverage against weak targets by city/protocol")
        ax.set_ylabel("Coverage within p10-p90")
        ax.set_xlabel("City | protocol")
        plt.tight_layout()
        path = figures_dir / "interval_coverage_by_city.png"
        plt.savefig(path, dpi=150)
        plt.close()
        generated.append(str(path))

    if not inference_frame.empty:
        sample = inference_frame.sample(min(len(inference_frame), 2500), random_state=42) if len(inference_frame) > 2500 else inference_frame
        ax = sample.plot.scatter(
            x="relative_uncertainty",
            y="absolute_error_p50",
            c="confidence_score",
            colormap="viridis",
            figsize=(7, 5),
            alpha=0.35,
        )
        ax.set_title("Absolute proxy error vs relative uncertainty")
        ax.set_xlabel("Relative uncertainty")
        ax.set_ylabel("Absolute error vs weak target")
        plt.tight_layout()
        path = figures_dir / "error_vs_relative_uncertainty.png"
        plt.savefig(path, dpi=150)
        plt.close()
        generated.append(str(path))

    if not confidence_summary.empty:
        plot_df = confidence_summary.copy()
        plot_df["city_band"] = plot_df["city"].astype(str) + " | " + plot_df["confidence_band"].astype(str)
        ax = plot_df.plot.bar(x="city_band", y="mean_error_if_available", figsize=(11, 5), legend=False)
        ax.set_title("Mean proxy error by confidence band")
        ax.set_xlabel("City | confidence band")
        ax.set_ylabel("Mean absolute error vs weak target")
        plt.tight_layout()
        path = figures_dir / "confidence_band_error_summary.png"
        plt.savefig(path, dpi=150)
        plt.close()
        generated.append(str(path))

    if not hotspot_summary.empty:
        ax = hotspot_summary.plot.bar(
            x="hotspot_priority_class",
            y="mean_stability_metric",
            figsize=(10, 5),
            legend=False,
        )
        ax.set_ylim(0, 1)
        ax.set_title("Hotspot stability by priority class")
        ax.set_xlabel("Hotspot priority class")
        ax.set_ylabel("Mean stability metric")
        plt.tight_layout()
        path = figures_dir / "hotspot_stability_by_class.png"
        plt.savefig(path, dpi=150)
        plt.close()
        generated.append(str(path))

    return generated


def run_core_uncertainty_validation(
    *,
    project_root: Path,
    run_id: str,
    features_dir: str,
    totals_csv: str,
    city_status_csv: str,
    osm_summary_csv: str,
    inference_root: str,
    hotspot_root: str,
    output_root: str,
    cities: list[str],
    ensemble_size: int,
    rf_n_estimators: int,
    create_figures: bool,
) -> dict[str, object]:
    from src.city1.city_totals import load_city_totals
    from src.city1.training import TrainingConfig, build_training_dataset
    from src.city1.uncertainty import UncertaintyConfig
    from src.city1.uncertainty_validation import (
        compute_confidence_band_validation_summary,
        compute_error_uncertainty_alignment_summary,
        compute_error_uncertainty_monotonicity,
        compute_hotspot_stability_tables,
        compute_interval_coverage_summary,
        concatenate_proxy_check_frames,
        cross_validate_uncertainty_by_city,
        load_city_completeness_lookup,
        load_city_display_lookup,
        load_city_internal_support_lookup,
        load_inference_only_proxy_check_frames,
        load_phase4_city_frames,
        validate_phase6_inputs,
    )

    output_dir = project_root / output_root / run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    validation = validate_phase6_inputs(
        run_id=run_id,
        inference_root=project_root / inference_root,
        hotspot_root=project_root / hotspot_root,
        cities=cities,
    )
    validation_path = output_dir / "phase6_input_validation.json"
    validation_path.write_text(
        json.dumps(
            {
                "run_id": validation.run_id,
                "required_files": list(validation.required_files),
                "missing_files": list(validation.missing_files),
                "validation_errors": list(validation.validation_errors),
                "ok": validation.ok,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    if not validation.ok:
        raise SystemExit(
            "Phase 6 input validation failed:\n"
            + "\n".join(f"- {item}" for item in [*validation.missing_files, *validation.validation_errors])
        )

    display_lookup = load_city_display_lookup(project_root / city_status_csv)
    completeness_lookup = load_city_completeness_lookup(project_root / osm_summary_csv)
    internal_support_lookup = load_city_internal_support_lookup(project_root / city_status_csv)

    totals_lookup = load_city_totals(project_root / totals_csv)
    training_config = TrainingConfig(
        model_name="random_forest",
        rf_n_estimators=rf_n_estimators,
        rf_min_samples_leaf=2,
        rf_n_jobs=1,
        use_log_target=True,
        validation_protocol="leave_one_city_out",
    )

    core_outputs: dict[str, Path] = {"phase6_input_validation": validation_path}
    blocker_notes: list[str] = []

    dataset = build_training_dataset(
        features_dir=project_root / features_dir,
        totals_lookup=totals_lookup,
        required_feature_columns=training_config.feature_columns,
    )

    loco_diagnostics = pd.DataFrame()
    fold_metrics = pd.DataFrame()
    interval_loco = pd.DataFrame()
    error_loco = pd.DataFrame()
    monotonicity = pd.DataFrame()
    monotonicity_metrics: dict[str, float] = {}

    try:
        loco_diagnostics, fold_metrics = cross_validate_uncertainty_by_city(
            dataset.frame,
            training_config=training_config,
            uncertainty_config=UncertaintyConfig(ensemble_size=ensemble_size),
            display_lookup=display_lookup,
            completeness_lookup=completeness_lookup,
            internal_support_lookup=internal_support_lookup,
        )
        interval_loco = compute_interval_coverage_summary(loco_diagnostics, protocol="locov_like")
        error_loco = compute_error_uncertainty_alignment_summary(loco_diagnostics, protocol="locov_like")
        monotonicity, monotonicity_metrics = compute_error_uncertainty_monotonicity(
            loco_diagnostics,
            uncertainty_column="relative_uncertainty",
            error_column="absolute_error_p50",
        )
    except Exception as exc:
        blocker_notes.append(
            f"LOCO-like weak-target reconstruction was not completed. The bounded blocker was: {exc}"
        )

    inference_frames = load_inference_only_proxy_check_frames(
        run_id=run_id,
        inference_root=project_root / inference_root,
        features_dir=project_root / features_dir,
        totals_csv=project_root / totals_csv,
        cities=cities,
        training_config=training_config,
    )
    inference_diagnostics = concatenate_proxy_check_frames(inference_frames)
    interval_inference = compute_interval_coverage_summary(
        inference_diagnostics,
        protocol="inference_only_proxy_check",
    )
    error_inference = compute_error_uncertainty_alignment_summary(
        inference_diagnostics,
        protocol="inference_only_proxy_check",
    )
    confidence_summary = compute_confidence_band_validation_summary(inference_diagnostics)

    phase4_frames = load_phase4_city_frames(
        run_id=run_id,
        inference_root=project_root / inference_root,
        cities=cities,
    )
    hotspot_stability, hotspot_stability_summary = compute_hotspot_stability_tables(phase4_frames)

    interval_combined = pd.concat(
        [frame for frame in (interval_loco, interval_inference) if not frame.empty],
        ignore_index=True,
    ) if not interval_loco.empty or not interval_inference.empty else pd.DataFrame()
    error_combined = pd.concat(
        [frame for frame in (error_loco, error_inference) if not frame.empty],
        ignore_index=True,
    ) if not error_loco.empty or not error_inference.empty else pd.DataFrame()

    save_map: dict[str, pd.DataFrame] = {
        "interval_coverage_weak_target": _add_run_id(interval_combined, run_id),
        "error_uncertainty_alignment": _add_run_id(error_combined, run_id),
        "confidence_band_validation_summary": _add_run_id(confidence_summary, run_id),
        "hotspot_stability": _add_run_id(hotspot_stability, run_id),
        "hotspot_stability_summary": _add_run_id(hotspot_stability_summary, run_id),
        "uncertainty_fold_metrics": _add_run_id(fold_metrics, run_id),
        "uncertainty_monotonicity": _add_run_id(monotonicity, run_id),
        "uncertainty_diagnostics_loco_like": _add_run_id(loco_diagnostics, run_id),
        "uncertainty_diagnostics_inference_only_proxy_check": _add_run_id(inference_diagnostics, run_id),
    }

    for stem, frame in save_map.items():
        path = output_dir / f"{stem}.csv"
        _save_csv(frame, path)
        core_outputs[stem] = path

    monotonicity_metrics_path = output_dir / "uncertainty_monotonicity_metrics.json"
    monotonicity_metrics_path.write_text(json.dumps(monotonicity_metrics, indent=2), encoding="utf-8")
    core_outputs["uncertainty_monotonicity_metrics"] = monotonicity_metrics_path

    figure_paths = _save_optional_figures(
        output_dir=output_dir,
        interval_frame=save_map["interval_coverage_weak_target"],
        inference_frame=inference_diagnostics,
        confidence_summary=confidence_summary,
        hotspot_summary=hotspot_stability_summary,
    ) if create_figures else []

    manifest_path = output_dir / "run_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "run_id": run_id,
                "phase": "phase6_core_uncertainty_validation",
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
                "features_dir": features_dir,
                "totals_csv": totals_csv,
                "city_status_csv": city_status_csv,
                "osm_summary_csv": osm_summary_csv,
                "inference_root": inference_root,
                "hotspot_root": hotspot_root,
                "output_root": str(output_dir),
                "ensemble_size_for_loco_like": ensemble_size,
                "rf_n_estimators_for_loco_like": rf_n_estimators,
                "generated_outputs": {key: str(path) for key, path in core_outputs.items()},
                "generated_figures": figure_paths,
                "blocker_notes": blocker_notes,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    core_outputs["run_manifest"] = manifest_path

    return {
        "output_dir": str(output_dir),
        "outputs": {key: str(path) for key, path in core_outputs.items()},
        "figures": figure_paths,
        "blocker_notes": blocker_notes,
        "loco_ensemble_size": ensemble_size,
        "loco_rf_n_estimators": rf_n_estimators,
        "interval_coverage": save_map["interval_coverage_weak_target"],
        "error_alignment": save_map["error_uncertainty_alignment"],
        "confidence_summary": save_map["confidence_band_validation_summary"],
        "hotspot_stability_summary": save_map["hotspot_stability_summary"],
    }


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    parser = build_parser()
    args = parser.parse_args()

    result = run_core_uncertainty_validation(
        project_root=project_root,
        run_id=args.run_id,
        features_dir=args.features_dir,
        totals_csv=args.totals_csv,
        city_status_csv=args.city_status_csv,
        osm_summary_csv=args.osm_summary_csv,
        inference_root=args.inference_root,
        hotspot_root=args.hotspot_root,
        output_root=args.output_root,
        cities=list(args.cities),
        ensemble_size=int(args.ensemble_size),
        rf_n_estimators=int(args.rf_n_estimators),
        create_figures=not args.no_figures,
    )

    print("City1 v3 Phase 6 core uncertainty validation completed.")
    print(f"run_id: {args.run_id}")
    print(f"output_dir: {result['output_dir']}")
    for name, path in result["outputs"].items():
        print(f"  - {name}: {path}")
    if result["figures"]:
        for path in result["figures"]:
            print(f"  - figure: {path}")
    if result["blocker_notes"]:
        print("Blockers / partial notes:")
        for note in result["blocker_notes"]:
            print(f"  - {note}")


if __name__ == "__main__":
    main()
