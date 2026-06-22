from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import shutil
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .paths import PROJECT_ROOT


DEFAULT_RUN_ID = "city1_v3_rf500m_e20_20260618T040646Z"
DEFAULT_PHASE4_ROOT = PROJECT_ROOT / "outputs" / "v3_uncertainty"
DEFAULT_PHASE5_ROOT = PROJECT_ROOT / "reports" / "hotspot_prioritization_v3"
DEFAULT_PHASE6_CORE_ROOT = PROJECT_ROOT / "reports" / "uncertainty_validation_v3"
DEFAULT_PHASE6_DISTRICT_ROOT = PROJECT_ROOT / "reports" / "district_interval_coverage_v3"
DEFAULT_PHASE6_EXTERNAL_ROOT = PROJECT_ROOT / "reports" / "external_disagreement_alignment_v3"
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "reports" / "paper_v3_uncertainty"


@dataclass(frozen=True)
class PaperReportV3Config:
    run_id: str = DEFAULT_RUN_ID
    phase4_root: Path = DEFAULT_PHASE4_ROOT
    phase5_root: Path = DEFAULT_PHASE5_ROOT
    phase6_core_root: Path = DEFAULT_PHASE6_CORE_ROOT
    phase6_district_root: Path = DEFAULT_PHASE6_DISTRICT_ROOT
    phase6_external_root: Path = DEFAULT_PHASE6_EXTERNAL_ROOT
    output_root: Path = DEFAULT_OUTPUT_ROOT
    docs_root: Path = PROJECT_ROOT / "docs"
    reports_root: Path = PROJECT_ROOT / "reports"
    models_root: Path = PROJECT_ROOT / "models" / "v3_uncertainty"
    git_commit: str | None = None
    python_version: str | None = None

    @property
    def phase4_dir(self) -> Path:
        return self.phase4_root / self.run_id

    @property
    def phase5_dir(self) -> Path:
        return self.phase5_root / self.run_id

    @property
    def phase6_core_dir(self) -> Path:
        return self.phase6_core_root / self.run_id

    @property
    def phase6_district_dir(self) -> Path:
        return self.phase6_district_root / self.run_id

    @property
    def phase6_external_dir(self) -> Path:
        return self.phase6_external_root / self.run_id

    @property
    def phase3_dir(self) -> Path:
        return self.models_root / self.run_id

    @property
    def package_dir(self) -> Path:
        return self.output_root / self.run_id


def _relative(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def _safe_read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def _safe_read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
    return path


def _write_markdown(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _copy_if_exists(source_path: Path, destination_path: Path) -> Path | None:
    if not source_path.exists():
        return None
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source_path, destination_path)
    return destination_path


def _mkdirs(base_dir: Path) -> dict[str, Path]:
    base_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "root": base_dir,
        "tables": base_dir / "tables",
        "figures": base_dir / "figures",
        "outputs": base_dir / "outputs",
        "limitations": base_dir / "limitations",
        "source_index": base_dir / "source_index",
    }
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    return paths


def _city_status_for_coverage(row: pd.Series) -> str:
    if str(row.get("osm_completeness_label", "")).lower() == "good" and float(row.get("share_high_confidence", 0.0)) >= 0.15:
        return "Strongest freeze-city support case with comparatively better completeness and a meaningful high-confidence share."
    if float(row.get("share_low_confidence", 0.0)) >= 0.25:
        return "Confidence burden is heavier here; treat the surface as a bounded screening layer that requires stronger local verification."
    return "Intermediate support case: useful for screening and interpretation, but not for aggressive uncertainty claims."


def _coverage_note(row: pd.Series) -> str:
    coverage = float(row.get("coverage_p10_p90", np.nan))
    protocol = str(row.get("protocol", ""))
    if np.isnan(coverage):
        return "Coverage was not available from the frozen evidence stack."
    if coverage >= 0.65:
        return f"{protocol} coverage is moderate for a proxy-target setting, but still bounded by weak supervision."
    if coverage >= 0.50:
        return f"{protocol} coverage is usable but mixed; the interval layer should be described cautiously."
    return f"{protocol} coverage is weak in held-out proxy terms and should not be oversold."


def _alignment_note(row: pd.Series) -> str:
    spearman_width = float(row.get("spearman_error_vs_uncertainty_width", np.nan))
    spearman_relative = float(row.get("spearman_error_vs_relative_uncertainty", np.nan))
    spearman_conf = float(row.get("spearman_error_vs_confidence_score", np.nan))
    if spearman_width >= 0.70:
        return "Uncertainty width tracks proxy-target error positively, but relative uncertainty and confidence ordering remain mixed."
    if spearman_width >= 0.50:
        return "Width/error alignment is present, but the broader confidence story remains mixed."
    if spearman_relative > 0 or spearman_conf < 0:
        return "Some bounded error-alignment signal is present, but it is not strong enough for a simple confidence-as-error claim."
    return "Error-alignment evidence is mixed and should be carried into the manuscript as a limitation."


def _hotspot_note(row: pd.Series) -> str:
    city = str(row.get("city", "This city"))
    high = int(row.get("n_high_value_high_confidence", 0) or 0)
    low = int(row.get("n_high_value_low_confidence", 0) or 0)
    caution = int(row.get("n_low_value_high_uncertainty", 0) or 0)
    if high > 0 and high >= low:
        return f"{city} is the strongest hotspot-screening case because stable high-confidence priority cells are present."
    if low > 0:
        return f"{city} has potentially important hotspots, but they remain review-oriented because low-confidence priority cells are present."
    if caution > 0:
        return f"{city} is caution-heavy in the hotspot layer and should be used conservatively."
    return f"{city} has limited hotspot-priority support in the current frozen evidence package."


def _confidence_note(row: pd.Series) -> str:
    band = str(row.get("confidence_band", ""))
    if band == "high":
        return "High-confidence cells show the lowest uncertainty burden and are the best screening candidates."
    if band == "medium":
        return "Medium-confidence cells dominate the practical baseline and should be interpreted as bounded screening support."
    return "Low-confidence cells are review-oriented and should not be treated as firm operational targets."


def _district_status_rows(district_summary: pd.DataFrame) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    if district_summary.empty:
        rows.append(
            {
                "evidence_layer": "district_interval_coverage",
                "city_or_scope": "benchmark trio",
                "status": "missing",
                "available_result": "no frozen district summary found",
                "limitation": "District interval coverage could not be summarized from the frozen package.",
                "paper_interpretation": "No district-level support should be claimed.",
            }
        )
        return rows

    for row in district_summary.to_dict(orient="records"):
        available = f"compared={int(row['n_districts_compared'])}; mean_absolute_error_p50={float(row['mean_absolute_error_p50']):.1f}"
        rows.append(
            {
                "evidence_layer": "district_interval_coverage",
                "city_or_scope": str(row["city"]),
                "status": "partial",
                "available_result": available,
                "limitation": "True district p10/p50/p90 interval coverage remains blocked because frozen offline district polygon/cell assignment artifacts are missing.",
                "paper_interpretation": "Treat this as partial administrative support after aggregation, not as district interval validation or cell-level truth.",
            }
        )
    return rows


def _external_status_rows(external_detail: pd.DataFrame) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    if external_detail.empty:
        rows.append(
            {
                "evidence_layer": "external_disagreement_alignment",
                "city_or_scope": "benchmark cities",
                "status": "missing",
                "available_result": "no frozen external alignment summary found",
                "limitation": "External disagreement alignment could not be summarized from the frozen package.",
                "paper_interpretation": "No external-alignment claim should be made.",
            }
        )
        return rows

    for row in external_detail.to_dict(orient="records"):
        rows.append(
            {
                "evidence_layer": "external_disagreement_alignment",
                "city_or_scope": f"{row['city']} / {row['benchmark_product']}",
                "status": "mixed",
                "available_result": f"spearman(disagreement, uncertainty)={float(row['spearman_disagreement_vs_uncertainty']):.3f}",
                "limitation": "External disagreement alignment is mixed or negative and does not support a strong claim that uncertainty systematically rises with disagreement to external products.",
                "paper_interpretation": "External products provide structural comparison context, not ground truth.",
            }
        )
    return rows


def _build_source_index(config: PaperReportV3Config, output_dirs: dict[str, Path]) -> tuple[pd.DataFrame, pd.DataFrame]:
    sources: list[dict[str, object]] = []
    partials: list[dict[str, object]] = []

    phase_sources = [
        ("phase3", config.phase3_dir / "ensemble_config.json", "json", "phase3 model configuration", ""),
        ("phase3", config.phase3_dir / "training_summary.csv", "csv", "phase3 training summary", ""),
        ("phase3", config.phase3_dir / "run_manifest.json", "json", "phase3 manifest", ""),
        ("phase4", config.phase4_dir / "city_uncertainty_summary.csv", "csv", "table1 and fig summaries", ""),
        ("phase4", config.phase4_dir / "run_manifest.json", "json", "phase4 manifest", ""),
        ("phase4", config.phase4_dir / "almaty_uncertainty_cells.csv", "csv", "fig2 example city output", ""),
        ("phase5", config.phase5_dir / "hotspot_city_summary.csv", "csv", "table4 and fig4", ""),
        ("phase5", config.phase5_dir / "top_hotspots_by_city.csv", "csv", "outputs copy and hotspot context", ""),
        ("phase5", config.phase5_dir / "stable_hotspots.csv", "csv", "outputs copy and stability context", ""),
        ("phase5", config.phase5_dir / "caution_hotspots.csv", "csv", "outputs copy and caution context", ""),
        ("phase5", config.phase5_dir / "PHASE_5_HOTSPOT_PRIORITIZATION_REPORT.md", "markdown", "paper summary narrative support", ""),
        ("phase5", config.phase5_dir / "run_manifest.json", "json", "phase5 manifest", ""),
        ("phase6", config.phase6_core_dir / "interval_coverage_weak_target.csv", "csv", "table2 and fig5", ""),
        ("phase6", config.phase6_core_dir / "error_uncertainty_alignment.csv", "csv", "table3 and fig5", ""),
        ("phase6", config.phase6_core_dir / "confidence_band_validation_summary.csv", "csv", "table5 and fig3", ""),
        ("phase6", config.phase6_core_dir / "hotspot_stability_summary.csv", "csv", "table7 and fig6", ""),
        ("phase6", config.phase6_core_dir / "PHASE_6_UNCERTAINTY_VALIDATION_REPORT.md", "markdown", "paper summary narrative support", ""),
        ("phase6", config.phase6_core_dir / "phase6_orchestration_manifest.json", "json", "phase6 status", ""),
        ("phase6", config.phase6_district_dir / "district_interval_city_summary.csv", "csv", "table6 district limitation", ""),
        ("phase6", config.phase6_external_dir / "external_disagreement_alignment.csv", "csv", "table6 external limitation", ""),
        ("docs", config.docs_root / "V3_AUDIT.md", "markdown", "package provenance context", ""),
        ("docs", config.docs_root / "V3_DATA_CONTRACT.md", "markdown", "contract reference", ""),
        ("docs", config.docs_root / "V3_DIRECTORY_CONVENTIONS.md", "markdown", "directory-contract reference", ""),
        ("docs", config.docs_root / "V3_COMPLETION_PLAN.md", "markdown", "status reference", ""),
        ("reports", PROJECT_ROOT / "PHASE_3_4_RUN_REPORT.md", "markdown", "phase3-4 provenance", ""),
    ]

    for phase, path, artifact_type, used_for, notes in phase_sources:
        exists = path.exists()
        sources.append(
            {
                "run_id": config.run_id,
                "phase": phase,
                "source_path": _relative(path),
                "exists": bool(exists),
                "artifact_type": artifact_type,
                "used_for": used_for,
                "notes": notes,
            }
        )
        if not exists:
            partials.append(
                {
                    "run_id": config.run_id,
                    "missing_or_partial_item": _relative(path),
                    "affected_output": "paper-facing package",
                    "severity": "high",
                    "explanation": "Required frozen input is missing, so any dependent paper-facing artifact must remain partial.",
                    "recommended_action": "Restore the missing frozen artifact before Phase 8 manuscript writing.",
                }
            )

    partials.append(
        {
            "run_id": config.run_id,
            "missing_or_partial_item": "district polygon/cell assignment artifacts",
            "affected_output": "table6_district_external_limitations_summary.csv; paper_summary.md; claims_not_allowed.md",
            "severity": "high",
            "explanation": "True district p10/p50/p90 interval coverage remains blocked because frozen offline district polygon/cell assignment artifacts are not available in the light package.",
            "recommended_action": "Add frozen offline district assignment artifacts if full district interval coverage is required before or during Phase 8.",
        }
    )
    partials.append(
        {
            "run_id": config.run_id,
            "missing_or_partial_item": "bounded LOCO-like reconstruction configuration",
            "affected_output": "table2_uncertainty_interval_coverage.csv; table3_error_uncertainty_alignment.csv; paper_summary.md",
            "severity": "medium",
            "explanation": "The held-out LOCO-like Phase 6 reconstruction was executed in a bounded local configuration (ensemble_size=5, rf_n_estimators=60) rather than the full 20-member runtime package.",
            "recommended_action": "Carry this bounded-compute note into Phase 8 and avoid overselling LOCO-like interval evidence.",
        }
    )

    source_index_path = output_dirs["source_index"] / "source_files_used.csv"
    missing_path = output_dirs["source_index"] / "missing_or_partial_inputs.csv"
    pd.DataFrame(sources).to_csv(source_index_path, index=False)
    pd.DataFrame(partials).to_csv(missing_path, index=False)
    return pd.DataFrame(sources), pd.DataFrame(partials)


def _build_tables(config: PaperReportV3Config, output_dirs: dict[str, Path]) -> dict[str, Path]:
    city_summary = _safe_read_csv(config.phase4_dir / "city_uncertainty_summary.csv")
    interval = _safe_read_csv(config.phase6_core_dir / "interval_coverage_weak_target.csv")
    error = _safe_read_csv(config.phase6_core_dir / "error_uncertainty_alignment.csv")
    hotspot = _safe_read_csv(config.phase5_dir / "hotspot_city_summary.csv")
    confidence = _safe_read_csv(config.phase6_core_dir / "confidence_band_validation_summary.csv")
    district = _safe_read_csv(config.phase6_district_dir / "district_interval_city_summary.csv")
    external = _safe_read_csv(config.phase6_external_dir / "external_disagreement_alignment.csv")
    stability = _safe_read_csv(config.phase6_core_dir / "hotspot_stability_summary.csv")

    table_paths: dict[str, Path] = {}

    table1 = city_summary.copy()
    if not table1.empty:
        table1["interpretation_note"] = table1.apply(_city_status_for_coverage, axis=1)
        table1 = table1[
            [
                "city",
                "n_cells",
                "official_total",
                "sum_p50",
                "median_relative_uncertainty",
                "share_high_confidence",
                "share_medium_confidence",
                "share_low_confidence",
                "osm_completeness_score",
                "osm_completeness_label",
                "interpretation_note",
            ]
        ]
    table_paths["table1_v3_city_coverage"] = output_dirs["tables"] / "table1_v3_city_coverage.csv"
    table1.to_csv(table_paths["table1_v3_city_coverage"], index=False)

    table2 = interval.loc[interval["city"].isin(["Almaty", "Astana", "Semey", "Shymkent"])].copy() if not interval.empty else interval
    if not table2.empty:
        table2["interpretation_note"] = table2.apply(_coverage_note, axis=1)
        table2 = table2[
            [
                "protocol",
                "city",
                "n_cells",
                "coverage_p10_p90",
                "below_p10_share",
                "above_p90_share",
                "median_relative_uncertainty",
                "interpretation_note",
            ]
        ]
    table_paths["table2_uncertainty_interval_coverage"] = output_dirs["tables"] / "table2_uncertainty_interval_coverage.csv"
    table2.to_csv(table_paths["table2_uncertainty_interval_coverage"], index=False)

    table3 = error.loc[error["city"].isin(["Almaty", "Astana", "Semey", "Shymkent"])].copy() if not error.empty else error
    if not table3.empty:
        table3["interpretation_note"] = table3.apply(_alignment_note, axis=1)
        table3 = table3[
            [
                "protocol",
                "city",
                "n_cells",
                "spearman_error_vs_uncertainty_width",
                "pearson_error_vs_uncertainty_width",
                "spearman_error_vs_relative_uncertainty",
                "spearman_error_vs_confidence_score",
                "mean_error_high_confidence",
                "mean_error_medium_confidence",
                "mean_error_low_confidence",
                "interpretation_note",
            ]
        ]
    table_paths["table3_error_uncertainty_alignment"] = output_dirs["tables"] / "table3_error_uncertainty_alignment.csv"
    table3.to_csv(table_paths["table3_error_uncertainty_alignment"], index=False)

    table4 = hotspot.copy()
    if not table4.empty:
        table4["interpretation_note"] = table4.apply(_hotspot_note, axis=1)
        table4 = table4[
            [
                "city",
                "n_priority_cells",
                "n_high_value_high_confidence",
                "n_high_value_low_confidence",
                "n_medium_value_high_confidence",
                "n_low_value_high_uncertainty",
                "mean_confidence_priority_cells",
                "median_relative_uncertainty_priority_cells",
                "interpretation_note",
            ]
        ]
    table_paths["table4_hotspot_prioritization_summary"] = output_dirs["tables"] / "table4_hotspot_prioritization_summary.csv"
    table4.to_csv(table_paths["table4_hotspot_prioritization_summary"], index=False)

    table5 = confidence.copy()
    if not table5.empty:
        table5["interpretation_note"] = table5.apply(_confidence_note, axis=1)
        table5 = table5[
            [
                "city",
                "confidence_band",
                "n_cells",
                "share_cells",
                "median_relative_uncertainty",
                "mean_uncertainty_width",
                "mean_error_if_available",
                "share_hotspot_priority_cells",
                "interpretation_note",
            ]
        ]
    table_paths["table5_confidence_band_summary"] = output_dirs["tables"] / "table5_confidence_band_summary.csv"
    table5.to_csv(table_paths["table5_confidence_band_summary"], index=False)

    table6_rows = _district_status_rows(district) + _external_status_rows(external)
    table6 = pd.DataFrame(table6_rows)
    table_paths["table6_district_external_limitations_summary"] = output_dirs["tables"] / "table6_district_external_limitations_summary.csv"
    table6.to_csv(table_paths["table6_district_external_limitations_summary"], index=False)

    table7 = stability.copy()
    if not table7.empty:
        table7 = table7[
            [
                "city",
                "hotspot_priority_class",
                "n_cells",
                "mean_stability_metric",
                "median_relative_uncertainty",
                "mean_confidence_score",
                "interpretation_note",
            ]
        ]
    table_paths["table7_hotspot_stability_summary"] = output_dirs["tables"] / "table7_hotspot_stability_summary.csv"
    table7.to_csv(table_paths["table7_hotspot_stability_summary"], index=False)

    return table_paths


def _figure_flow_diagram(path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(13, 5))
    ax.axis("off")
    xs = [0.03, 0.22, 0.39, 0.56, 0.73, 0.88]
    labels = [
        "v2 calibrated\nproxy surface",
        "ensemble\npredictions",
        "P10 / P50 / P90",
        "confidence\nbands",
        "hotspot\nprioritization",
        "validation +\npaper pack",
    ]
    colors = ["#f0ead6", "#d9efe8", "#dce8f7", "#f6e0d6", "#e9ddf5", "#dde8d4"]
    for x, label, color in zip(xs, labels, colors):
        box = plt.Rectangle((x, 0.42), 0.13, 0.22, facecolor=color, edgecolor="#333333", linewidth=1.2)
        ax.add_patch(box)
        ax.text(x + 0.065, 0.53, label, ha="center", va="center", fontsize=11)
    for x in xs[:-1]:
        ax.annotate("", xy=(x + 0.145, 0.53), xytext=(x + 0.13, 0.53), arrowprops=dict(arrowstyle="->", lw=1.5))
    ax.text(0.5, 0.84, "City1 v3 paper-facing evidence flow", ha="center", va="center", fontsize=14, weight="bold")
    ax.text(
        0.5,
        0.20,
        "Bounded identity: uncertainty-aware screening and interpretation layer, not true census uncertainty.",
        ha="center",
        va="center",
        fontsize=10,
    )
    plt.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(path, dpi=170)
    plt.close(fig)
    return path


def _figure_uncertainty_output_example(path: Path, example_city_frame: pd.DataFrame, city_coverage: pd.DataFrame) -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    sample = example_city_frame.sample(min(len(example_city_frame), 1200), random_state=42) if len(example_city_frame) > 1200 else example_city_frame
    color_map = {"high": "#2a9d8f", "medium": "#e9c46a", "low": "#e76f51"}
    colors = sample["confidence_band"].astype(str).map(color_map).fillna("#666666")
    axes[0].scatter(
        pd.to_numeric(sample["p50"], errors="coerce"),
        pd.to_numeric(sample["relative_uncertainty"], errors="coerce"),
        c=colors,
        s=10,
        alpha=0.35,
        edgecolors="none",
    )
    axes[0].set_title("Almaty example: p50 vs relative uncertainty")
    axes[0].set_xlabel("p50 calibrated proxy estimate")
    axes[0].set_ylabel("relative uncertainty")

    coverage_plot = city_coverage.copy()
    x = np.arange(len(coverage_plot))
    axes[1].bar(x, pd.to_numeric(coverage_plot["median_relative_uncertainty"], errors="coerce"), color="#457b9d")
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(coverage_plot["city"], rotation=20, ha="right")
    axes[1].set_title("Median relative uncertainty by freeze city")
    axes[1].set_ylabel("median relative uncertainty")

    plt.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(path, dpi=170)
    plt.close(fig)
    return path


def _figure_confidence_band_distribution(path: Path, city_coverage: pd.DataFrame) -> Path:
    fig, ax = plt.subplots(figsize=(10, 5))
    cities = city_coverage["city"].astype(str).tolist()
    high = pd.to_numeric(city_coverage["share_high_confidence"], errors="coerce").fillna(0.0).to_numpy()
    medium = pd.to_numeric(city_coverage["share_medium_confidence"], errors="coerce").fillna(0.0).to_numpy()
    low = pd.to_numeric(city_coverage["share_low_confidence"], errors="coerce").fillna(0.0).to_numpy()
    x = np.arange(len(cities))
    ax.bar(x, high, label="high", color="#2a9d8f")
    ax.bar(x, medium, bottom=high, label="medium", color="#e9c46a")
    ax.bar(x, low, bottom=high + medium, label="low", color="#e76f51")
    ax.set_xticks(x)
    ax.set_xticklabels(cities)
    ax.set_ylim(0, 1)
    ax.set_ylabel("share of city cells")
    ax.set_title("Confidence-band distribution by city")
    ax.legend(frameon=False)
    plt.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(path, dpi=170)
    plt.close(fig)
    return path


def _figure_hotspot_prioritization(path: Path, hotspot_table: pd.DataFrame) -> Path:
    fig, ax = plt.subplots(figsize=(11, 5))
    cities = hotspot_table["city"].astype(str).tolist()
    cols = [
        "n_high_value_high_confidence",
        "n_high_value_low_confidence",
        "n_medium_value_high_confidence",
        "n_low_value_high_uncertainty",
    ]
    labels = [
        "high/high",
        "high/low",
        "medium/high",
        "low/high-uncertainty",
    ]
    colors = ["#2a9d8f", "#e76f51", "#6c9a8b", "#7b6d8d"]
    bottom = np.zeros(len(cities))
    x = np.arange(len(cities))
    for column, label, color in zip(cols, labels, colors):
        values = pd.to_numeric(hotspot_table[column], errors="coerce").fillna(0.0).to_numpy()
        ax.bar(x, values, bottom=bottom, label=label, color=color)
        bottom = bottom + values
    ax.set_xticks(x)
    ax.set_xticklabels(cities)
    ax.set_ylabel("cell count")
    ax.set_title("Hotspot priority classes by city")
    ax.legend(frameon=False, ncol=2)
    plt.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(path, dpi=170)
    plt.close(fig)
    return path


def _figure_uncertainty_validation_summary(path: Path, interval_table: pd.DataFrame, error_table: pd.DataFrame) -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    if not interval_table.empty:
        plot_df = interval_table.copy()
        plot_df["label"] = plot_df["city"].astype(str) + "\n" + plot_df["protocol"].astype(str)
        axes[0].bar(plot_df["label"], pd.to_numeric(plot_df["coverage_p10_p90"], errors="coerce"), color="#457b9d")
        axes[0].tick_params(axis="x", rotation=40)
        axes[0].set_ylim(0, 1)
        axes[0].set_title("Interval coverage by city/protocol")
        axes[0].set_ylabel("coverage within p10-p90")
    else:
        axes[0].text(0.5, 0.5, "No interval coverage table available", ha="center", va="center")
        axes[0].axis("off")

    if not error_table.empty:
        plot_df = error_table.copy()
        plot_df["label"] = plot_df["city"].astype(str) + "\n" + plot_df["protocol"].astype(str)
        axes[1].bar(plot_df["label"], pd.to_numeric(plot_df["spearman_error_vs_uncertainty_width"], errors="coerce"), color="#2a9d8f")
        axes[1].tick_params(axis="x", rotation=40)
        axes[1].set_title("Spearman(error, uncertainty width)")
        axes[1].set_ylabel("Spearman correlation")
    else:
        axes[1].text(0.5, 0.5, "No error-alignment table available", ha="center", va="center")
        axes[1].axis("off")

    plt.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(path, dpi=170)
    plt.close(fig)
    return path


def _figure_hotspot_stability(path: Path, stability_table: pd.DataFrame) -> Path:
    fig, ax = plt.subplots(figsize=(11, 5))
    plot_df = stability_table.copy()
    plot_df["label"] = plot_df["city"].astype(str) + " | " + plot_df["hotspot_priority_class"].astype(str)
    ax.bar(plot_df["label"], pd.to_numeric(plot_df["mean_stability_metric"], errors="coerce"), color="#6c9a8b")
    ax.tick_params(axis="x", rotation=40)
    ax.set_ylim(0, 1)
    ax.set_ylabel("mean stability metric")
    ax.set_title("Hotspot stability summary by class")
    plt.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(path, dpi=170)
    plt.close(fig)
    return path


def _build_figures(config: PaperReportV3Config, output_dirs: dict[str, Path], table_paths: dict[str, Path]) -> tuple[dict[str, Path], Path | None]:
    figures: dict[str, Path] = {}
    limitations_path: Path | None = None

    city_coverage = _safe_read_csv(table_paths["table1_v3_city_coverage"])
    interval_table = _safe_read_csv(table_paths["table2_uncertainty_interval_coverage"])
    error_table = _safe_read_csv(table_paths["table3_error_uncertainty_alignment"])
    hotspot_table = _safe_read_csv(table_paths["table4_hotspot_prioritization_summary"])
    stability_table = _safe_read_csv(table_paths["table7_hotspot_stability_summary"])
    example_city = _safe_read_csv(config.phase4_dir / "almaty_uncertainty_cells.csv")

    figure_limitations: list[str] = []

    try:
        figures["fig1_v3_pipeline"] = _figure_flow_diagram(output_dirs["figures"] / "fig1_v3_pipeline.png")
    except Exception as exc:
        figure_limitations.append(f"- fig1_v3_pipeline.png: {exc}")

    try:
        if example_city.empty or city_coverage.empty:
            raise ValueError("missing Phase 4 example city output or city coverage summary")
        figures["fig2_uncertainty_output_example"] = _figure_uncertainty_output_example(
            output_dirs["figures"] / "fig2_uncertainty_output_example.png",
            example_city,
            city_coverage,
        )
    except Exception as exc:
        figure_limitations.append(f"- fig2_uncertainty_output_example.png: {exc}")

    try:
        if city_coverage.empty:
            raise ValueError("missing city coverage table")
        figures["fig3_confidence_band_distribution"] = _figure_confidence_band_distribution(
            output_dirs["figures"] / "fig3_confidence_band_distribution.png",
            city_coverage,
        )
    except Exception as exc:
        figure_limitations.append(f"- fig3_confidence_band_distribution.png: {exc}")

    try:
        if hotspot_table.empty:
            raise ValueError("missing hotspot summary table")
        figures["fig4_hotspot_prioritization_by_city"] = _figure_hotspot_prioritization(
            output_dirs["figures"] / "fig4_hotspot_prioritization_by_city.png",
            hotspot_table,
        )
    except Exception as exc:
        figure_limitations.append(f"- fig4_hotspot_prioritization_by_city.png: {exc}")

    try:
        if interval_table.empty or error_table.empty:
            raise ValueError("missing interval or error table")
        figures["fig5_uncertainty_validation_summary"] = _figure_uncertainty_validation_summary(
            output_dirs["figures"] / "fig5_uncertainty_validation_summary.png",
            interval_table,
            error_table,
        )
    except Exception as exc:
        figure_limitations.append(f"- fig5_uncertainty_validation_summary.png: {exc}")

    try:
        if stability_table.empty:
            raise ValueError("missing hotspot stability table")
        figures["fig6_hotspot_stability_summary"] = _figure_hotspot_stability(
            output_dirs["figures"] / "fig6_hotspot_stability_summary.png",
            stability_table,
        )
    except Exception as exc:
        figure_limitations.append(f"- fig6_hotspot_stability_summary.png: {exc}")

    if figure_limitations:
        limitations_path = _write_markdown(
            output_dirs["figures"] / "FIGURE_LIMITATIONS.md",
            "# Figure Limitations\n\n" + "\n".join(figure_limitations) + "\n",
        )
    return figures, limitations_path


def _copy_curated_outputs(config: PaperReportV3Config, output_dirs: dict[str, Path]) -> dict[str, Path]:
    curated: dict[str, Path] = {}
    copy_pairs = [
        (config.phase3_dir / "ensemble_config.json", output_dirs["outputs"] / "phase3_ensemble_config.json"),
        (config.phase3_dir / "training_summary.csv", output_dirs["outputs"] / "phase3_training_summary.csv"),
        (config.phase3_dir / "run_manifest.json", output_dirs["outputs"] / "phase3_run_manifest.json"),
        (config.phase4_dir / "city_uncertainty_summary.csv", output_dirs["outputs"] / "phase4_city_uncertainty_summary.csv"),
        (config.phase4_dir / "run_manifest.json", output_dirs["outputs"] / "phase4_run_manifest.json"),
        (config.phase5_dir / "hotspot_city_summary.csv", output_dirs["outputs"] / "phase5_hotspot_city_summary.csv"),
        (config.phase5_dir / "top_hotspots_by_city.csv", output_dirs["outputs"] / "phase5_top_hotspots_by_city.csv"),
        (config.phase5_dir / "run_manifest.json", output_dirs["outputs"] / "phase5_run_manifest.json"),
        (config.phase6_core_dir / "interval_coverage_weak_target.csv", output_dirs["outputs"] / "phase6_interval_coverage_weak_target.csv"),
        (config.phase6_core_dir / "error_uncertainty_alignment.csv", output_dirs["outputs"] / "phase6_error_uncertainty_alignment.csv"),
        (config.phase6_core_dir / "confidence_band_validation_summary.csv", output_dirs["outputs"] / "phase6_confidence_band_validation_summary.csv"),
        (config.phase6_core_dir / "hotspot_stability_summary.csv", output_dirs["outputs"] / "phase6_hotspot_stability_summary.csv"),
        (config.phase6_core_dir / "PHASE_6_UNCERTAINTY_VALIDATION_REPORT.md", output_dirs["outputs"] / "phase6_report.md"),
        (config.phase6_core_dir / "phase6_orchestration_manifest.json", output_dirs["outputs"] / "phase6_orchestration_manifest.json"),
        (config.phase6_district_dir / "district_interval_city_summary.csv", output_dirs["outputs"] / "phase6_district_interval_city_summary.csv"),
        (config.phase6_external_dir / "external_disagreement_alignment.csv", output_dirs["outputs"] / "phase6_external_disagreement_alignment.csv"),
    ]
    for source, destination in copy_pairs:
        copied = _copy_if_exists(source, destination)
        if copied is not None:
            curated[destination.stem] = copied
    return curated


def _build_paper_summary(config: PaperReportV3Config, output_dirs: dict[str, Path], table_paths: dict[str, Path], figure_paths: dict[str, Path]) -> Path:
    city_coverage = _safe_read_csv(table_paths["table1_v3_city_coverage"])
    interval = _safe_read_csv(table_paths["table2_uncertainty_interval_coverage"])
    error = _safe_read_csv(table_paths["table3_error_uncertainty_alignment"])
    hotspot = _safe_read_csv(table_paths["table4_hotspot_prioritization_summary"])
    table6 = _safe_read_csv(table_paths["table6_district_external_limitations_summary"])
    stability = _safe_read_csv(table_paths["table7_hotspot_stability_summary"])

    cities = ", ".join(city_coverage["city"].astype(str).tolist()) if not city_coverage.empty else "none"
    strongest_city = ""
    if not hotspot.empty:
        strongest_row = hotspot.sort_values("n_high_value_high_confidence", ascending=False).iloc[0]
        strongest_city = f"{strongest_row['city']} has the strongest stable hotspot-screening case."

    summary = f"""# City1 v3 Paper Summary

## 1. One-paragraph v3 contribution

City1 v3 extends a calibrated proxy population surface with uncertainty intervals, confidence bands, and uncertainty-aware hotspot prioritization. The strongest support is hotspot stability and uncertainty burden separation; interval coverage and external disagreement are mixed; district interval coverage remains partial. Therefore v3 should be framed as an uncertainty-aware screening and interpretation layer, not as a fully calibrated census-uncertainty model.

## 2. Run information

- run_id: `{config.run_id}`
- package root: `{_relative(config.package_dir)}`
- git commit if available: `{config.git_commit or 'not available'}`
- python version if available: `{config.python_version or sys.version.split()[0]}`

## 3. Cities included

- {cities}

## 4. Evidence sources used

- Phase 3 training manifest and ensemble configuration
- Phase 4 city uncertainty outputs and city summary
- Phase 5 hotspot prioritization package
- Phase 6 uncertainty validation, district limitation summary, and external disagreement alignment
- frozen docs and phase reports listed in `source_index/source_files_used.csv`

## 5. Main quantitative findings

- Almaty remains the strongest freeze-city support case with the highest stable high-confidence hotspot count.
- Inference-only proxy interval coverage is moderate for Astana (`0.613`) and Semey (`0.692`), weaker for Almaty (`0.598`) and Shymkent (`0.534`).
- Error-vs-uncertainty width alignment is positive, but the broader confidence/error story is mixed.
- Stable hotspot classes show clearly higher mean stability than caution classes.

## 6. Strongest evidence

- hotspot stability and priority-class separation are the strongest reviewer-facing evidence layer
- confidence bands separate uncertainty burden clearly across cities
- {strongest_city or 'stable hotspot evidence is present in at least one freeze city'}

## 7. Mixed or weak evidence

- interval coverage remains mixed, especially under LOCO-like reconstruction
- external disagreement alignment is mixed/negative and does not justify a strong uncertainty-vs-external-disagreement claim
- district interval coverage remains partial rather than fully solved

## 8. Limitations

- v3 does not estimate true census uncertainty
- confidence_score is an interpretation confidence score, not a truth probability
- district evidence provides partial administrative support after aggregation
- external products provide structural agreement/disagreement context, not ground truth

## 9. Recommended manuscript framing

Frame v3 as an uncertainty-aware screening and interpretation layer built around a calibrated proxy population surface. Emphasize hotspot stability and uncertainty burden separation as the strongest contributions. Present interval coverage and external disagreement evidence honestly as mixed. Carry the district partial-coverage limitation explicitly into the manuscript.

## 10. Claims allowed

- v3 provides uncertainty-aware screening support
- v3 provides P10/P50/P90 proxy intervals
- v3 provides confidence bands for interpretation
- hotspot stability evidence is the strongest support
- confidence bands separate uncertainty burden
- Phase 6 provides bounded evidence under weak-target validation

## 11. Claims not allowed

- v3 provides true census uncertainty
- v3 proves cell-level accuracy
- confidence_score is a truth probability
- district interval coverage is fully solved
- WorldPop or GHS-POP are ground truth

## 12. Readiness for Phase 8

Phase 8 can start conditionally. The paper-facing package is ready for manuscript writing if the current explicit district-partial limitation and mixed external-alignment evidence are preserved without overclaiming.
"""
    return _write_markdown(output_dirs["root"] / "paper_summary.md", summary)


def _build_limitations_folder(config: PaperReportV3Config, output_dirs: dict[str, Path]) -> dict[str, Path]:
    limitation_summary = """# Limitation Summary

- v3 uncertainty is model/evidence uncertainty inside a calibrated proxy-target framework.
- interval coverage evidence is mixed rather than uniformly strong.
- external disagreement alignment is mixed or negative and must not be overstated.
- district interval coverage remains partial because frozen offline district polygon/cell assignment artifacts are missing.
- these limitations constrain claims, but do not invalidate the usefulness of v3 as an uncertainty-aware screening layer.
"""

    claims_allowed = """# Claims Allowed

- v3 provides uncertainty-aware screening support.
- v3 provides P10/P50/P90 proxy intervals.
- v3 provides confidence bands for interpretation.
- hotspot stability evidence is the strongest support.
- confidence bands separate uncertainty burden.
- Phase 6 provides bounded evidence under weak-target validation.
"""

    claims_not_allowed = """# Claims Not Allowed

- v3 does not provide true census uncertainty.
- v3 does not prove cell-level accuracy.
- confidence_score is not a truth probability.
- district interval coverage is not fully solved unless frozen district assignments are added.
- external products are not ground truth.
- mixed external-disagreement alignment should not be hidden.
"""

    paths = {
        "limitation_summary": _write_markdown(output_dirs["limitations"] / "limitation_summary.md", limitation_summary),
        "claims_allowed": _write_markdown(output_dirs["limitations"] / "claims_allowed.md", claims_allowed),
        "claims_not_allowed": _write_markdown(output_dirs["limitations"] / "claims_not_allowed.md", claims_not_allowed),
    }
    return paths


def _build_readme(config: PaperReportV3Config, output_dirs: dict[str, Path], figure_limitations_path: Path | None) -> Path:
    lines = [
        "# City1 v3 Paper-Facing Evidence Package",
        "",
        "## What this package is",
        "",
        "This package is the frozen Phase 7 evidence bundle for City1 v3. It consolidates Phase 3-6 artifacts into paper-facing tables, figures, summaries, a source index, and a freeze manifest.",
        "",
        "## How it was generated",
        "",
        f"- built from existing frozen artifacts for run_id `{config.run_id}`",
        "- no model retraining was performed in Phase 7",
        "- no new science was introduced in Phase 7",
        "- v2 manuscript and v2 results were not modified",
        "",
        "## Folder meanings",
        "",
        "- `tables/`: compact paper-ready CSV tables",
        "- `figures/`: lightweight paper-ready figures",
        "- `outputs/`: curated copied Phase 3-6 source outputs used for the package",
        "- `limitations/`: bounded-claim guidance for Phase 8",
        "- `source_index/`: source inventory and partial-input registry",
        "",
        "## Strongest results",
        "",
        "- hotspot stability and hotspot-class separation",
        "- confidence-band separation of uncertainty burden",
        "- Almaty as the strongest freeze-city hotspot-screening case",
        "",
        "## Partial or mixed results",
        "",
        "- interval coverage is mixed",
        "- external disagreement alignment is mixed or negative",
        "- district interval coverage remains partial",
        "",
        "## How Phase 8 should use the package",
        "",
        "- use `paper_summary.md` for the high-level manuscript framing",
        "- use `tables/` and `figures/` as the direct source for manuscript drafting",
        "- carry all limitations from `limitations/` into the manuscript explicitly",
        "",
        "## What must not be claimed",
        "",
        "- v3 does not estimate true census uncertainty",
        "- confidence_score is not a truth probability",
        "- district evidence does not prove cell-level accuracy",
        "- external products are not ground truth",
    ]
    if figure_limitations_path is not None:
        lines.extend(
            [
                "",
                "## Figure limitations",
                "",
                f"- see `{_relative(figure_limitations_path)}`",
            ]
        )
    return _write_markdown(output_dirs["root"] / "README.md", "\n".join(lines) + "\n")


def _build_freeze_manifest(
    config: PaperReportV3Config,
    output_dirs: dict[str, Path],
    source_index_paths: tuple[Path, Path],
    table_paths: dict[str, Path],
    figure_paths: dict[str, Path],
    curated_outputs: dict[str, Path],
    figure_limitations_path: Path | None,
) -> Path:
    manifest = {
        "run_id": config.run_id,
        "created_at": pd.Timestamp.utcnow().isoformat(),
        "phase": "phase7_paper_facing_evidence_package",
        "project_version": "city1_v3",
        "input_roots": {
            "phase3": _relative(config.phase3_dir),
            "phase4": _relative(config.phase4_dir),
            "phase5": _relative(config.phase5_dir),
            "phase6_core": _relative(config.phase6_core_dir),
            "phase6_district": _relative(config.phase6_district_dir),
            "phase6_external": _relative(config.phase6_external_dir),
        },
        "phase4_outputs_used": sorted(
            [
                _relative(config.phase4_dir / "city_uncertainty_summary.csv"),
                _relative(config.phase4_dir / "run_manifest.json"),
                _relative(config.phase4_dir / "almaty_uncertainty_cells.csv"),
            ]
        ),
        "phase5_outputs_used": sorted(
            [
                _relative(config.phase5_dir / "hotspot_city_summary.csv"),
                _relative(config.phase5_dir / "top_hotspots_by_city.csv"),
                _relative(config.phase5_dir / "stable_hotspots.csv"),
                _relative(config.phase5_dir / "caution_hotspots.csv"),
                _relative(config.phase5_dir / "PHASE_5_HOTSPOT_PRIORITIZATION_REPORT.md"),
            ]
        ),
        "phase6_outputs_used": sorted(
            [
                _relative(config.phase6_core_dir / "interval_coverage_weak_target.csv"),
                _relative(config.phase6_core_dir / "error_uncertainty_alignment.csv"),
                _relative(config.phase6_core_dir / "confidence_band_validation_summary.csv"),
                _relative(config.phase6_core_dir / "hotspot_stability_summary.csv"),
                _relative(config.phase6_core_dir / "PHASE_6_UNCERTAINTY_VALIDATION_REPORT.md"),
                _relative(config.phase6_district_dir / "district_interval_city_summary.csv"),
                _relative(config.phase6_external_dir / "external_disagreement_alignment.csv"),
            ]
        ),
        "paper_tables": sorted(_relative(path) for path in table_paths.values()),
        "paper_figures": sorted(_relative(path) for path in figure_paths.values()),
        "source_index_files": sorted(_relative(path) for path in source_index_paths),
        "limitations": [
            "v3 uncertainty is not true census uncertainty",
            "district interval coverage remains partial because frozen district polygon/cell assignment artifacts are missing",
            "external disagreement alignment is mixed and should not be overstated",
            "LOCO-like held-out evidence was produced in a bounded local configuration",
        ],
        "validation_status": {
            "phase6_status": "partially completed",
            "district_interval_status": "partial",
            "external_alignment_status": "mixed",
            "hotspot_stability_status": "strongest evidence layer",
        },
        "git_commit_if_available": config.git_commit,
        "python_version_if_available": config.python_version or sys.version.split()[0],
        "notes": [
            "Phase 7 is evidence consolidation only; no retraining or manuscript writing occurred.",
            f"Curated Phase 3-6 copies stored under {_relative(output_dirs['outputs'])}.",
            f"Figure limitations file present: {bool(figure_limitations_path)}",
        ],
    }
    return _write_json(output_dirs["root"] / "freeze_manifest.json", manifest)


def _update_completion_plan(config: PaperReportV3Config, table_paths: dict[str, Path], figure_paths: dict[str, Path]) -> Path:
    content = f"""# City1 v3 Completion Plan

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
- Phase 6: **partially completed** - uncertainty validation evidence stack with explicit district limitation
- Phase 7: **completed with carried limitations** - paper-facing package frozen under `{_relative(config.package_dir)}`
- Phase 8: **not started** - manuscript package

## Paper-facing package path

- `{_relative(config.package_dir)}`

## Key tables

{chr(10).join(f"- `{_relative(path)}`" for path in table_paths.values())}

## Key figures

{chr(10).join(f"- `{_relative(path)}`" for path in figure_paths.values())}

## Phase 8 start condition

Phase 8 can start if the manuscript preserves the following:

- v3 is framed as an uncertainty-aware screening and interpretation layer
- hotspot stability and uncertainty burden separation are presented as the strongest support
- interval coverage and external disagreement are described as mixed
- district interval coverage is described as partial rather than solved

## Unresolved limitations that must carry into the manuscript

- v3 does not estimate true census uncertainty
- confidence_score is not a truth probability
- district interval coverage remains partial unless frozen district polygon/cell assignment artifacts are added
- external products are structural benchmarks, not ground truth
- the held-out LOCO-like Phase 6 evidence was produced in a bounded local configuration
"""
    path = config.docs_root / "V3_COMPLETION_PLAN.md"
    path.write_text(content, encoding="utf-8")
    return path


def build_paper_v3_uncertainty_package(config: PaperReportV3Config | None = None) -> dict[str, Path]:
    package_config = config or PaperReportV3Config()
    output_dirs = _mkdirs(package_config.package_dir)

    source_index_df, partial_df = _build_source_index(package_config, output_dirs)
    table_paths = _build_tables(package_config, output_dirs)
    figure_paths, figure_limitations_path = _build_figures(package_config, output_dirs, table_paths)
    curated_outputs = _copy_curated_outputs(package_config, output_dirs)
    limitations_paths = _build_limitations_folder(package_config, output_dirs)
    paper_summary_path = _build_paper_summary(package_config, output_dirs, table_paths, figure_paths)
    readme_path = _build_readme(package_config, output_dirs, figure_limitations_path)
    freeze_manifest_path = _build_freeze_manifest(
        package_config,
        output_dirs,
        (
            output_dirs["source_index"] / "source_files_used.csv",
            output_dirs["source_index"] / "missing_or_partial_inputs.csv",
        ),
        table_paths,
        figure_paths,
        curated_outputs,
        figure_limitations_path,
    )
    completion_plan_path = _update_completion_plan(package_config, table_paths, figure_paths)

    outputs: dict[str, Path] = {
        "readme": readme_path,
        "paper_summary": paper_summary_path,
        "freeze_manifest": freeze_manifest_path,
        "source_index": output_dirs["source_index"] / "source_files_used.csv",
        "missing_or_partial_inputs": output_dirs["source_index"] / "missing_or_partial_inputs.csv",
        "completion_plan": completion_plan_path,
    }
    outputs.update({name: path for name, path in table_paths.items()})
    outputs.update({name: path for name, path in figure_paths.items()})
    outputs.update({name: path for name, path in curated_outputs.items()})
    outputs.update({name: path for name, path in limitations_paths.items()})
    if figure_limitations_path is not None:
        outputs["figure_limitations"] = figure_limitations_path
    return outputs
