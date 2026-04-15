from __future__ import annotations

from dataclasses import dataclass

from .config import FeaturePipelineConfig
from .crs import CityGeometryBundle, prepare_city_geometry
from .features import FeatureComputationResult, build_feature_output, compute_grid_features
from .grid import generate_city_grid
from .osm import OSMLayerBundle, extract_osm_layers, fetch_city_boundary


@dataclass
class FeaturePipelineArtifacts:
    city_geometry: CityGeometryBundle
    grid_working: object
    layers: OSMLayerBundle
    features: FeatureComputationResult


def generate_city_features(
    place_name: str,
    config: FeaturePipelineConfig | None = None,
) -> FeaturePipelineArtifacts:
    pipeline_config = config or FeaturePipelineConfig()

    city_boundary = fetch_city_boundary(place_name, config=pipeline_config.osm)
    city_geometry = prepare_city_geometry(
        city_boundary,
        place_name=place_name,
        display_crs=pipeline_config.display_crs,
    )

    grid_working = generate_city_grid(city_geometry, config=pipeline_config.grid)
    layers = extract_osm_layers(city_geometry, config=pipeline_config.osm)
    featured_grid = compute_grid_features(
        grid_working,
        layers=layers.layers,
        config=pipeline_config.features,
    )
    feature_result = build_feature_output(
        featured_grid,
        display_crs=pipeline_config.display_crs,
    )

    return FeaturePipelineArtifacts(
        city_geometry=city_geometry,
        grid_working=grid_working,
        layers=layers,
        features=feature_result,
    )
