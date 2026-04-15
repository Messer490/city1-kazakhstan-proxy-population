from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Mapping

import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors

from .config import DEFAULT_DISPLAY_CRS, FeatureEngineeringConfig
from .contracts import CITY_FEATURE_COLUMNS

if TYPE_CHECKING:
    import geopandas as gpd


RESIDENTIAL_BUILDING_TYPES = {
    "apartments",
    "detached",
    "dormitory",
    "farm",
    "ger",
    "house",
    "residential",
    "semidetached_house",
    "terrace",
}
COMMERCIAL_BUILDING_TYPES = {
    "commercial",
    "industrial",
    "kiosk",
    "office",
    "warehouse",
}
RETAIL_BUILDING_TYPES = {
    "mall",
    "retail",
    "supermarket",
}
PUBLIC_BUILDING_TYPES = {
    "civic",
    "college",
    "government",
    "hospital",
    "kindergarten",
    "public",
    "school",
    "train_station",
    "transportation",
    "university",
}


@dataclass
class FeatureComputationResult:
    working_gdf: "gpd.GeoDataFrame"
    display_gdf: "gpd.GeoDataFrame"
    feature_frame: pd.DataFrame


def min_max_scale_frame(df: pd.DataFrame) -> pd.DataFrame:
    minima = df.min()
    maxima = df.max()
    denominator = (maxima - minima).replace(0, np.nan)
    scaled = (df - minima) / denominator
    return scaled.fillna(0.0)


def compute_combined_index(
    df: pd.DataFrame,
    feature_columns: tuple[str, ...],
) -> pd.Series:
    available_columns = [column for column in feature_columns if column in df.columns]
    if not available_columns:
        return pd.Series(0.0, index=df.index, dtype=float)
    normalized = min_max_scale_frame(df[available_columns].fillna(0.0))
    return normalized.sum(axis=1)


def _string_series(df: pd.DataFrame, column: str) -> pd.Series:
    if column not in df.columns:
        return pd.Series("", index=df.index, dtype="object")
    return df[column].fillna("").astype(str).str.lower().str.strip()


def _building_use_masks(buildings: pd.DataFrame) -> dict[str, pd.Series]:
    building_type = _string_series(buildings, "building")
    amenity = _string_series(buildings, "amenity")
    shop = _string_series(buildings, "shop")
    office = _string_series(buildings, "office")

    residential_mask = building_type.isin(RESIDENTIAL_BUILDING_TYPES)
    commercial_mask = building_type.isin(COMMERCIAL_BUILDING_TYPES) | office.ne("")
    retail_mask = building_type.isin(RETAIL_BUILDING_TYPES) | shop.ne("")
    public_mask = building_type.isin(PUBLIC_BUILDING_TYPES) | amenity.isin(PUBLIC_BUILDING_TYPES)

    return {
        "residential": residential_mask,
        "commercial": commercial_mask,
        "retail": retail_mask,
        "public": public_mask,
    }


def _building_levels(buildings: pd.DataFrame) -> pd.Series:
    if "building:levels" not in buildings.columns:
        return pd.Series(index=buildings.index, dtype=float)
    levels = pd.to_numeric(buildings["building:levels"], errors="coerce")
    return levels.where(levels > 0)


def _candidate_subset(layer: "gpd.GeoDataFrame", geometry):
    if layer is None or layer.empty:
        return layer

    try:
        indices = list(layer.sindex.query(geometry, predicate="intersects"))
        return layer.iloc[indices].copy() if indices else layer.iloc[0:0].copy()
    except Exception:
        mask = layer.intersects(geometry)
        return layer.loc[mask].copy()


def _intersecting_subset(layer: "gpd.GeoDataFrame", geometry):
    if layer is None or layer.empty:
        return layer
    subset = _candidate_subset(layer, geometry)
    if subset.empty:
        return subset
    return subset.loc[subset.intersects(geometry)].copy()


def _intersection_measure(layer: "gpd.GeoDataFrame", geometry, mode: str) -> tuple[float, pd.Series]:
    subset = _intersecting_subset(layer, geometry)
    if subset is None or subset.empty:
        return 0.0, pd.Series(dtype=float)

    intersections = subset.geometry.intersection(geometry)
    if mode == "area":
        values = intersections.area.clip(lower=0.0)
    elif mode == "length":
        values = intersections.length.clip(lower=0.0)
    else:
        raise ValueError(f"Unsupported intersection mode: {mode}")

    return float(values.sum()), values


def _count_intersections(layer: "gpd.GeoDataFrame", geometry) -> tuple[int, "gpd.GeoDataFrame"]:
    subset = _intersecting_subset(layer, geometry)
    if subset is None or subset.empty:
        return 0, subset
    return int(len(subset)), subset


def build_poi_reference_points(
    layers: Mapping[str, "gpd.GeoDataFrame"],
    poi_layer_names: tuple[str, ...],
    working_crs: object,
) -> "gpd.GeoDataFrame":
    import geopandas as gpd

    frames: list[pd.DataFrame] = []

    for layer_name in poi_layer_names:
        layer = layers.get(layer_name)
        if layer is None or layer.empty:
            continue

        points = layer[["geometry"]].copy()
        points["geometry"] = points.geometry.representative_point()
        frames.append(points)

    if not frames:
        return gpd.GeoDataFrame({"geometry": []}, geometry="geometry", crs=working_crs)

    combined = pd.concat(frames, ignore_index=True)
    return gpd.GeoDataFrame(combined, geometry="geometry", crs=working_crs)


def compute_poi_access_index(
    grid_gdf: "gpd.GeoDataFrame",
    poi_points: "gpd.GeoDataFrame",
    neighbors: int,
    epsilon_meters: float,
) -> pd.Series:
    if grid_gdf.empty or poi_points.empty:
        return pd.Series(0.0, index=grid_gdf.index, dtype=float)

    grid_centroids = grid_gdf.geometry.centroid
    grid_coords = np.column_stack([grid_centroids.x.to_numpy(), grid_centroids.y.to_numpy()])
    poi_coords = np.column_stack([poi_points.geometry.x.to_numpy(), poi_points.geometry.y.to_numpy()])

    n_neighbors = max(1, min(neighbors, len(poi_points)))
    model = NearestNeighbors(n_neighbors=n_neighbors)
    model.fit(poi_coords)
    distances, _ = model.kneighbors(grid_coords)
    mean_distance = distances.mean(axis=1)
    return pd.Series(1.0 / (mean_distance + epsilon_meters), index=grid_gdf.index)


def compute_grid_features(
    grid_gdf: "gpd.GeoDataFrame",
    layers: Mapping[str, "gpd.GeoDataFrame"],
    config: FeatureEngineeringConfig | None = None,
) -> "gpd.GeoDataFrame":
    feature_config = config or FeatureEngineeringConfig()
    grid = grid_gdf.copy()
    feature_records: list[dict[str, float]] = []

    for _, cell in grid.iterrows():
        geometry = cell.geometry

        building_count, buildings_in = _count_intersections(layers.get("buildings"), geometry)
        road_length, _ = _intersection_measure(layers.get("roads"), geometry, mode="length")
        bus_stop_count, _ = _count_intersections(layers.get("bus_stops"), geometry)
        park_area, parks_in = _intersection_measure(layers.get("parks"), geometry, mode="area")
        schools_count, _ = _count_intersections(layers.get("schools"), geometry)
        hospitals_count, _ = _count_intersections(layers.get("hospitals"), geometry)
        shops_count, shops_in = _count_intersections(layers.get("shops"), geometry)

        building_area, building_intersection_areas = _intersection_measure(
            layers.get("buildings"),
            geometry,
            mode="area",
        )

        if buildings_in is None or buildings_in.empty:
            building_masks = {
                "residential": pd.Series(dtype=bool),
                "commercial": pd.Series(dtype=bool),
                "retail": pd.Series(dtype=bool),
                "public": pd.Series(dtype=bool),
            }
            building_levels = pd.Series(dtype=float)
            residential_area = 0.0
            commercial_area = 0.0
            retail_area = 0.0
            public_area = 0.0
            total_floor_area = 0.0
            building_with_levels_count = 0.0
            mean_building_levels = 0.0
        else:
            building_masks = _building_use_masks(buildings_in)
            building_levels = _building_levels(buildings_in)

            residential_area = float(building_intersection_areas.loc[building_masks["residential"]].sum())
            commercial_area = float(building_intersection_areas.loc[building_masks["commercial"]].sum())
            retail_area = float(building_intersection_areas.loc[building_masks["retail"]].sum())
            public_area = float(building_intersection_areas.loc[building_masks["public"]].sum())

            effective_levels = building_levels.fillna(feature_config.floor_area_fallback_levels).clip(lower=1.0)
            total_floor_area = float((effective_levels * building_intersection_areas).sum())
            building_with_levels_count = float(building_levels.notna().sum())
            mean_building_levels = float(building_levels.dropna().mean()) if building_levels.notna().any() else 0.0

        feature_records.append(
            {
                "Building_Count": float(building_count),
                "Building_Area": float(building_area),
                "Residential_Area": float(residential_area),
                "Commercial_Area": float(commercial_area),
                "Retail_Area": float(retail_area),
                "Public_Area": float(public_area),
                "Road_Length": float(road_length),
                "Bus_Stop_Count": float(bus_stop_count),
                "Park_Area": float(park_area),
                "Building_With_Levels_Count": float(building_with_levels_count),
                "Mean_Building_Levels": float(mean_building_levels),
                "Total_Floor_Area": float(total_floor_area),
                "Schools_Count": float(schools_count),
                "Hospitals_Count": float(hospitals_count),
                "Parks_Shops_Count": float(len(parks_in) + shops_count),
            }
        )

    feature_frame = pd.DataFrame(feature_records, index=grid.index)
    featured_grid = grid.join(feature_frame)

    poi_points = build_poi_reference_points(
        layers=layers,
        poi_layer_names=feature_config.poi_layer_names,
        working_crs=grid.crs,
    )
    featured_grid["POI_Access_Index"] = compute_poi_access_index(
        featured_grid,
        poi_points=poi_points,
        neighbors=feature_config.poi_neighbors,
        epsilon_meters=feature_config.poi_index_epsilon_meters,
    )
    featured_grid["Combined_Index"] = compute_combined_index(
        featured_grid,
        feature_columns=feature_config.combined_index_columns,
    )

    return featured_grid


def build_feature_output(
    working_gdf: "gpd.GeoDataFrame",
    display_crs: str = DEFAULT_DISPLAY_CRS,
) -> FeatureComputationResult:
    import geopandas as gpd

    display_gdf = working_gdf.to_crs(display_crs)
    centroids_display = gpd.GeoSeries(
        working_gdf.geometry.centroid,
        crs=working_gdf.crs,
    ).to_crs(display_crs)

    feature_frame = display_gdf.drop(columns="geometry").copy()
    feature_frame["latitude"] = centroids_display.y
    feature_frame["longitude"] = centroids_display.x

    ordered_columns = [column for column in CITY_FEATURE_COLUMNS if column in feature_frame.columns]
    feature_frame = feature_frame[ordered_columns]

    return FeatureComputationResult(
        working_gdf=working_gdf,
        display_gdf=display_gdf,
        feature_frame=feature_frame,
    )
