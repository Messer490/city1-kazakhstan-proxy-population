from __future__ import annotations

from dataclasses import dataclass
import time
from typing import TYPE_CHECKING

from .config import OSMExtractionConfig
from .crs import CityGeometryBundle

if TYPE_CHECKING:
    import geopandas as gpd


@dataclass
class OSMLayerBundle:
    working_crs: object
    layers: dict[str, "gpd.GeoDataFrame"]
    warnings: tuple[str, ...] = ()

    def get(self, name: str):
        return self.layers.get(name)

    def __getitem__(self, name: str):
        return self.layers[name]


def _empty_geodataframe(crs: object) -> "gpd.GeoDataFrame":
    import geopandas as gpd

    return gpd.GeoDataFrame({"geometry": []}, geometry="geometry", crs=crs)


def _normalize_layer_gdf(layer: "gpd.GeoDataFrame", target_crs: object) -> "gpd.GeoDataFrame":
    import geopandas as gpd

    if layer is None or layer.empty:
        return _empty_geodataframe(target_crs)

    frame = gpd.GeoDataFrame(layer.copy(), geometry="geometry", crs=layer.crs)
    frame = frame.reset_index(drop=True)
    frame = frame[frame.geometry.notna()].copy()
    if frame.empty:
        return _empty_geodataframe(target_crs)

    if frame.crs is None:
        raise ValueError("OSM layer was returned without CRS metadata.")

    return frame.to_crs(target_crs)


def configure_osmnx(config: OSMExtractionConfig) -> None:
    import osmnx as ox

    ox.settings.timeout = config.timeout_seconds
    ox.settings.use_cache = config.use_osmnx_cache
    if config.overpass_endpoint:
        ox.settings.overpass_endpoint = config.overpass_endpoint


def _call_with_retries(func, config: OSMExtractionConfig, label: str):
    last_error = None
    attempts = max(1, int(config.request_retries))
    for attempt in range(1, attempts + 1):
        try:
            return func()
        except Exception as exc:  # pragma: no cover - depends on network/OSM service
            last_error = exc
            if attempt >= attempts:
                break
            time.sleep(max(0.0, float(config.retry_sleep_seconds)))
    raise RuntimeError(f"{label} failed after {attempts} attempts: {last_error}") from last_error


def fetch_city_boundary(place_name: str, config: OSMExtractionConfig | None = None):
    import osmnx as ox

    osm_config = config or OSMExtractionConfig()
    configure_osmnx(osm_config)
    return _call_with_retries(
        lambda: ox.geocode_to_gdf(place_name),
        config=osm_config,
        label=f"city geocoding for {place_name!r}",
    )


def _fetch_feature_layer(
    polygon_display,
    tags: dict[str, object],
    target_crs: object,
    layer_name: str,
    config: OSMExtractionConfig,
) -> tuple["gpd.GeoDataFrame", str | None]:
    import osmnx as ox

    try:
        layer = _call_with_retries(
            lambda: ox.features_from_polygon(polygon_display, tags),
            config=config,
            label=layer_name,
        )
        return _normalize_layer_gdf(layer, target_crs), None
    except Exception as exc:  # pragma: no cover - depends on network/OSM service
        return _empty_geodataframe(target_crs), f"{layer_name}: {exc}"


def _fetch_roads_layer(
    polygon_display,
    target_crs: object,
    network_type: str,
    config: OSMExtractionConfig,
) -> tuple["gpd.GeoDataFrame", str | None]:
    import osmnx as ox

    try:
        graph = _call_with_retries(
            lambda: ox.graph_from_polygon(polygon_display, network_type=network_type),
            config=config,
            label="roads",
        )
        roads = ox.graph_to_gdfs(graph, nodes=False)
        return _normalize_layer_gdf(roads, target_crs), None
    except Exception as exc:  # pragma: no cover - depends on network/OSM service
        return _empty_geodataframe(target_crs), f"roads: {exc}"


def extract_osm_layers(
    city_geometry: CityGeometryBundle,
    config: OSMExtractionConfig | None = None,
) -> OSMLayerBundle:
    osm_config = config or OSMExtractionConfig()
    configure_osmnx(osm_config)

    polygon_display = city_geometry.display_geometry
    target_crs = city_geometry.working_crs
    warnings: list[str] = []

    layers: dict[str, "gpd.GeoDataFrame"] = {}

    buildings, warning = _fetch_feature_layer(
        polygon_display,
        osm_config.buildings_tags,
        target_crs,
        "buildings",
        osm_config,
    )
    if warning:
        warnings.append(warning)
    layers["buildings"] = buildings

    roads, warning = _fetch_roads_layer(
        polygon_display,
        target_crs,
        osm_config.network_type,
        osm_config,
    )
    if warning:
        warnings.append(warning)
    layers["roads"] = roads

    for layer_name, tags in (
        ("bus_stops", osm_config.bus_stops_tags),
        ("parks", osm_config.parks_tags),
        ("schools", osm_config.schools_tags),
        ("hospitals", osm_config.hospitals_tags),
        ("shops", osm_config.shops_tags),
    ):
        layer, warning = _fetch_feature_layer(
            polygon_display,
            tags,
            target_crs,
            layer_name,
            osm_config,
        )
        if warning:
            warnings.append(warning)
        layers[layer_name] = layer

    return OSMLayerBundle(
        working_crs=target_crs,
        layers=layers,
        warnings=tuple(warnings),
    )
