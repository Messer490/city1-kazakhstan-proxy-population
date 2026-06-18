from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


GRID_FEATURE_COLUMNS: tuple[str, ...] = (
    "Building_Count",
    "Building_Area",
    "Residential_Area",
    "Commercial_Area",
    "Retail_Area",
    "Public_Area",
    "Road_Length",
    "Bus_Stop_Count",
    "Park_Area",
    "Building_With_Levels_Count",
    "Mean_Building_Levels",
    "Total_Floor_Area",
    "Schools_Count",
    "Hospitals_Count",
    "Parks_Shops_Count",
)

# In v2 this feature must be computed from real POI distances in a projected CRS.
MODEL_FEATURE_COLUMNS: tuple[str, ...] = GRID_FEATURE_COLUMNS + (
    "POI_Access_Index",
    "Combined_Index",
)

CITY_FEATURE_COLUMNS: tuple[str, ...] = (
    "Zone_ID",
    "latitude",
    "longitude",
) + MODEL_FEATURE_COLUMNS

CITY_OUTPUT_COLUMNS: tuple[str, ...] = CITY_FEATURE_COLUMNS + (
    "Population_Estimate_Final",
)

UNCERTAINTY_OUTPUT_COLUMNS: tuple[str, ...] = (
    "Population_Estimate_P10",
    "Population_Estimate_P50",
    "Population_Estimate_P90",
    "Population_Uncertainty_Width",
    "Population_Uncertainty_Relative",
    "Population_Confidence_Band",
)

MODEL_VERSION_V3 = "city1_v3_rf500m_uncertainty"

CITY_OUTPUT_COLUMNS_V3: tuple[str, ...] = (
    "run_id",
    "model_version",
    "city",
    "city_slug",
    "cell_id",
    "centroid_latitude",
    "centroid_longitude",
    "official_city_total",
    "calibrated_member_count",
    "p10",
    "p50",
    "p90",
    "population_estimate_final",
    "uncertainty_width",
    "relative_uncertainty",
    "model_stability_score",
    "osm_completeness_score",
    "osm_completeness_label",
    "osm_support_score",
    "external_agreement_score",
    "internal_support_score",
    "confidence_score",
    "confidence_band",
    "hotspot_rank",
    "hotspot_priority_class",
    "district_support_flag",
)

CITY_SUMMARY_COLUMNS_V3: tuple[str, ...] = (
    "run_id",
    "model_version",
    "city",
    "city_slug",
    "n_cells",
    "official_total",
    "sum_p50",
    "p50_total_gap_abs",
    "calibrated_member_count",
    "mean_uncertainty_width",
    "median_relative_uncertainty",
    "mean_confidence_score",
    "share_high_confidence",
    "share_medium_confidence",
    "share_low_confidence",
    "hotspot_threshold_p90",
    "n_high_confidence_hotspots",
    "n_low_confidence_hotspots",
    "n_low_value_high_uncertainty",
    "osm_completeness_score",
    "osm_completeness_label",
    "external_agreement_score",
    "district_support_flag",
    "district_interval_coverage_available",
    "district_interval_coverage_rate",
)

HOTSPOT_PRIORITY_CLASSES_V3: tuple[str, ...] = (
    "high_value_high_confidence",
    "high_value_low_confidence",
    "medium_value_high_confidence",
    "low_value_high_uncertainty",
    "not_priority",
)


@dataclass(frozen=True)
class ProblemStatement:
    name: str
    objective: str
    supervision: str
    calibration: str


PROBLEM_STATEMENT = ProblemStatement(
    name="city1_v2_proxy_population_surface",
    objective=(
        "Estimate the relative spatial distribution of population inside a city "
        "from geospatial proxy features."
    ),
    supervision=(
        "Weak or semi-supervised setup because cell-level population targets are absent."
    ),
    calibration=(
        "Calibrate grid-level predictions so that their sum matches official city-level totals."
    ),
)


PROBLEM_STATEMENT_V3 = ProblemStatement(
    name="city1_v3_uncertainty_aware_proxy_population_surface",
    objective=(
        "Estimate a calibrated proxy population surface together with an uncertainty and "
        "confidence layer for intra-urban analysis inside Kazakhstan cities."
    ),
    supervision=(
        "Weak or semi-supervised setup because cell-level population targets are absent; "
        "uncertainty expresses agreement inside an ensemble of calibrated proxy models rather "
        "than probabilistic ground truth."
    ),
    calibration=(
        "Calibrate each ensemble member so that the city-level sum matches official totals, "
        "then summarize the calibrated ensemble with interval and confidence outputs."
    ),
)


def missing_columns(columns: Iterable[str], required: Iterable[str]) -> list[str]:
    """Return required columns that are absent in the provided iterable."""
    column_set = set(columns)
    return [column for column in required if column not in column_set]
