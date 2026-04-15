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


def missing_columns(columns: Iterable[str], required: Iterable[str]) -> list[str]:
    """Return required columns that are absent in the provided iterable."""
    column_set = set(columns)
    return [column for column in required if column not in column_set]
