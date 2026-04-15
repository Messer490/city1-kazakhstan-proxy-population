from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .config import DEFAULT_DISPLAY_CRS

if TYPE_CHECKING:
    import geopandas as gpd


@dataclass
class CityGeometryBundle:
    place_name: str
    display_crs: str
    working_crs: object
    display_gdf: "gpd.GeoDataFrame"
    working_gdf: "gpd.GeoDataFrame"

    @property
    def display_geometry(self):
        return self.display_gdf.geometry.iloc[0]

    @property
    def working_geometry(self):
        return self.working_gdf.geometry.iloc[0]


def _to_single_geometry_gdf(city_gdf: "gpd.GeoDataFrame") -> "gpd.GeoDataFrame":
    import geopandas as gpd

    geometry = city_gdf.geometry.unary_union
    return gpd.GeoDataFrame({"geometry": [geometry]}, crs=city_gdf.crs)


def normalize_display_crs(
    city_gdf: "gpd.GeoDataFrame",
    display_crs: str = DEFAULT_DISPLAY_CRS,
) -> "gpd.GeoDataFrame":
    if city_gdf.crs is None:
        raise ValueError("City boundary GeoDataFrame must have a CRS.")
    return city_gdf.to_crs(display_crs)


def infer_working_crs(city_gdf_display: "gpd.GeoDataFrame") -> object:
    working_crs = city_gdf_display.estimate_utm_crs()
    if working_crs is None:
        raise ValueError("Failed to infer a projected CRS for the city geometry.")
    return working_crs


def prepare_city_geometry(
    city_gdf: "gpd.GeoDataFrame",
    place_name: str,
    display_crs: str = DEFAULT_DISPLAY_CRS,
) -> CityGeometryBundle:
    display = _to_single_geometry_gdf(normalize_display_crs(city_gdf, display_crs))
    working_crs = infer_working_crs(display)
    working = display.to_crs(working_crs)
    return CityGeometryBundle(
        place_name=place_name,
        display_crs=display_crs,
        working_crs=working_crs,
        display_gdf=display,
        working_gdf=working,
    )

