from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

import geopandas as gpd
import pandas as pd


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

    if isinstance(hotspots, gpd.GeoDataFrame):
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
