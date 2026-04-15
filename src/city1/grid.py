from __future__ import annotations

import math
from typing import TYPE_CHECKING

from .config import GridConfig
from .crs import CityGeometryBundle

if TYPE_CHECKING:
    import geopandas as gpd


def validate_grid_config(config: GridConfig) -> None:
    if config.cell_size_meters <= 0:
        raise ValueError("Grid cell size must be positive.")
    if not config.zone_id_prefix:
        raise ValueError("Grid zone_id_prefix must be a non-empty string.")


def generate_city_grid(
    city_geometry: CityGeometryBundle,
    config: GridConfig | None = None,
) -> "gpd.GeoDataFrame":
    import geopandas as gpd
    from shapely.geometry import box

    grid_config = config or GridConfig()
    validate_grid_config(grid_config)

    city_polygon = city_geometry.working_geometry
    minx, miny, maxx, maxy = city_polygon.bounds
    cell_size = grid_config.cell_size_meters

    records: list[dict[str, object]] = []
    zone_number = 1

    n_cols = int(math.ceil((maxx - minx) / cell_size))
    n_rows = int(math.ceil((maxy - miny) / cell_size))

    for col_idx in range(n_cols):
        for row_idx in range(n_rows):
            x0 = minx + col_idx * cell_size
            y0 = miny + row_idx * cell_size
            cell = box(x0, y0, x0 + cell_size, y0 + cell_size)

            if not cell.intersects(city_polygon):
                continue

            geometry = cell.intersection(city_polygon) if grid_config.clip_to_city_boundary else cell
            if geometry.is_empty:
                continue

            records.append(
                {
                    "Zone_ID": f"{grid_config.zone_id_prefix}{zone_number}",
                    "grid_col": col_idx,
                    "grid_row": row_idx,
                    "geometry": geometry,
                }
            )
            zone_number += 1

    if not records:
        raise ValueError("Generated grid is empty. Check city geometry and grid configuration.")

    grid = gpd.GeoDataFrame(records, crs=city_geometry.working_crs)
    grid["cell_area_m2"] = grid.geometry.area
    return grid

