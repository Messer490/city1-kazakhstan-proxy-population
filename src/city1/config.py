from __future__ import annotations

from dataclasses import dataclass, field

from .contracts import GRID_FEATURE_COLUMNS


DEFAULT_DISPLAY_CRS = "EPSG:4326"


@dataclass(frozen=True)
class GridConfig:
    cell_size_meters: int = 500
    clip_to_city_boundary: bool = True
    zone_id_prefix: str = "Z"


@dataclass(frozen=True)
class OSMExtractionConfig:
    timeout_seconds: int = 300
    overpass_endpoint: str | None = "https://overpass.kumi.systems/api/interpreter"
    network_type: str = "drive"
    use_osmnx_cache: bool = True
    request_retries: int = 3
    retry_sleep_seconds: float = 2.0
    buildings_tags: dict[str, object] = field(default_factory=lambda: {"building": True})
    bus_stops_tags: dict[str, object] = field(default_factory=lambda: {"highway": "bus_stop"})
    parks_tags: dict[str, object] = field(default_factory=lambda: {"leisure": "park"})
    schools_tags: dict[str, object] = field(default_factory=lambda: {"amenity": ["school", "kindergarten"]})
    hospitals_tags: dict[str, object] = field(default_factory=lambda: {"amenity": ["hospital", "clinic"]})
    shops_tags: dict[str, object] = field(default_factory=lambda: {"shop": True})


@dataclass(frozen=True)
class FeatureEngineeringConfig:
    combined_index_columns: tuple[str, ...] = (
        "Building_Count",
        "Building_Area",
        "Residential_Area",
        "Commercial_Area",
        "Retail_Area",
        "Public_Area",
        "Road_Length",
        "Bus_Stop_Count",
        "Park_Area",
        "Total_Floor_Area",
    )
    poi_layer_names: tuple[str, ...] = (
        "bus_stops",
        "parks",
        "schools",
        "hospitals",
        "shops",
    )
    poi_neighbors: int = 5
    poi_index_epsilon_meters: float = 1.0
    floor_area_fallback_levels: float = 1.0


@dataclass(frozen=True)
class FeaturePipelineConfig:
    display_crs: str = DEFAULT_DISPLAY_CRS
    grid: GridConfig = field(default_factory=GridConfig)
    osm: OSMExtractionConfig = field(default_factory=OSMExtractionConfig)
    features: FeatureEngineeringConfig = field(default_factory=FeatureEngineeringConfig)


def default_feature_columns() -> tuple[str, ...]:
    """Expose the canonical feature columns used by the model pipeline."""
    return GRID_FEATURE_COLUMNS
