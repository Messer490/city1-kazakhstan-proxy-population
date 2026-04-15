from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from .paths import MODELS_DIR, PROJECT_ROOT


DEFAULT_STATUS_CSV = PROJECT_ROOT / "data" / "external" / "city_status_registry_v2.csv"
DEFAULT_QA_CITY_SUMMARY_CSV = PROJECT_ROOT / "reports" / "feature_qa_stage1_batch1" / "city_summary.csv"
DEFAULT_GRID_BENCHMARK_DIR = PROJECT_ROOT / "reports" / "grid_size_benchmark_v2_batch1"
DEFAULT_OSM_COMPLETENESS_DIR = PROJECT_ROOT / "reports" / "osm_completeness_v2"
DEFAULT_DISTRICT_BENCHMARK_DIR = PROJECT_ROOT / "reports" / "district_benchmark_v2"
DEFAULT_EXTERNAL_BENCHMARK_DIR = PROJECT_ROOT / "reports" / "external_benchmark_v2"
DEFAULT_ABLATION_DIR = PROJECT_ROOT / "reports" / "ablation_v2"
DEFAULT_QUALITATIVE_VALIDATION_DIR = PROJECT_ROOT / "reports" / "qualitative_validation_v2"
DEFAULT_INFERENCE_RUNS_DIR = PROJECT_ROOT / "data" / "processed" / "inference_runs"
DEFAULT_METRICS_DIR = MODELS_DIR / "trained_stage1_batch1"


@dataclass(frozen=True)
class PaperReportConfig:
    status_csv: Path = DEFAULT_STATUS_CSV
    qa_city_summary_csv: Path = DEFAULT_QA_CITY_SUMMARY_CSV
    metrics_dir: Path = DEFAULT_METRICS_DIR
    grid_benchmark_dir: Path = DEFAULT_GRID_BENCHMARK_DIR
    osm_completeness_dir: Path = DEFAULT_OSM_COMPLETENESS_DIR
    district_benchmark_dir: Path = DEFAULT_DISTRICT_BENCHMARK_DIR
    external_benchmark_dir: Path = DEFAULT_EXTERNAL_BENCHMARK_DIR
    ablation_dir: Path = DEFAULT_ABLATION_DIR
    qualitative_validation_dir: Path = DEFAULT_QUALITATIVE_VALIDATION_DIR
    inference_runs_dir: Path = DEFAULT_INFERENCE_RUNS_DIR
    output_dir: Path = PROJECT_ROOT / "reports" / "paper_v2_baseline"
    example_city_slugs: tuple[str, ...] = ("almaty", "semey")


def _load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def _require_file(path: Path) -> Path:
    if not path.exists():
        raise FileNotFoundError(f"Required paper report input was not found: {path}")
    return path


def _require_csv(path: Path) -> pd.DataFrame:
    _require_file(path)
    return pd.read_csv(path)


def _copy_required_file(source_path: Path, destination_path: Path) -> Path:
    _require_file(source_path)
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source_path, destination_path)
    return destination_path


def _aggregate_training_metrics(metrics_dir: Path) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for path in sorted(metrics_dir.glob("*_fold_metrics.csv")):
        frame = pd.read_csv(path)
        stem = path.name.replace("_fold_metrics.csv", "")
        if "__" in stem:
            model_name, validation_protocol = stem.split("__", 1)
        else:
            model_name, validation_protocol = stem, "leave_one_city_out"

        rows.append(
            {
                "model_name": model_name,
                "validation_protocol": validation_protocol,
                "folds": int(len(frame)),
                "mean_calibrated_mae": float(frame["calibrated_mae"].mean()),
                "mean_calibrated_rmse": float(frame["calibrated_rmse"].mean()),
                "mean_calibrated_r2": float(frame["calibrated_r2"].mean()),
                "median_calibrated_rmse": float(frame["calibrated_rmse"].median()),
                "median_calibrated_r2": float(frame["calibrated_r2"].median()),
            }
        )

    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values(
        ["validation_protocol", "mean_calibrated_rmse", "mean_calibrated_mae"],
        ascending=[True, True, True],
    ).reset_index(drop=True)


def _plot_model_comparison(metrics_df: pd.DataFrame, output_path: Path) -> None:
    if metrics_df.empty:
        return

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    display = metrics_df.copy()
    display["model_protocol"] = display["model_name"] + "\n" + display["validation_protocol"]

    sns.barplot(
        data=display,
        x="model_protocol",
        y="mean_calibrated_rmse",
        ax=axes[0],
        color="#2563eb",
    )
    axes[0].set_title("Calibrated RMSE by Model / Protocol")
    axes[0].set_xlabel("")
    axes[0].set_ylabel("Mean calibrated RMSE")
    axes[0].tick_params(axis="x", labelrotation=20)

    sns.barplot(
        data=display,
        x="model_protocol",
        y="mean_calibrated_r2",
        ax=axes[1],
        color="#059669",
    )
    axes[1].set_title("Calibrated R2 by Model / Protocol")
    axes[1].set_xlabel("")
    axes[1].set_ylabel("Mean calibrated R2")
    axes[1].tick_params(axis="x", labelrotation=20)

    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def _plot_city_status(status_df: pd.DataFrame, output_path: Path) -> None:
    if status_df.empty or "status_label" not in status_df.columns:
        return

    counts = status_df["status_label"].value_counts().reset_index()
    counts.columns = ["status_label", "city_count"]

    fig, ax = plt.subplots(figsize=(8, 4))
    sns.barplot(data=counts, y="status_label", x="city_count", ax=ax, color="#7c3aed")
    ax.set_title("City Coverage Status")
    ax.set_xlabel("Cities")
    ax.set_ylabel("")
    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def _plot_qa_summary(qa_df: pd.DataFrame, output_path: Path) -> None:
    if qa_df.empty:
        return

    fig, ax = plt.subplots(figsize=(10, 4))
    display = qa_df.copy().sort_values("high_zero_share_feature_count", ascending=False)
    sns.barplot(
        data=display,
        x="city_name",
        y="high_zero_share_feature_count",
        ax=ax,
        color="#f59e0b",
    )
    ax.set_title("High Zero-Share Feature Warnings by City")
    ax.set_xlabel("")
    ax.set_ylabel("High zero-share feature count")
    ax.tick_params(axis="x", labelrotation=25)
    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def _plot_grid_size_summary(summary_df: pd.DataFrame, output_path: Path) -> None:
    required = {"cell_size_meters", "benchmark_score", "mean_calibration_distance_from_one"}
    if summary_df.empty or not required.issubset(summary_df.columns):
        return

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    sns.barplot(
        data=summary_df,
        x="cell_size_meters",
        y="benchmark_score",
        ax=axes[0],
        color="#2563eb",
    )
    axes[0].set_title("Grid-Size Benchmark Score")
    axes[0].set_xlabel("Cell size (m)")
    axes[0].set_ylabel("Benchmark score")

    sns.barplot(
        data=summary_df,
        x="cell_size_meters",
        y="mean_calibration_distance_from_one",
        ax=axes[1],
        color="#059669",
    )
    axes[1].set_title("Calibration Distance from 1")
    axes[1].set_xlabel("Cell size (m)")
    axes[1].set_ylabel("Mean |log(calibration factor)|")

    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def _plot_osm_completeness(summary_df: pd.DataFrame, output_path: Path) -> None:
    required = {"city_name", "completeness_score"}
    if summary_df.empty or not required.issubset(summary_df.columns):
        return

    fig, ax = plt.subplots(figsize=(10, 4.5))
    display = summary_df.sort_values("completeness_score", ascending=False)
    sns.barplot(data=display, x="city_name", y="completeness_score", ax=ax, color="#0ea5e9")
    ax.set_title("OSM Completeness Score by City")
    ax.set_xlabel("")
    ax.set_ylabel("Completeness score")
    ax.tick_params(axis="x", labelrotation=25)
    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def _load_district_benchmark_metrics(district_benchmark_dir: Path) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    for path in sorted(district_benchmark_dir.glob("*/district_benchmark_metrics.csv")):
        frame = _load_csv(path)
        if frame.empty:
            continue
        frame = frame.copy()
        frame["source_metrics_path"] = str(path)
        rows.append(frame)
    if not rows:
        return pd.DataFrame()
    return pd.concat(rows, ignore_index=True)


def _plot_district_benchmark(metrics_df: pd.DataFrame, output_path: Path) -> None:
    required = {"city_name", "rmse"}
    if metrics_df.empty or not required.issubset(metrics_df.columns):
        return

    fig, ax = plt.subplots(figsize=(8, 4.5))
    display = metrics_df.sort_values("rmse", ascending=True)
    sns.barplot(data=display, x="city_name", y="rmse", ax=ax, color="#dc2626")
    ax.set_title("District benchmark RMSE by city")
    ax.set_xlabel("")
    ax.set_ylabel("District RMSE")
    ax.tick_params(axis="x", labelrotation=20)
    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def _plot_population_surface_example(frame: pd.DataFrame, title: str, output_path: Path) -> None:
    if frame.empty:
        return
    required = {"longitude", "latitude", "Population_Estimate_Final"}
    if not required.issubset(frame.columns):
        return

    fig, ax = plt.subplots(figsize=(7, 6))
    scatter = ax.scatter(
        frame["longitude"],
        frame["latitude"],
        c=frame["Population_Estimate_Final"],
        s=8,
        cmap="viridis",
        linewidths=0,
    )
    ax.set_title(title)
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    cbar = fig.colorbar(scatter, ax=ax)
    cbar.set_label("Estimated population per cell")
    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def _find_example_csv(inference_runs_dir: Path, city_slug: str) -> Path | None:
    candidates = sorted(inference_runs_dir.glob(f"{city_slug}*__random_forest.csv"))
    if not candidates:
        return None
    return candidates[0]


def build_paper_report(config: PaperReportConfig) -> dict[str, Path]:
    output_dir = Path(config.output_dir)
    figures_dir = output_dir / "figures"
    tables_dir = output_dir / "tables"
    figures_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)

    status_df = _load_csv(config.status_csv)
    qa_df = _load_csv(config.qa_city_summary_csv)
    grid_summary_df = _load_csv(config.grid_benchmark_dir / "grid_size_summary.csv")
    grid_city_recommendations_df = _load_csv(config.grid_benchmark_dir / "grid_size_city_recommendations.csv")
    osm_completeness_df = _load_csv(config.osm_completeness_dir / "osm_completeness_summary.csv")
    district_benchmark_metrics_df = _load_district_benchmark_metrics(config.district_benchmark_dir)
    metrics_df = _aggregate_training_metrics(config.metrics_dir)
    external_metrics_df = _require_csv(config.external_benchmark_dir / "external_benchmark_metrics.csv")
    external_summary_df = _require_csv(config.external_benchmark_dir / "external_benchmark_summary_by_source.csv")
    ablation_summary_df = _require_csv(config.ablation_dir / "ablation_summary.csv")
    ablation_selected_extras_df = _require_csv(config.ablation_dir / "selected_extras_summary.csv")
    qualitative_summary_df = _require_csv(config.qualitative_validation_dir / "qualitative_validation_summary.csv")
    _require_file(config.qualitative_validation_dir / "qualitative_validation_report.md")

    status_table_path = tables_dir / "city_status_table.csv"
    qa_table_path = tables_dir / "qa_city_summary_table.csv"
    metrics_table_path = tables_dir / "model_validation_table.csv"
    grid_summary_table_path = tables_dir / "grid_size_summary_table.csv"
    grid_city_table_path = tables_dir / "grid_size_city_recommendations_table.csv"
    osm_completeness_table_path = tables_dir / "osm_completeness_table.csv"
    district_benchmark_table_path = tables_dir / "district_benchmark_metrics_table.csv"
    external_benchmark_summary_table_path = tables_dir / "external_benchmark_summary_table.csv"
    external_benchmark_metrics_table_path = tables_dir / "external_benchmark_metrics_table.csv"
    ablation_summary_table_path = tables_dir / "ablation_summary_table.csv"
    ablation_selected_extras_table_path = tables_dir / "ablation_selected_extras_table.csv"
    qualitative_validation_case_table_path = tables_dir / "qualitative_validation_case_table.csv"

    status_df.to_csv(status_table_path, index=False)
    qa_df.to_csv(qa_table_path, index=False)
    metrics_df.to_csv(metrics_table_path, index=False)
    grid_summary_df.to_csv(grid_summary_table_path, index=False)
    grid_city_recommendations_df.to_csv(grid_city_table_path, index=False)
    osm_completeness_df.to_csv(osm_completeness_table_path, index=False)
    district_benchmark_metrics_df.to_csv(district_benchmark_table_path, index=False)
    external_summary_df.to_csv(external_benchmark_summary_table_path, index=False)
    external_metrics_df.to_csv(external_benchmark_metrics_table_path, index=False)
    ablation_summary_df.to_csv(ablation_summary_table_path, index=False)
    ablation_selected_extras_df.to_csv(ablation_selected_extras_table_path, index=False)
    qualitative_summary_df.to_csv(qualitative_validation_case_table_path, index=False)

    model_comparison_png = figures_dir / "figure_model_comparison.png"
    city_status_png = figures_dir / "figure_city_status.png"
    qa_summary_png = figures_dir / "figure_qa_warnings.png"
    grid_size_png = figures_dir / "figure_grid_size_benchmark.png"
    osm_completeness_png = figures_dir / "figure_osm_completeness.png"
    district_benchmark_png = figures_dir / "figure_district_benchmark.png"
    external_benchmark_pearson_png = figures_dir / "figure_external_benchmark_pearson.png"
    external_benchmark_hotspot_png = figures_dir / "figure_external_benchmark_hotspot_iou.png"
    ablation_png = figures_dir / "figure_ablation_loco.png"
    qualitative_overview_almaty_png = figures_dir / "figure_qualitative_overview_almaty.png"
    qualitative_overview_astana_png = figures_dir / "figure_qualitative_overview_astana.png"
    qualitative_cases_almaty_png = figures_dir / "figure_qualitative_cases_almaty.png"
    qualitative_cases_astana_png = figures_dir / "figure_qualitative_cases_astana.png"

    _plot_model_comparison(metrics_df, model_comparison_png)
    _plot_city_status(status_df, city_status_png)
    _plot_qa_summary(qa_df, qa_summary_png)
    _plot_grid_size_summary(grid_summary_df, grid_size_png)
    _plot_osm_completeness(osm_completeness_df, osm_completeness_png)
    _plot_district_benchmark(district_benchmark_metrics_df, district_benchmark_png)
    _copy_required_file(
        config.external_benchmark_dir / "figures" / "figure_external_benchmark_pearson.png",
        external_benchmark_pearson_png,
    )
    _copy_required_file(
        config.external_benchmark_dir / "figures" / "figure_external_benchmark_hotspot_iou.png",
        external_benchmark_hotspot_png,
    )
    _copy_required_file(
        config.ablation_dir / "figures" / "figure_ablation_loco.png",
        ablation_png,
    )
    _copy_required_file(
        config.qualitative_validation_dir / "figures" / "figure_qualitative_overview_almaty.png",
        qualitative_overview_almaty_png,
    )
    _copy_required_file(
        config.qualitative_validation_dir / "figures" / "figure_qualitative_overview_astana.png",
        qualitative_overview_astana_png,
    )
    _copy_required_file(
        config.qualitative_validation_dir / "figures" / "figure_qualitative_cases_almaty.png",
        qualitative_cases_almaty_png,
    )
    _copy_required_file(
        config.qualitative_validation_dir / "figures" / "figure_qualitative_cases_astana.png",
        qualitative_cases_astana_png,
    )

    example_figure_paths: list[Path] = []
    for city_slug in config.example_city_slugs:
        csv_path = _find_example_csv(config.inference_runs_dir, city_slug)
        if csv_path is None:
            continue
        frame = pd.read_csv(csv_path)
        city_name = str(frame["city_name"].iloc[0]) if "city_name" in frame.columns and not frame.empty else city_slug.title()
        output_path = figures_dir / f"figure_surface_{city_slug}.png"
        _plot_population_surface_example(frame, f"{city_name} Population Surface", output_path)
        example_figure_paths.append(output_path)

    report_path = output_dir / "paper_report_summary.md"
    baseline_rf = metrics_df.loc[
        (metrics_df["model_name"] == "random_forest") & (metrics_df["validation_protocol"] == "leave_one_city_out")
    ]
    best_grid_row = grid_summary_df.iloc[0] if not grid_summary_df.empty else None
    best_pearson_row = external_summary_df.loc[external_summary_df["pearson_r"].idxmax()] if not external_summary_df.empty else None
    best_spearman_row = external_summary_df.loc[external_summary_df["spearman_r"].idxmax()] if not external_summary_df.empty else None
    best_top_decile_row = external_summary_df.loc[external_summary_df["top_decile_overlap"].idxmax()] if not external_summary_df.empty else None
    best_hotspot_row = external_summary_df.loc[external_summary_df["hotspot_iou"].idxmax()] if not external_summary_df.empty else None
    full_ablation_row = ablation_summary_df.loc[ablation_summary_df["ablation_name"] == "full_features"]
    winner_ablation_row = ablation_summary_df.loc[ablation_summary_df["is_selected_non_full_winner"] == True]
    qualitative_city_slugs = sorted(qualitative_summary_df["city_slug"].astype(str).unique().tolist()) if not qualitative_summary_df.empty else []
    qualitative_case_count = int(len(qualitative_summary_df))
    completeness_lookup = osm_completeness_df.copy()
    if not completeness_lookup.empty and "city_name" in completeness_lookup.columns:
        completeness_lookup["city_slug"] = completeness_lookup["city_name"].astype(str).str.strip().str.lower().str.replace(" ", "_", regex=False)
        completeness_lookup = completeness_lookup.set_index("city_slug")

    lines = ["# City1 v2 Paper Report", ""]
    lines.append("## Baseline status")
    lines.append("")
    if not status_df.empty:
        lines.append(f"- Calibrated cities in reference: `{int(status_df['supported_for_calibrated_inference'].sum())}`")
        lines.append(f"- Validated baseline cities: `{int(status_df['validated_batch'].sum())}`")
        lines.append(f"- Smoke-passed cities: `{int(status_df['smoke_passed'].sum())}`")
        lines.append("")

    lines.append("## Model summary")
    lines.append("")
    if not baseline_rf.empty:
        row = baseline_rf.iloc[0]
        lines.append(
            f"- `random_forest` under LOCO: calibrated RMSE `{float(row['mean_calibrated_rmse']):.3f}`, "
            f"calibrated R2 `{float(row['mean_calibrated_r2']):.3f}`"
        )
    if not metrics_df.empty:
        best = metrics_df.sort_values(["mean_calibrated_rmse", "mean_calibrated_r2"], ascending=[True, False]).iloc[0]
        lines.append(
            f"- Best validation row in current report: `{best['model_name']}` / `{best['validation_protocol']}` "
            f"with RMSE `{float(best['mean_calibrated_rmse']):.3f}`"
        )
    lines.append("")

    lines.append("## Grid-size summary")
    lines.append("")
    if best_grid_row is not None:
        lines.append(
            f"- Recommended default cell size: `{int(best_grid_row['cell_size_meters'])} m` "
            f"(benchmark score `{float(best_grid_row['benchmark_score']):.6f}`)"
        )
    lines.append("")

    lines.append("## OSM completeness")
    lines.append("")
    if not osm_completeness_df.empty:
        ranked = osm_completeness_df.sort_values("completeness_score", ascending=False)
        best = ranked.iloc[0]
        weakest = ranked.iloc[-1]
        mean_score = float(ranked["completeness_score"].mean())
        lines.append(
            f"- Best completeness in current batch: `{best['city_name']}` "
            f"with score `{float(best['completeness_score']):.3f}` and label `{best['completeness_label']}`"
        )
        lines.append(
            f"- Weakest completeness in current batch: `{weakest['city_name']}` "
            f"with score `{float(weakest['completeness_score']):.3f}` and label `{weakest['completeness_label']}`"
        )
        lines.append(f"- Mean completeness score across the batch: `{mean_score:.3f}`")
    lines.append("")

    lines.append("## District benchmark")
    lines.append("")
    if not district_benchmark_metrics_df.empty:
        full_mask = (
            (district_benchmark_metrics_df.get("district_reference_row_count", district_benchmark_metrics_df["district_count_total"]) == district_benchmark_metrics_df["district_count_compared"])
            & (district_benchmark_metrics_df.get("boundary_warning_count", 0) == 0)
        )
        full_count = int(full_mask.sum())
        partial_count = int(len(district_benchmark_metrics_df) - full_count)
        best = district_benchmark_metrics_df.sort_values("rmse", ascending=True).iloc[0]
        lines.append(
            f"- Available district benchmark cities: `{len(district_benchmark_metrics_df)}`"
        )
        lines.append(f"- Fully matched district benchmark cities: `{full_count}`")
        lines.append(f"- Partial district benchmark cities: `{partial_count}`")
        lines.append(
            f"- Best district benchmark currently available: `{best['city_name']}` "
            f"with RMSE `{float(best['rmse']):.3f}` and Pearson r `{float(best['pearson_r']):.3f}`"
        )
    lines.append("")

    lines.append("## External benchmark")
    lines.append("")
    if best_pearson_row is not None:
        lines.append(
            f"- Best Pearson benchmark: `{best_pearson_row['benchmark_name']}` "
            f"with Pearson r `{float(best_pearson_row['pearson_r']):.3f}`"
        )
    if best_spearman_row is not None:
        lines.append(
            f"- Best Spearman benchmark: `{best_spearman_row['benchmark_name']}` "
            f"with Spearman r `{float(best_spearman_row['spearman_r']):.3f}`"
        )
    if best_top_decile_row is not None:
        lines.append(
            f"- Best top-decile overlap benchmark: `{best_top_decile_row['benchmark_name']}` "
            f"with overlap `{float(best_top_decile_row['top_decile_overlap']):.3f}`"
        )
    if best_hotspot_row is not None:
        lines.append(
            f"- Best hotspot IoU benchmark: `{best_hotspot_row['benchmark_name']}` "
            f"with IoU `{float(best_hotspot_row['hotspot_iou']):.3f}`"
        )
    lines.append("")

    lines.append("## Ablation")
    lines.append("")
    if not full_ablation_row.empty:
        full = full_ablation_row.iloc[0]
        lines.append(
            f"- Full model calibrated RMSE / R2: `{float(full['mean_calibrated_rmse']):.3f}` / "
            f"`{float(full['mean_calibrated_r2']):.3f}`"
        )
        lines.append(
            f"- Full model calibration RMSE gain: `{float(full['calibration_rmse_gain']):.3f}`"
        )
    if not winner_ablation_row.empty:
        winner = winner_ablation_row.iloc[0]
        lines.append(
            f"- Strongest non-full ablation: `{winner['ablation_name']}`"
        )
        lines.append(
            f"- Winner non-full calibrated RMSE / R2: `{float(winner['mean_calibrated_rmse']):.3f}` / "
            f"`{float(winner['mean_calibrated_r2']):.3f}`"
        )
    lines.append("")

    lines.append("## Qualitative validation")
    lines.append("")
    lines.append(f"- Qualitative validation cities: `{len(qualitative_city_slugs)}` (`{', '.join(qualitative_city_slugs)}`)")
    lines.append(f"- Total curated cases: `{qualitative_case_count}`")
    if "almaty" in completeness_lookup.index:
        almaty_row = completeness_lookup.loc["almaty"]
        lines.append(
            f"- `Almaty` has stronger qualitative reading context because OSM completeness is "
            f"`{almaty_row['completeness_label']}` (`{float(almaty_row['completeness_score']):.3f}`)"
        )
    if "astana" in completeness_lookup.index:
        astana_row = completeness_lookup.loc["astana"]
        lines.append(
            f"- `Astana` should be interpreted more cautiously because OSM completeness is "
            f"`{astana_row['completeness_label']}` (`{float(astana_row['completeness_score']):.3f}`)"
        )
    lines.append("")

    lines.append("## Main outputs")
    lines.append("")
    lines.append(f"- Model comparison figure: `{model_comparison_png}`")
    lines.append(f"- City status figure: `{city_status_png}`")
    lines.append(f"- QA figure: `{qa_summary_png}`")
    lines.append(f"- Grid-size figure: `{grid_size_png}`")
    if osm_completeness_png.exists():
        lines.append(f"- OSM completeness figure: `{osm_completeness_png}`")
    if district_benchmark_png.exists():
        lines.append(f"- District benchmark figure: `{district_benchmark_png}`")
    lines.append(f"- External benchmark Pearson figure: `{external_benchmark_pearson_png}`")
    lines.append(f"- External benchmark hotspot IoU figure: `{external_benchmark_hotspot_png}`")
    lines.append(f"- Ablation figure: `{ablation_png}`")
    lines.append(f"- Qualitative overview figure: `{qualitative_overview_almaty_png}`")
    lines.append(f"- Qualitative overview figure: `{qualitative_overview_astana_png}`")
    lines.append(f"- Qualitative cases figure: `{qualitative_cases_almaty_png}`")
    lines.append(f"- Qualitative cases figure: `{qualitative_cases_astana_png}`")
    for path in example_figure_paths:
        lines.append(f"- Population surface example: `{path}`")
    lines.append("")
    lines.append("## Tables")
    lines.append("")
    lines.append(f"- `{status_table_path}`")
    lines.append(f"- `{qa_table_path}`")
    lines.append(f"- `{metrics_table_path}`")
    lines.append(f"- `{grid_summary_table_path}`")
    lines.append(f"- `{grid_city_table_path}`")
    lines.append(f"- `{osm_completeness_table_path}`")
    lines.append(f"- `{district_benchmark_table_path}`")
    lines.append(f"- `{external_benchmark_summary_table_path}`")
    lines.append(f"- `{external_benchmark_metrics_table_path}`")
    lines.append(f"- `{ablation_summary_table_path}`")
    lines.append(f"- `{ablation_selected_extras_table_path}`")
    lines.append(f"- `{qualitative_validation_case_table_path}`")
    lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")

    outputs = {
        "report_path": report_path,
        "status_table_path": status_table_path,
        "qa_table_path": qa_table_path,
        "metrics_table_path": metrics_table_path,
        "grid_summary_table_path": grid_summary_table_path,
        "grid_city_table_path": grid_city_table_path,
        "osm_completeness_table_path": osm_completeness_table_path,
        "district_benchmark_table_path": district_benchmark_table_path,
        "external_benchmark_summary_table_path": external_benchmark_summary_table_path,
        "external_benchmark_metrics_table_path": external_benchmark_metrics_table_path,
        "ablation_summary_table_path": ablation_summary_table_path,
        "ablation_selected_extras_table_path": ablation_selected_extras_table_path,
        "qualitative_validation_case_table_path": qualitative_validation_case_table_path,
        "model_comparison_figure_path": model_comparison_png,
        "city_status_figure_path": city_status_png,
        "qa_summary_figure_path": qa_summary_png,
        "grid_size_figure_path": grid_size_png,
        "external_benchmark_pearson_figure_path": external_benchmark_pearson_png,
        "external_benchmark_hotspot_figure_path": external_benchmark_hotspot_png,
        "ablation_figure_path": ablation_png,
        "qualitative_overview_figure_almaty": qualitative_overview_almaty_png,
        "qualitative_overview_figure_astana": qualitative_overview_astana_png,
        "qualitative_cases_figure_almaty": qualitative_cases_almaty_png,
        "qualitative_cases_figure_astana": qualitative_cases_astana_png,
    }
    if osm_completeness_png.exists():
        outputs["osm_completeness_figure_path"] = osm_completeness_png
    if district_benchmark_png.exists():
        outputs["district_benchmark_figure_path"] = district_benchmark_png
    for index, path in enumerate(example_figure_paths, start=1):
        outputs[f"example_surface_figure_{index}"] = path
    return outputs
