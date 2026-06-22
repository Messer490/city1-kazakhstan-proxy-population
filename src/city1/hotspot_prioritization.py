from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd

try:  # GeoPandas is optional for Phase 5 CSV-first reporting.
    import geopandas as gpd  # type: ignore
except Exception:  # pragma: no cover - optional dependency guard
    gpd = None  # type: ignore


HOTSPOT_PRIORITY_CLASSES = {
    "high_value_high_confidence",
    "high_value_low_confidence",
    "medium_value_high_confidence",
    "low_value_high_uncertainty",
    "not_priority",
}

PLANNING_INTERPRETATION = {
    "high_value_high_confidence": "Strong planning-screening candidate.",
    "high_value_low_confidence": "Potentially important but requires local verification.",
    "medium_value_high_confidence": "Stable secondary candidate.",
    "low_value_high_uncertainty": "Caution zone; avoid strong conclusions without additional evidence.",
    "not_priority": "Not a hotspot priority cell.",
}

VERIFICATION_NEED = {
    "high_value_high_confidence": "Optional local verification before operational use.",
    "high_value_low_confidence": "Local verification recommended before strong interpretation.",
    "medium_value_high_confidence": "Use as a secondary screening signal; verify if operationally important.",
    "low_value_high_uncertainty": "Additional evidence required; avoid definitive prioritization.",
    "not_priority": "No hotspot-specific verification needed from this layer.",
}


@dataclass(frozen=True)
class HotspotPrioritizationSummary:
    hotspot_quantile: float
    hotspot_threshold: float
    hotspot_cell_count: int
    high_priority_count: int
    review_required_count: int
    medium_value_high_confidence_count: int
    low_value_high_uncertainty_count: int
    high_priority_population_sum: float
    review_required_population_sum: float

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _resolve_columns(frame: pd.DataFrame, population_column: str, confidence_column: str) -> tuple[str, str]:
    resolved_population = population_column
    resolved_confidence = confidence_column
    if resolved_population not in frame.columns and "Population_Estimate_P50" in frame.columns:
        resolved_population = "Population_Estimate_P50"
    if resolved_confidence not in frame.columns and "Population_Confidence_Band" in frame.columns:
        resolved_confidence = "Population_Confidence_Band"
    return resolved_population, resolved_confidence


def build_hotspot_priority_table(
    frame: pd.DataFrame,
    *,
    hotspot_quantile: float = 0.90,
    population_column: str = "p50",
    confidence_column: str = "confidence_band",
) -> tuple[pd.DataFrame, HotspotPrioritizationSummary]:
    """Return hotspot rows and a compact legacy-compatible summary.

    This function is kept for earlier tests and one-city workflows. The Phase 5
    report builder below works on canonical v3 CSV outputs and emits run-level
    tables.
    """
    population_column, confidence_column = _resolve_columns(frame, population_column, confidence_column)
    if population_column not in frame.columns:
        raise ValueError(f"Missing population column: {population_column}")
    if confidence_column not in frame.columns:
        raise ValueError(f"Missing confidence column: {confidence_column}")
    if frame.empty:
        raise ValueError("Cannot prioritize hotspots from an empty frame.")

    working = frame.copy()
    population = pd.to_numeric(working[population_column], errors="coerce").fillna(0.0)
    threshold = float(population.quantile(hotspot_quantile))
    p75_threshold = float(population.quantile(0.75))
    median_threshold = float(population.quantile(0.50))
    confidence = working[confidence_column].astype(str).str.lower()

    working["hotspot_rank"] = population.rank(method="dense", ascending=False).astype(int)
    working["hotspot_priority_class"] = "not_priority"
    high_value = population >= threshold
    medium_value = (population >= p75_threshold) & (population < threshold)
    low_value = population < median_threshold

    working.loc[high_value & (confidence == "high"), "hotspot_priority_class"] = "high_value_high_confidence"
    working.loc[high_value & (confidence == "low"), "hotspot_priority_class"] = "high_value_low_confidence"
    working.loc[medium_value & (confidence == "high"), "hotspot_priority_class"] = "medium_value_high_confidence"
    working.loc[low_value & (confidence == "low"), "hotspot_priority_class"] = "low_value_high_uncertainty"
    working["hotspot_threshold"] = threshold
    working["hotspot_quantile"] = hotspot_quantile

    hotspots = working.loc[high_value].copy()
    if hotspots.empty:
        hotspots = working.nlargest(1, population_column).copy()

    hotspots = hotspots.sort_values([population_column, confidence_column], ascending=[False, True]).reset_index(drop=True)
    hotspot_population = pd.to_numeric(hotspots[population_column], errors="coerce").fillna(0.0)

    summary = HotspotPrioritizationSummary(
        hotspot_quantile=float(hotspot_quantile),
        hotspot_threshold=float(threshold),
        hotspot_cell_count=int(len(hotspots)),
        high_priority_count=int((hotspots["hotspot_priority_class"] == "high_value_high_confidence").sum()),
        review_required_count=int((hotspots["hotspot_priority_class"] == "high_value_low_confidence").sum()),
        medium_value_high_confidence_count=int((working["hotspot_priority_class"] == "medium_value_high_confidence").sum()),
        low_value_high_uncertainty_count=int((working["hotspot_priority_class"] == "low_value_high_uncertainty").sum()),
        high_priority_population_sum=float(hotspot_population.loc[hotspots["hotspot_priority_class"] == "high_value_high_confidence"].sum()),
        review_required_population_sum=float(hotspot_population.loc[hotspots["hotspot_priority_class"] == "high_value_low_confidence"].sum()),
    )
    return hotspots, summary


def save_hotspot_prioritization_outputs(
    hotspots,
    summary: HotspotPrioritizationSummary,
    output_dir: str | Path,
) -> dict[str, Path]:
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    table_csv = output_root / "hotspot_priority_table.csv"
    summary_csv = output_root / "hotspot_priority_summary.csv"
    report_md = output_root / "hotspot_priority_report.md"

    if gpd is not None and isinstance(hotspots, gpd.GeoDataFrame):
        geojson_path = output_root / "hotspot_priority.geojson"
        hotspots.to_file(geojson_path, driver="GeoJSON")
        hotspots.drop(columns="geometry").to_csv(table_csv, index=False)
    else:
        geojson_path = None
        hotspots.to_csv(table_csv, index=False)

    pd.DataFrame([summary.to_dict()]).to_csv(summary_csv, index=False)
    lines = [
        "# City1 v3 Hotspot Prioritization",
        "",
        "This output splits high-value cells from the calibrated `p50` surface by confidence band.",
        "",
        f"- Hotspot quantile: `{summary.hotspot_quantile:.2f}`",
        f"- Hotspot threshold: `{summary.hotspot_threshold:.6f}`",
        f"- Hotspot cells: `{summary.hotspot_cell_count}`",
        f"- High-value / high-confidence: `{summary.high_priority_count}`",
        f"- High-value / low-confidence: `{summary.review_required_count}`",
        f"- Medium-value / high-confidence: `{summary.medium_value_high_confidence_count}`",
        f"- Low-value / high-uncertainty: `{summary.low_value_high_uncertainty_count}`",
        f"- High-value / high-confidence population sum: `{summary.high_priority_population_sum:.6f}`",
        f"- High-value / low-confidence population sum: `{summary.review_required_population_sum:.6f}`",
    ]
    report_md.write_text("\n".join(lines), encoding="utf-8")

    outputs = {
        "table_csv": table_csv,
        "summary_csv": summary_csv,
        "report_md": report_md,
    }
    if geojson_path is not None:
        outputs["geojson_path"] = geojson_path
    return outputs


def _required_columns() -> list[str]:
    return [
        "run_id",
        "model_version",
        "city",
        "city_slug",
        "cell_id",
        "p10",
        "p50",
        "p90",
        "uncertainty_width",
        "relative_uncertainty",
        "confidence_score",
        "confidence_band",
        "hotspot_rank",
        "hotspot_priority_class",
        "official_city_total",
        "calibrated_member_count",
        "osm_completeness_score",
        "external_agreement_score",
        "internal_support_score",
        "district_support_flag",
    ]


def validate_phase5_city_frame(frame: pd.DataFrame, *, city_slug: str, tolerance: float = 1e-6) -> list[str]:
    """Return validation error messages for a canonical Phase 4 city output."""
    errors: list[str] = []
    missing = [column for column in _required_columns() if column not in frame.columns]
    if missing:
        errors.append(f"{city_slug}: missing required columns: {', '.join(missing)}")
        return errors

    p10 = pd.to_numeric(frame["p10"], errors="coerce")
    p50 = pd.to_numeric(frame["p50"], errors="coerce")
    p90 = pd.to_numeric(frame["p90"], errors="coerce")
    width = pd.to_numeric(frame["uncertainty_width"], errors="coerce")
    confidence = pd.to_numeric(frame["confidence_score"], errors="coerce")

    invalid_quantiles = int(((p10 > p50) | (p50 > p90)).fillna(True).sum())
    if invalid_quantiles:
        errors.append(f"{city_slug}: p10 <= p50 <= p90 failed for {invalid_quantiles} rows")

    invalid_width = int(((width - (p90 - p10)).abs() > tolerance).fillna(True).sum())
    if invalid_width:
        errors.append(f"{city_slug}: uncertainty_width != p90 - p10 for {invalid_width} rows")

    invalid_confidence = int((~confidence.between(0, 1)).fillna(True).sum())
    if invalid_confidence:
        errors.append(f"{city_slug}: confidence_score outside [0,1] for {invalid_confidence} rows")

    invalid_bands = set(frame["confidence_band"].astype(str)) - {"high", "medium", "low"}
    if invalid_bands:
        errors.append(f"{city_slug}: invalid confidence_band values: {sorted(invalid_bands)}")

    invalid_classes = set(frame["hotspot_priority_class"].astype(str)) - HOTSPOT_PRIORITY_CLASSES
    if invalid_classes:
        errors.append(f"{city_slug}: invalid hotspot_priority_class values: {sorted(invalid_classes)}")

    sorted_frame = frame.sort_values("hotspot_rank")
    ranks = pd.to_numeric(sorted_frame["hotspot_rank"], errors="coerce")
    if int((ranks == 1).sum()) < 1:
        errors.append(f"{city_slug}: hotspot_rank does not start at 1")
    rank_order_p50 = pd.to_numeric(sorted_frame["p50"], errors="coerce")
    if not rank_order_p50.is_monotonic_decreasing:
        errors.append(f"{city_slug}: hotspot_rank is not descending by p50")

    official_total = float(pd.to_numeric(frame["official_city_total"], errors="coerce").dropna().iloc[0])
    sum_p50 = float(p50.sum())
    if abs(sum_p50 - official_total) > max(1e-4, official_total * 1e-9):
        errors.append(f"{city_slug}: sum(p50)={sum_p50:.6f} differs from official_city_total={official_total:.6f}")

    return errors


def _first_value(frame: pd.DataFrame, column: str, default: object = "") -> object:
    if column not in frame.columns or frame.empty:
        return default
    series = frame[column].dropna()
    if series.empty:
        return default
    return series.iloc[0]


def _priority_frame(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.loc[frame["hotspot_priority_class"].astype(str) != "not_priority"].copy()


def _interpret_city(row: dict[str, object]) -> str:
    high = int(row.get("n_high_value_high_confidence", 0) or 0)
    low = int(row.get("n_high_value_low_confidence", 0) or 0)
    caution = int(row.get("n_low_value_high_uncertainty", 0) or 0)
    city = str(row.get("city", "This city"))
    if high > 0 and high >= low:
        return f"{city} has a stronger high-confidence hotspot signal for planning-screening, while remaining bounded by proxy-surface uncertainty."
    if low > 0:
        return f"{city} contains high-value hotspot candidates, but the current confidence layer indicates that local verification is needed before strong interpretation."
    if caution > 0:
        return f"{city} is caution-heavy in the Phase 5 layer; many cells should be treated as preliminary screening signals only."
    return f"{city} has limited priority hotspot signal under the current Phase 5 thresholds."


def make_hotspot_city_summary(city_frames: Iterable[pd.DataFrame]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for frame in city_frames:
        if frame.empty:
            continue
        priority = _priority_frame(frame)
        p50 = pd.to_numeric(frame["p50"], errors="coerce")
        threshold = float(p50.quantile(0.90))
        n_cells = int(len(frame))
        counts = frame["hotspot_priority_class"].value_counts().to_dict()
        priority_count = int(len(priority))
        row: dict[str, object] = {
            "run_id": _first_value(frame, "run_id"),
            "city": _first_value(frame, "city"),
            "city_slug": _first_value(frame, "city_slug"),
            "n_cells": n_cells,
            "official_total": float(_first_value(frame, "official_city_total", 0.0)),
            "hotspot_threshold_p90": threshold,
            "n_priority_cells": priority_count,
            "n_high_value_high_confidence": int(counts.get("high_value_high_confidence", 0)),
            "n_high_value_low_confidence": int(counts.get("high_value_low_confidence", 0)),
            "n_medium_value_high_confidence": int(counts.get("medium_value_high_confidence", 0)),
            "n_low_value_high_uncertainty": int(counts.get("low_value_high_uncertainty", 0)),
            "share_priority_cells": priority_count / n_cells if n_cells else 0.0,
            "share_high_value_high_confidence": int(counts.get("high_value_high_confidence", 0)) / n_cells if n_cells else 0.0,
            "share_high_value_low_confidence": int(counts.get("high_value_low_confidence", 0)) / n_cells if n_cells else 0.0,
            "share_low_value_high_uncertainty": int(counts.get("low_value_high_uncertainty", 0)) / n_cells if n_cells else 0.0,
            "mean_p50_priority_cells": float(pd.to_numeric(priority["p50"], errors="coerce").mean()) if not priority.empty else 0.0,
            "median_p50_priority_cells": float(pd.to_numeric(priority["p50"], errors="coerce").median()) if not priority.empty else 0.0,
            "mean_confidence_priority_cells": float(pd.to_numeric(priority["confidence_score"], errors="coerce").mean()) if not priority.empty else 0.0,
            "median_relative_uncertainty_priority_cells": float(pd.to_numeric(priority["relative_uncertainty"], errors="coerce").median()) if not priority.empty else 0.0,
            "osm_completeness_score": float(_first_value(frame, "osm_completeness_score", 0.0)),
            "osm_completeness_label": _first_value(frame, "osm_completeness_label", "unknown"),
            "external_agreement_score": float(_first_value(frame, "external_agreement_score", 0.5)),
            "internal_support_score": float(_first_value(frame, "internal_support_score", 0.5)),
            "district_support_flag": _first_value(frame, "district_support_flag", "not_available"),
        }
        row["interpretation_note"] = _interpret_city(row)
        rows.append(row)
    return pd.DataFrame(rows)


def _planning_interpretation(priority_class: object) -> str:
    return PLANNING_INTERPRETATION.get(str(priority_class), PLANNING_INTERPRETATION["not_priority"])


def _verification_need(priority_class: object) -> str:
    return VERIFICATION_NEED.get(str(priority_class), VERIFICATION_NEED["not_priority"])


def make_top_hotspots_by_city(city_frames: Iterable[pd.DataFrame], *, top_n: int = 25) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    columns = [
        "run_id",
        "city",
        "city_slug",
        "hotspot_rank",
        "cell_id",
        "centroid_latitude",
        "centroid_longitude",
        "p10",
        "p50",
        "p90",
        "uncertainty_width",
        "relative_uncertainty",
        "confidence_score",
        "confidence_band",
        "hotspot_priority_class",
        "planning_interpretation",
        "verification_need",
    ]
    for frame in city_frames:
        priority = _priority_frame(frame).sort_values("hotspot_rank").head(top_n).copy()
        if priority.empty:
            continue
        priority["planning_interpretation"] = priority["hotspot_priority_class"].map(_planning_interpretation)
        priority["verification_need"] = priority["hotspot_priority_class"].map(_verification_need)
        rows.append(priority[columns])
    if not rows:
        return pd.DataFrame(columns=columns)
    return pd.concat(rows, ignore_index=True)


def _caution_reason(row: pd.Series) -> str:
    reasons: list[str] = []
    priority_class = str(row.get("hotspot_priority_class", ""))
    if priority_class == "high_value_low_confidence":
        reasons.append("high estimated value but low confidence")
    if priority_class == "low_value_high_uncertainty":
        reasons.append("low-value cell with high uncertainty")
    if str(row.get("confidence_band", "")) == "low":
        reasons.append("low confidence score")
    if float(row.get("relative_uncertainty", 0.0) or 0.0) >= 0.5:
        reasons.append("wide prediction interval")
    label = str(row.get("osm_completeness_label", ""))
    if label in {"moderate", "weak"}:
        reasons.append("moderate or weak OSM support")
    return "; ".join(dict.fromkeys(reasons)) or "caution indicated by v3 priority class"


def _recommended_action(row: pd.Series) -> str:
    priority_class = str(row.get("hotspot_priority_class", ""))
    if priority_class == "high_value_low_confidence":
        return "local verification recommended before strong planning interpretation"
    if priority_class == "low_value_high_uncertainty":
        return "use only for preliminary screening and avoid definitive prioritization"
    return "compare with administrative or field data if operationally important"


def make_caution_hotspots(city_frames: Iterable[pd.DataFrame]) -> pd.DataFrame:
    focus = {"high_value_low_confidence", "low_value_high_uncertainty"}
    columns = [
        "run_id",
        "city",
        "city_slug",
        "cell_id",
        "hotspot_rank",
        "p50",
        "p10",
        "p90",
        "relative_uncertainty",
        "confidence_score",
        "confidence_band",
        "hotspot_priority_class",
        "caution_reason",
        "recommended_action",
    ]
    frames: list[pd.DataFrame] = []
    for frame in city_frames:
        selected = frame.loc[frame["hotspot_priority_class"].isin(focus)].copy()
        if selected.empty:
            continue
        selected["caution_reason"] = selected.apply(_caution_reason, axis=1)
        selected["recommended_action"] = selected.apply(_recommended_action, axis=1)
        frames.append(selected.sort_values(["city_slug", "hotspot_rank"])[columns])
    if not frames:
        return pd.DataFrame(columns=columns)
    return pd.concat(frames, ignore_index=True)


def _stability_reason(row: pd.Series) -> str:
    reasons: list[str] = []
    if str(row.get("confidence_band", "")) == "high":
        reasons.append("high confidence score")
    if float(row.get("relative_uncertainty", 0.0) or 0.0) <= 0.25:
        reasons.append("narrower uncertainty interval")
    if str(row.get("osm_completeness_label", "")) == "good":
        reasons.append("strong OSM completeness context")
    if str(row.get("hotspot_priority_class", "")) == "high_value_high_confidence":
        reasons.append("high p50 with acceptable uncertainty")
    return "; ".join(dict.fromkeys(reasons)) or "stable according to v3 confidence framework"


def _planning_use_case(row: pd.Series) -> str:
    priority_class = str(row.get("hotspot_priority_class", ""))
    if priority_class == "high_value_high_confidence":
        return "service-planning screening; infrastructure prioritization screening"
    return "urban density review; field verification prioritization"


def make_stable_hotspots(city_frames: Iterable[pd.DataFrame]) -> pd.DataFrame:
    focus = {"high_value_high_confidence", "medium_value_high_confidence"}
    columns = [
        "run_id",
        "city",
        "city_slug",
        "cell_id",
        "hotspot_rank",
        "p50",
        "p10",
        "p90",
        "relative_uncertainty",
        "confidence_score",
        "confidence_band",
        "hotspot_priority_class",
        "stability_reason",
        "planning_use_case",
    ]
    frames: list[pd.DataFrame] = []
    for frame in city_frames:
        selected = frame.loc[frame["hotspot_priority_class"].isin(focus)].copy()
        if selected.empty:
            continue
        selected["stability_reason"] = selected.apply(_stability_reason, axis=1)
        selected["planning_use_case"] = selected.apply(_planning_use_case, axis=1)
        frames.append(selected.sort_values(["city_slug", "hotspot_rank"])[columns])
    if not frames:
        return pd.DataFrame(columns=columns)
    return pd.concat(frames, ignore_index=True)


def generate_phase5_hotspot_package(
    *,
    run_id: str,
    input_root: str | Path = "outputs/v3_uncertainty",
    output_root: str | Path = "reports/hotspot_prioritization_v3",
    cities: Iterable[str] = ("almaty", "astana", "semey", "shymkent"),
    top_n: int = 25,
    create_figures: bool = True,
) -> dict[str, object]:
    project_input = Path(input_root) / run_id
    project_output = Path(output_root) / run_id
    project_output.mkdir(parents=True, exist_ok=True)
    figures_dir = project_output / "figures"

    city_frames: list[pd.DataFrame] = []
    validation_errors: list[str] = []
    input_files: list[str] = []
    for city in cities:
        city_slug = str(city).lower().replace(" ", "_")
        path = project_input / f"{city_slug}_uncertainty_cells.csv"
        if not path.exists():
            validation_errors.append(f"{city_slug}: missing input file {path}")
            continue
        frame = pd.read_csv(path)
        input_files.append(str(path))
        validation_errors.extend(validate_phase5_city_frame(frame, city_slug=city_slug))
        city_frames.append(frame)

    summary_path = project_input / "city_uncertainty_summary.csv"
    manifest_path = project_input / "run_manifest.json"
    if summary_path.exists():
        input_files.append(str(summary_path))
    else:
        validation_errors.append(f"missing city summary input: {summary_path}")
    if manifest_path.exists():
        input_files.append(str(manifest_path))
    else:
        validation_errors.append(f"missing run manifest input: {manifest_path}")

    if validation_errors:
        error_report = project_output / "PHASE_5_VALIDATION_FAILED.md"
        error_report.write_text("# Phase 5 input validation failed\n\n" + "\n".join(f"- {e}" for e in validation_errors), encoding="utf-8")
        raise ValueError("Phase 5 input validation failed: " + "; ".join(validation_errors))

    hotspot_city_summary = make_hotspot_city_summary(city_frames)
    top_hotspots = make_top_hotspots_by_city(city_frames, top_n=top_n)
    caution_hotspots = make_caution_hotspots(city_frames)
    stable_hotspots = make_stable_hotspots(city_frames)

    outputs: dict[str, Path] = {}
    outputs["hotspot_city_summary"] = project_output / "hotspot_city_summary.csv"
    outputs["top_hotspots_by_city"] = project_output / "top_hotspots_by_city.csv"
    outputs["caution_hotspots"] = project_output / "caution_hotspots.csv"
    outputs["stable_hotspots"] = project_output / "stable_hotspots.csv"

    hotspot_city_summary.to_csv(outputs["hotspot_city_summary"], index=False)
    top_hotspots.to_csv(outputs["top_hotspots_by_city"], index=False)
    caution_hotspots.to_csv(outputs["caution_hotspots"], index=False)
    stable_hotspots.to_csv(outputs["stable_hotspots"], index=False)

    figure_paths: list[Path] = []
    if create_figures:
        figure_paths = _create_phase5_figures(city_frames, hotspot_city_summary, figures_dir)
        for path in figure_paths:
            outputs[path.stem] = path

    report_path = project_output / "PHASE_5_HOTSPOT_PRIORITIZATION_REPORT.md"
    report_path.write_text(
        _build_phase5_report(
            run_id=run_id,
            input_files=input_files,
            output_files=[str(path) for path in outputs.values()] + [str(report_path)],
            hotspot_city_summary=hotspot_city_summary,
            stable_hotspots=stable_hotspots,
            caution_hotspots=caution_hotspots,
            figure_paths=figure_paths,
        ),
        encoding="utf-8",
    )
    outputs["phase5_report"] = report_path

    return {
        "run_id": run_id,
        "output_root": str(project_output),
        "outputs": {key: str(path) for key, path in outputs.items()},
        "city_summary_rows": hotspot_city_summary.to_dict(orient="records"),
        "stable_count": int(len(stable_hotspots)),
        "caution_count": int(len(caution_hotspots)),
    }


def _create_phase5_figures(
    city_frames: list[pd.DataFrame],
    hotspot_city_summary: pd.DataFrame,
    figures_dir: Path,
) -> list[Path]:
    figures_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    try:
        import matplotlib.pyplot as plt
    except Exception:
        return []

    all_cells = pd.concat(city_frames, ignore_index=True)

    class_counts = (
        all_cells.groupby(["city", "hotspot_priority_class"]).size().unstack(fill_value=0)
        if not all_cells.empty else pd.DataFrame()
    )
    if not class_counts.empty:
        ax = class_counts.plot(kind="bar", figsize=(10, 5))
        ax.set_title("Hotspot priority class distribution by city")
        ax.set_xlabel("City")
        ax.set_ylabel("Cell count")
        plt.tight_layout()
        path = figures_dir / "hotspot_class_distribution_by_city.png"
        plt.savefig(path, dpi=150)
        plt.close()
        paths.append(path)

    band_counts = (
        all_cells.groupby(["city", "confidence_band"]).size().unstack(fill_value=0)
        if not all_cells.empty else pd.DataFrame()
    )
    if not band_counts.empty:
        ax = band_counts.plot(kind="bar", figsize=(10, 5))
        ax.set_title("Confidence band distribution by city")
        ax.set_xlabel("City")
        ax.set_ylabel("Cell count")
        plt.tight_layout()
        path = figures_dir / "confidence_band_distribution_by_city.png"
        plt.savefig(path, dpi=150)
        plt.close()
        paths.append(path)

    for city, group in all_cells.groupby("city"):
        sample = group.sample(min(len(group), 1200), random_state=42) if len(group) > 1200 else group
        ax = sample.plot.scatter(x="p50", y="relative_uncertainty", figsize=(7, 5), alpha=0.35)
        ax.set_title(f"P50 vs relative uncertainty - {city}")
        ax.set_xlabel("p50 calibrated proxy estimate")
        ax.set_ylabel("relative uncertainty")
        plt.tight_layout()
        path = figures_dir / f"{str(city).lower().replace(' ', '_')}_p50_vs_relative_uncertainty.png"
        plt.savefig(path, dpi=150)
        plt.close()
        paths.append(path)

    if not hotspot_city_summary.empty:
        cols = [
            "n_high_value_high_confidence",
            "n_high_value_low_confidence",
            "n_medium_value_high_confidence",
            "n_low_value_high_uncertainty",
        ]
        plot_df = hotspot_city_summary.set_index("city")[cols]
        ax = plot_df.plot(kind="bar", figsize=(10, 5))
        ax.set_title("Phase 5 hotspot prioritization summary")
        ax.set_xlabel("City")
        ax.set_ylabel("Priority cell count")
        plt.tight_layout()
        path = figures_dir / "hotspot_priority_scatter_by_city.png"
        plt.savefig(path, dpi=150)
        plt.close()
        paths.append(path)

    return paths


def _build_phase5_report(
    *,
    run_id: str,
    input_files: list[str],
    output_files: list[str],
    hotspot_city_summary: pd.DataFrame,
    stable_hotspots: pd.DataFrame,
    caution_hotspots: pd.DataFrame,
    figure_paths: list[Path],
) -> str:
    lines = [
        "# Phase 5 Hotspot Prioritization Report",
        "",
        f"- run_id: `{run_id}`",
        "- scope: bounded practical layer for uncertainty-aware hotspot screening",
        "- interpretation discipline: hotspot priority is derived from a calibrated proxy surface and confidence layer, not from cell-level census truth",
        "",
        "## Inputs used",
    ]
    lines.extend(f"- `{path}`" for path in input_files)
    lines.extend(
        [
            "",
            "## Outputs generated",
        ]
    )
    lines.extend(f"- `{path}`" for path in output_files)

    lines.extend(
        [
            "",
            "## City summary",
            "",
        ]
    )
    if hotspot_city_summary.empty:
        lines.append("No city summary rows were generated.")
    else:
        for row in hotspot_city_summary.to_dict(orient="records"):
            lines.append(
                f"- {row['city']}: priority cells={int(row['n_priority_cells'])}, "
                f"high-confidence hotspots={int(row['n_high_value_high_confidence'])}, "
                f"review-required hotspots={int(row['n_high_value_low_confidence'])}, "
                f"caution cells={int(row['n_low_value_high_uncertainty'])}. "
                f"{row['interpretation_note']}"
            )

    lines.extend(
        [
            "",
            "## Stable vs caution hotspot counts",
            "",
            f"- Stable hotspot rows exported: `{len(stable_hotspots)}`",
            f"- Caution hotspot rows exported: `{len(caution_hotspots)}`",
        ]
    )

    if figure_paths:
        lines.extend(
            [
                "",
                "## Lightweight figures",
                "",
            ]
        )
        lines.extend(f"- `{path}`" for path in figure_paths)

    lines.extend(
        [
            "",
            "## What this phase supports",
            "",
            "- identification of strong high-confidence hotspot screening candidates",
            "- separation of stable hotspot cells from review-required hotspot cells",
            "- bounded planning-oriented summaries that remain subordinate to the proxy-population framing",
            "",
            "## What this phase does not prove",
            "",
            "- it does not validate cell-level census truth",
            "- it does not convert uncertainty/confidence into true population probability",
            "- it does not justify causal or operational claims without additional local evidence",
        ]
    )
    return "\n".join(lines) + "\n"
