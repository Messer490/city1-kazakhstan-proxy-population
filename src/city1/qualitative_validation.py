from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .crs import prepare_city_geometry
from .paths import EXTERNAL_DATA_DIR, PROCESSED_DATA_DIR, PROJECT_ROOT


DEFAULT_FULL_INFERENCE_DIR = PROCESSED_DATA_DIR / "inference_runs"
DEFAULT_BUILT_FORM_INFERENCE_DIR = (
    PROJECT_ROOT
    / "reports"
    / "ablation_v2"
    / "selected_extras"
    / "external_benchmark_inputs"
    / "built_form_only"
)
DEFAULT_COMPLETENESS_CSV = PROJECT_ROOT / "reports" / "osm_completeness_v2" / "osm_completeness_summary.csv"
DEFAULT_REGISTRY_CSV = EXTERNAL_DATA_DIR / "qualitative_validation_case_registry_v2.csv"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "reports" / "qualitative_validation_v2"

DEFAULT_CITY_SLUGS: tuple[str, ...] = ("almaty", "astana")
DEFAULT_CITY_NAMES: Mapping[str, str] = {
    "almaty": "Almaty",
    "astana": "Astana",
}

REQUIRED_SURFACE_COLUMNS = {
    "Zone_ID",
    "Population_Estimate_Final",
    "Building_Area",
    "Road_Length",
    "Total_Floor_Area",
    "POI_Access_Index",
    "geometry",
}
REGISTRY_COLUMNS = [
    "city_slug",
    "zone_type",
    "case_id",
    "source_component_id",
    "case_title",
    "interpretation_label",
    "include_in_report",
    "narrative_summary",
    "caution_note",
]
CASE_IDS_BY_ZONE = {
    "hotspot": ("H1", "H2"),
    "coldspot": ("L1", "L2"),
}


@dataclass(frozen=True)
class QualitativeValidationConfig:
    full_inference_dir: Path = DEFAULT_FULL_INFERENCE_DIR
    built_form_inference_dir: Path = DEFAULT_BUILT_FORM_INFERENCE_DIR
    completeness_csv: Path = DEFAULT_COMPLETENESS_CSV
    registry_csv: Path = DEFAULT_REGISTRY_CSV
    output_dir: Path = DEFAULT_OUTPUT_DIR
    city_slugs: tuple[str, ...] = DEFAULT_CITY_SLUGS
    city_slug_to_name: Mapping[str, str] | None = None
    hotspot_quantile: float = 0.90
    coldspot_quantile: float = 0.10
    minimum_component_cells: int = 3
    top_components_per_zone: int = 5
    case_buffer_meters: float = 750.0

    def __post_init__(self) -> None:
        if self.city_slug_to_name is None:
            object.__setattr__(self, "city_slug_to_name", DEFAULT_CITY_NAMES)


def _frame_to_markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_No rows._"
    display = frame.copy()
    for column in display.columns:
        if pd.api.types.is_float_dtype(display[column]):
            display[column] = display[column].map(lambda value: "" if pd.isna(value) else f"{float(value):.6f}")
        else:
            display[column] = display[column].map(lambda value: "" if pd.isna(value) else str(value))
    headers = list(display.columns)
    rows = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for record in display.to_dict(orient="records"):
        rows.append("| " + " | ".join(record[column] for column in headers) + " |")
    return "\n".join(rows)


def _safe_slug_fragment(text: str) -> str:
    return "".join(character.lower() if character.isalnum() else "_" for character in text).strip("_")


def _resolve_surface_path(directory: Path, city_slug: str) -> Path:
    candidates = sorted(directory.glob(f"{city_slug}*__random_forest.geojson"))
    if not candidates:
        raise FileNotFoundError(f"No frozen surface GeoJSON found for {city_slug!r} under {directory}.")
    return candidates[0]


def _load_surface(directory: Path, city_slug: str) -> gpd.GeoDataFrame:
    path = _resolve_surface_path(directory, city_slug)
    gdf = gpd.read_file(path)
    missing = REQUIRED_SURFACE_COLUMNS.difference(gdf.columns)
    if missing:
        raise ValueError(f"Surface {path} is missing required columns: {sorted(missing)}")
    if gdf.empty:
        raise ValueError(f"Surface {path} is empty.")
    geom_types = set(gdf.geom_type.astype(str))
    if not geom_types.issubset({"Polygon", "MultiPolygon"}):
        raise ValueError(f"Surface {path} must contain polygon grid cells.")
    return gdf


def _quantile_mask(values: pd.Series, *, zone_type: str, hotspot_quantile: float, coldspot_quantile: float) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce").fillna(0.0)
    if zone_type == "hotspot":
        threshold = float(numeric.quantile(hotspot_quantile))
        return numeric >= threshold
    if zone_type == "coldspot":
        threshold = float(numeric.quantile(coldspot_quantile))
        return numeric <= threshold
    raise ValueError(f"Unknown zone_type: {zone_type}")


def _build_connected_components(candidate_gdf: gpd.GeoDataFrame) -> list[list[int]]:
    if candidate_gdf.empty:
        return []
    candidate = candidate_gdf.reset_index(drop=True)
    sindex = candidate.sindex
    adjacency: dict[int, set[int]] = {idx: set() for idx in range(len(candidate))}
    for idx, geometry in enumerate(candidate.geometry):
        for neighbor in sindex.query(geometry, predicate="touches").tolist():
            if neighbor == idx:
                continue
            adjacency[idx].add(int(neighbor))
            adjacency[int(neighbor)].add(idx)

    visited: set[int] = set()
    components: list[list[int]] = []
    for start in range(len(candidate)):
        if start in visited:
            continue
        stack = [start]
        component: list[int] = []
        visited.add(start)
        while stack:
            node = stack.pop()
            component.append(node)
            for neighbor in adjacency[node]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    stack.append(neighbor)
        components.append(sorted(component))
    return components


def _classify_direction(bounds: tuple[float, float, float, float], centroid_x: float, centroid_y: float) -> str:
    minx, miny, maxx, maxy = bounds
    x_third = (maxx - minx) / 3.0 if maxx > minx else 0.0
    y_third = (maxy - miny) / 3.0 if maxy > miny else 0.0

    if x_third <= 0:
        horizontal = "central"
    elif centroid_x < minx + x_third:
        horizontal = "west"
    elif centroid_x > maxx - x_third:
        horizontal = "east"
    else:
        horizontal = "central"

    if y_third <= 0:
        vertical = "central"
    elif centroid_y < miny + y_third:
        vertical = "south"
    elif centroid_y > maxy - y_third:
        vertical = "north"
    else:
        vertical = "central"

    if horizontal == "central" and vertical == "central":
        return "central"
    if vertical == "central":
        return horizontal
    if horizontal == "central":
        return f"{vertical}-central"
    return f"{vertical}-{horizontal}"


def _aggregate_components(
    city_slug: str,
    zone_type: str,
    candidate_gdf: gpd.GeoDataFrame,
    *,
    minimum_component_cells: int,
    top_components_per_zone: int,
) -> tuple[pd.DataFrame, gpd.GeoDataFrame]:
    candidate = candidate_gdf.reset_index(drop=True).copy()
    components = _build_connected_components(candidate)
    city_bounds = tuple(candidate.total_bounds.tolist()) if not candidate.empty else (0.0, 0.0, 0.0, 0.0)

    rows: list[dict[str, object]] = []
    threshold = float(candidate["selection_threshold"].iloc[0]) if not candidate.empty else float("nan")

    for component in components:
        subset = candidate.iloc[component].copy()
        if len(subset) < minimum_component_cells:
            continue
        dissolved = subset.geometry.unary_union
        centroid = dissolved.centroid
        rows.append(
            {
                "city_slug": city_slug,
                "zone_type": zone_type,
                "raw_component_members": "|".join(str(index) for index in component),
                "cell_count": int(len(subset)),
                "total_population_full": float(subset["Population_Estimate_Final"].sum()),
                "mean_population_full": float(subset["Population_Estimate_Final"].mean()),
                "building_area_mean": float(subset["Building_Area"].mean()),
                "total_floor_area_mean": float(subset["Total_Floor_Area"].mean()),
                "road_length_mean": float(subset["Road_Length"].mean()),
                "poi_access_index_mean": float(subset["POI_Access_Index"].mean()),
                "zone_ids": "|".join(sorted(subset["Zone_ID"].astype(str).tolist())),
                "centroid_x": float(centroid.x),
                "centroid_y": float(centroid.y),
                "direction_label": _classify_direction(city_bounds, float(centroid.x), float(centroid.y)),
                "selection_threshold": threshold,
                "geometry": dissolved,
            }
        )

    if not rows:
        columns = [
            "city_slug",
            "zone_type",
            "source_component_id",
            "rank_within_zone_type",
            "cell_count",
            "total_population_full",
            "mean_population_full",
            "building_area_mean",
            "total_floor_area_mean",
            "road_length_mean",
            "poi_access_index_mean",
            "zone_ids",
            "centroid_x",
            "centroid_y",
            "direction_label",
            "selection_threshold",
        ]
        return (
            pd.DataFrame(columns=columns),
            gpd.GeoDataFrame(columns=columns + ["geometry"], geometry="geometry", crs=candidate.crs),
        )

    summary = pd.DataFrame(rows)
    if zone_type == "hotspot":
        summary = summary.sort_values(
            ["total_population_full", "mean_population_full"],
            ascending=[False, False],
        ).reset_index(drop=True)
    else:
        summary = summary.sort_values(
            ["cell_count", "mean_population_full"],
            ascending=[False, True],
        ).reset_index(drop=True)

    summary = summary.head(top_components_per_zone).copy().reset_index(drop=True)
    summary["rank_within_zone_type"] = np.arange(1, len(summary) + 1)
    summary["source_component_id"] = summary["rank_within_zone_type"].map(lambda rank: f"{zone_type}_{rank:02d}")

    geometry_frame = gpd.GeoDataFrame(summary.copy(), geometry="geometry", crs=candidate.crs)
    summary = summary.drop(columns=["geometry"])
    return summary, geometry_frame


def extract_candidate_components(
    full_surface: gpd.GeoDataFrame,
    *,
    city_slug: str,
    hotspot_quantile: float,
    coldspot_quantile: float,
    minimum_component_cells: int,
    top_components_per_zone: int,
) -> tuple[pd.DataFrame, gpd.GeoDataFrame]:
    candidates: list[pd.DataFrame] = []
    geometries: list[gpd.GeoDataFrame] = []
    numeric_population = pd.to_numeric(full_surface["Population_Estimate_Final"], errors="coerce").fillna(0.0)
    hotspot_threshold = float(numeric_population.quantile(hotspot_quantile))
    coldspot_threshold = float(numeric_population.quantile(coldspot_quantile))

    for zone_type, threshold in (("hotspot", hotspot_threshold), ("coldspot", coldspot_threshold)):
        mask = _quantile_mask(
            full_surface["Population_Estimate_Final"],
            zone_type=zone_type,
            hotspot_quantile=hotspot_quantile,
            coldspot_quantile=coldspot_quantile,
        )
        subset = full_surface.loc[mask].copy()
        subset["selection_threshold"] = threshold
        summary, geometry = _aggregate_components(
            city_slug,
            zone_type,
            subset,
            minimum_component_cells=minimum_component_cells,
            top_components_per_zone=top_components_per_zone,
        )
        candidates.append(summary)
        geometries.append(geometry)

    candidate_table = pd.concat(candidates, ignore_index=True) if candidates else pd.DataFrame()
    geometry_frames = [frame for frame in geometries if not frame.empty]
    if geometry_frames:
        candidate_geometries = gpd.GeoDataFrame(
            pd.concat(geometry_frames, ignore_index=True),
            geometry="geometry",
            crs=full_surface.crs,
        )
    else:
        candidate_geometries = gpd.GeoDataFrame(columns=list(candidate_table.columns) + ["geometry"], geometry="geometry", crs=full_surface.crs)
    if not candidate_table.empty:
        candidate_table = candidate_table.sort_values(["zone_type", "rank_within_zone_type"]).reset_index(drop=True)
    return candidate_table, candidate_geometries


def _seed_registry_template(
    registry_csv: Path,
    *,
    candidate_tables_by_city: Mapping[str, pd.DataFrame],
) -> Path:
    if registry_csv.exists():
        return registry_csv

    rows: list[dict[str, object]] = []
    for city_slug in DEFAULT_CITY_SLUGS:
        table = candidate_tables_by_city.get(city_slug, pd.DataFrame())
        if table.empty:
            continue
        for row in table.to_dict(orient="records"):
            rows.append(
                {
                    "city_slug": city_slug,
                    "zone_type": row["zone_type"],
                    "case_id": "",
                    "source_component_id": row["source_component_id"],
                    "case_title": f"{str(row['direction_label']).title()} {'Hotspot' if row['zone_type'] == 'hotspot' else 'Coldspot'}",
                    "interpretation_label": "",
                    "include_in_report": False,
                    "narrative_summary": "",
                    "caution_note": "",
                }
            )
    registry_frame = pd.DataFrame(rows, columns=REGISTRY_COLUMNS)
    registry_csv.parent.mkdir(parents=True, exist_ok=True)
    registry_frame.to_csv(registry_csv, index=False)
    return registry_csv


def _plot_candidate_overview(
    *,
    city_name: str,
    full_surface: gpd.GeoDataFrame,
    candidate_geometries: gpd.GeoDataFrame,
    output_path: Path,
) -> None:
    fig, ax = plt.subplots(figsize=(8, 8))
    values = np.log1p(pd.to_numeric(full_surface["Population_Estimate_Final"], errors="coerce").fillna(0.0))
    vmax = float(np.nanquantile(values, 0.99)) if len(values) else 0.0
    full_surface.assign(_plot_value=values).plot(
        column="_plot_value",
        ax=ax,
        cmap="viridis",
        linewidth=0.0,
        legend=True,
        vmin=0.0,
        vmax=vmax if vmax > 0 else None,
    )
    hotspot = candidate_geometries.loc[candidate_geometries["zone_type"] == "hotspot"]
    coldspot = candidate_geometries.loc[candidate_geometries["zone_type"] == "coldspot"]
    if not hotspot.empty:
        hotspot.boundary.plot(ax=ax, color="#dc2626", linewidth=1.8)
    if not coldspot.empty:
        coldspot.boundary.plot(ax=ax, color="#2563eb", linewidth=1.8)
    for frame, color in ((hotspot, "#dc2626"), (coldspot, "#2563eb")):
        for _, row in frame.iterrows():
            point = row.geometry.centroid
            ax.text(point.x, point.y, str(row["source_component_id"]), fontsize=8, color=color, ha="center", va="center")
    ax.set_title(f"{city_name}: Candidate Qualitative Zones")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def _to_boolean_series(values: Iterable[object]) -> pd.Series:
    series = pd.Series(list(values))
    return series.map(lambda value: str(value).strip().lower() in {"1", "true", "yes", "y"})


def validate_registry(
    registry_df: pd.DataFrame,
    *,
    candidate_tables_by_city: Mapping[str, pd.DataFrame],
    city_slugs: tuple[str, ...],
) -> pd.DataFrame:
    required = set(REGISTRY_COLUMNS)
    missing = required.difference(registry_df.columns)
    if missing:
        raise ValueError(f"Registry is missing required columns: {sorted(missing)}")

    normalized = registry_df.copy()
    normalized["city_slug"] = normalized["city_slug"].astype(str).str.strip().str.lower()
    normalized["zone_type"] = normalized["zone_type"].astype(str).str.strip().str.lower()
    normalized["case_id"] = normalized["case_id"].fillna("").astype(str).str.strip()
    normalized["source_component_id"] = normalized["source_component_id"].fillna("").astype(str).str.strip()
    normalized["case_title"] = normalized["case_title"].fillna("").astype(str).str.strip()
    normalized["interpretation_label"] = normalized["interpretation_label"].fillna("").astype(str).str.strip()
    normalized["narrative_summary"] = normalized["narrative_summary"].fillna("").astype(str).str.strip()
    normalized["caution_note"] = normalized["caution_note"].fillna("").astype(str).str.strip()
    normalized["include_in_report"] = _to_boolean_series(normalized["include_in_report"])

    invalid_cities = set(normalized["city_slug"]).difference(set(city_slugs))
    if invalid_cities:
        raise ValueError(f"Registry references unsupported cities: {sorted(invalid_cities)}")
    invalid_zone_types = set(normalized["zone_type"]).difference({"hotspot", "coldspot"})
    if invalid_zone_types:
        raise ValueError(f"Registry references invalid zone types: {sorted(invalid_zone_types)}")

    included = normalized.loc[normalized["include_in_report"]].copy()
    if included.empty:
        raise ValueError("Registry must include curated cases for the report.")

    for city_slug in city_slugs:
        city_rows = included.loc[included["city_slug"] == city_slug].copy()
        if len(city_rows) != 4:
            raise ValueError(f"Registry must include exactly 4 cases for {city_slug}.")
        zone_counts = city_rows["zone_type"].value_counts().to_dict()
        if zone_counts.get("hotspot", 0) != 2 or zone_counts.get("coldspot", 0) != 2:
            raise ValueError(f"Registry must include exactly 2 hotspots and 2 coldspots for {city_slug}.")
        for zone_type, expected_ids in CASE_IDS_BY_ZONE.items():
            actual_ids = set(city_rows.loc[city_rows["zone_type"] == zone_type, "case_id"])
            if actual_ids != set(expected_ids):
                raise ValueError(
                    f"Registry must use case ids {expected_ids} for {zone_type} in {city_slug}; got {sorted(actual_ids)}."
                )
        if city_rows["source_component_id"].duplicated().any():
            raise ValueError(f"Registry contains duplicate source_component_id values for {city_slug}.")
        missing_fields = city_rows.loc[
            (city_rows["case_title"] == "")
            | (city_rows["interpretation_label"] == "")
            | (city_rows["narrative_summary"] == "")
        ]
        if not missing_fields.empty:
            raise ValueError(f"Registry has missing required narrative fields for {city_slug}.")

        candidate_table = candidate_tables_by_city.get(city_slug)
        if candidate_table is None or candidate_table.empty:
            raise ValueError(f"No candidate table available for {city_slug}.")
        valid_components = set(candidate_table["source_component_id"].astype(str))
        unknown_components = set(city_rows["source_component_id"]).difference(valid_components)
        if unknown_components:
            raise ValueError(f"Registry references unknown source_component_id values for {city_slug}: {sorted(unknown_components)}")

    return normalized


def _load_completeness_context(completeness_csv: Path) -> pd.DataFrame:
    completeness = pd.read_csv(completeness_csv)
    completeness["city_slug"] = completeness["city_name"].astype(str).str.strip().str.lower().map(_safe_slug_fragment)
    return completeness


def _case_extent(case_geometry, working_crs: object, *, buffer_meters: float, display_crs: str) -> tuple[float, float, float, float]:
    case_gdf = gpd.GeoDataFrame({"geometry": [case_geometry]}, crs=display_crs)
    buffered = case_gdf.to_crs(working_crs).buffer(buffer_meters).to_crs(display_crs)
    return tuple(buffered.total_bounds.tolist())


def _plot_surface_panel(
    ax,
    gdf: gpd.GeoDataFrame,
    *,
    value_column: str,
    cmap: str,
    vmin: float | None,
    vmax: float | None,
    title: str,
) -> None:
    numeric = np.log1p(pd.to_numeric(gdf[value_column], errors="coerce").fillna(0.0))
    plot_gdf = gdf.assign(_plot_value=numeric)
    plot_gdf.plot(column="_plot_value", ax=ax, cmap=cmap, linewidth=0.0, legend=False, vmin=vmin, vmax=vmax)
    ax.set_title(title)
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")


def _build_case_metric_rows(
    *,
    selected_registry: pd.DataFrame,
    candidate_table: pd.DataFrame,
    full_surface: gpd.GeoDataFrame,
    built_surface: gpd.GeoDataFrame,
    completeness_row: pd.Series,
) -> list[dict[str, object]]:
    full_lookup = full_surface.set_index("Zone_ID")
    built_lookup = built_surface.set_index("Zone_ID")
    candidate_lookup = candidate_table.set_index("source_component_id")
    rows: list[dict[str, object]] = []

    for registry_row in selected_registry.to_dict(orient="records"):
        candidate_row = candidate_lookup.loc[str(registry_row["source_component_id"])]
        zone_ids = str(candidate_row["zone_ids"]).split("|")
        full_subset = full_lookup.loc[zone_ids]
        built_subset = built_lookup.loc[zone_ids]
        rows.append(
            {
                "city_slug": registry_row["city_slug"],
                "case_id": registry_row["case_id"],
                "zone_type": registry_row["zone_type"],
                "source_component_id": registry_row["source_component_id"],
                "case_title": registry_row["case_title"],
                "cell_count": int(candidate_row["cell_count"]),
                "total_population_full": float(full_subset["Population_Estimate_Final"].sum()),
                "mean_population_full": float(full_subset["Population_Estimate_Final"].mean()),
                "mean_population_built_form": float(built_subset["Population_Estimate_Final"].mean()),
                "building_area_mean": float(full_subset["Building_Area"].mean()),
                "total_floor_area_mean": float(full_subset["Total_Floor_Area"].mean()),
                "road_length_mean": float(full_subset["Road_Length"].mean()),
                "poi_access_index_mean": float(full_subset["POI_Access_Index"].mean()),
                "completeness_score": float(completeness_row["completeness_score"]),
                "completeness_label": str(completeness_row["completeness_label"]),
                "interpretation_label": registry_row["interpretation_label"],
                "narrative_summary": registry_row["narrative_summary"],
                "caution_note": registry_row["caution_note"],
            }
        )
    return rows


def _city_summary_text(city_name: str, completeness_score: float, completeness_label: str) -> str:
    if completeness_label.lower() == "good":
        return (
            f"{city_name} has a stronger qualitative reading context because its OSM completeness is "
            f"`{completeness_label}` ({completeness_score:.1f}). The selected cases should therefore be read as "
            "relatively convincing examples of dense built-form hotspots and peripheral or open coldspots."
        )
    return (
        f"{city_name} should be interpreted more cautiously because its OSM completeness is "
        f"`{completeness_label}` ({completeness_score:.1f}). Even so, the selected cases still allow a structured "
        "check of whether hotspot and coldspot patterns remain consistent with expected urban morphology."
    )


def save_qualitative_report(
    *,
    summary_df: pd.DataFrame,
    completeness_context: pd.DataFrame,
    output_dir: Path,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "qualitative_validation_report.md"
    completeness_table = completeness_context[["city_name", "completeness_score", "completeness_label"]].copy()

    lines = [
        "# Qualitative Validation Report v2",
        "",
        "This report evaluates whether the frozen `City1 v2` surface is qualitatively consistent with expected intra-urban structure. It is a spatial-plausibility check, not a ground-truth census validation layer.",
        "",
        "## Protocol",
        "",
        "- cities: `Almaty`, `Astana`",
        "- grid: frozen `500 m`",
        "- primary surface: `full_features`",
        "- comparison surface: `built_form_only`",
        "- hotspot source: top `10%` `Population_Estimate_Final` cells, grouped into polygon-touch components",
        "- coldspot source: bottom `10%` `Population_Estimate_Final` cells, grouped into polygon-touch components",
        "- final cases are curator-locked via `qualitative_validation_case_registry_v2.csv`",
        "",
        "## City Context",
        "",
        _frame_to_markdown_table(completeness_table),
        "",
    ]

    for city_slug in DEFAULT_CITY_SLUGS:
        city_name = DEFAULT_CITY_NAMES[city_slug]
        city_rows = summary_df.loc[summary_df["city_slug"] == city_slug].copy()
        completeness_row = completeness_context.loc[completeness_context["city_slug"] == city_slug].iloc[0]
        lines.append(f"## {city_name}")
        lines.append("")
        lines.append(
            _city_summary_text(
                city_name,
                float(completeness_row["completeness_score"]),
                str(completeness_row["completeness_label"]),
            )
        )
        lines.append("")
        for case_id in ("H1", "H2", "L1", "L2"):
            row = city_rows.loc[city_rows["case_id"] == case_id].iloc[0]
            lines.append(
                f"- `{case_id}` `{row['case_title']}`: {row['narrative_summary']} "
                f"(interpretation: `{row['interpretation_label']}`; caution: {row['caution_note']})"
            )
        lines.append("")

    lines.extend(
        [
            "## Limitations",
            "",
            "- qualitative validation is not ground truth",
            "- final cases are analyst-curated from deterministic candidates",
            "- OSM completeness influences how confidently the spatial reading can be interpreted",
            "",
            "## Synthesis",
            "",
            "The predicted surface is qualitatively consistent with expected intra-urban structure: dense residential and central mixed-use areas tend to receive high predicted population, while peripheral green, industrial, and sparsely built zones tend to receive low predicted population.",
            "",
        ]
    )
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def _ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def run_qualitative_scaffold(config: QualitativeValidationConfig) -> dict[str, Path]:
    output_root = _ensure_directory(config.output_dir)
    candidates_dir = _ensure_directory(output_root / "candidates")
    figures_dir = _ensure_directory(output_root / "figures")
    candidate_tables: dict[str, pd.DataFrame] = {}
    outputs: dict[str, Path] = {}

    for city_slug in config.city_slugs:
        full_surface = _load_surface(config.full_inference_dir, city_slug)
        candidate_table, candidate_geometries = extract_candidate_components(
            full_surface,
            city_slug=city_slug,
            hotspot_quantile=config.hotspot_quantile,
            coldspot_quantile=config.coldspot_quantile,
            minimum_component_cells=config.minimum_component_cells,
            top_components_per_zone=config.top_components_per_zone,
        )
        candidate_tables[city_slug] = candidate_table
        csv_path = candidates_dir / f"{city_slug}_candidate_zones.csv"
        geojson_path = candidates_dir / f"{city_slug}_candidate_zones.geojson"
        figure_path = figures_dir / f"figure_candidate_zones_{city_slug}.png"
        candidate_table.to_csv(csv_path, index=False)
        candidate_geometries.to_file(geojson_path, driver="GeoJSON")
        _plot_candidate_overview(
            city_name=config.city_slug_to_name[city_slug],
            full_surface=full_surface,
            candidate_geometries=candidate_geometries,
            output_path=figure_path,
        )
        outputs[f"{city_slug}_candidate_csv_path"] = csv_path
        outputs[f"{city_slug}_candidate_geojson_path"] = geojson_path
        outputs[f"{city_slug}_candidate_figure_path"] = figure_path

    outputs["registry_csv_path"] = _seed_registry_template(
        config.registry_csv,
        candidate_tables_by_city=candidate_tables,
    )
    return outputs


def _plot_overview_figure(
    *,
    city_name: str,
    full_surface: gpd.GeoDataFrame,
    built_surface: gpd.GeoDataFrame,
    selected_cases_gdf: gpd.GeoDataFrame,
    output_path: Path,
) -> None:
    pooled_population = np.log1p(
        pd.concat(
            [
                pd.to_numeric(full_surface["Population_Estimate_Final"], errors="coerce").fillna(0.0),
                pd.to_numeric(built_surface["Population_Estimate_Final"], errors="coerce").fillna(0.0),
            ],
            ignore_index=True,
        )
    )
    population_vmax = float(np.nanquantile(pooled_population, 0.99)) if len(pooled_population) else 0.0
    building_values = np.log1p(pd.to_numeric(full_surface["Building_Area"], errors="coerce").fillna(0.0))
    building_vmax = float(np.nanquantile(building_values, 0.99)) if len(building_values) else 0.0
    road_values = np.log1p(pd.to_numeric(full_surface["Road_Length"], errors="coerce").fillna(0.0))
    road_vmax = float(np.nanquantile(road_values, 0.99)) if len(road_values) else 0.0

    fig, axes = plt.subplots(2, 2, figsize=(14, 12))
    axes = axes.ravel()
    _plot_surface_panel(
        axes[0],
        full_surface,
        value_column="Population_Estimate_Final",
        cmap="viridis",
        vmin=0.0,
        vmax=population_vmax if population_vmax > 0 else None,
        title=f"{city_name}: full_features population surface",
    )
    if not selected_cases_gdf.empty:
        for _, row in selected_cases_gdf.iterrows():
            outline_color = "#dc2626" if row["zone_type"] == "hotspot" else "#2563eb"
            gpd.GeoSeries([row.geometry], crs=full_surface.crs).boundary.plot(ax=axes[0], color=outline_color, linewidth=2.0)
            point = row.geometry.centroid
            axes[0].text(point.x, point.y, str(row["case_id"]), fontsize=9, color="black", ha="center", va="center")
    _plot_surface_panel(
        axes[1],
        built_surface,
        value_column="Population_Estimate_Final",
        cmap="viridis",
        vmin=0.0,
        vmax=population_vmax if population_vmax > 0 else None,
        title=f"{city_name}: built_form_only population surface",
    )
    _plot_surface_panel(
        axes[2],
        full_surface,
        value_column="Building_Area",
        cmap="magma",
        vmin=0.0,
        vmax=building_vmax if building_vmax > 0 else None,
        title=f"{city_name}: Building_Area",
    )
    _plot_surface_panel(
        axes[3],
        full_surface,
        value_column="Road_Length",
        cmap="cividis",
        vmin=0.0,
        vmax=road_vmax if road_vmax > 0 else None,
        title=f"{city_name}: Road_Length",
    )
    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def _plot_case_figure(
    *,
    city_name: str,
    full_surface: gpd.GeoDataFrame,
    selected_cases_gdf: gpd.GeoDataFrame,
    case_buffer_meters: float,
    output_path: Path,
) -> None:
    geometry_bundle = prepare_city_geometry(full_surface[["geometry"]].copy(), city_name)
    log_population = np.log1p(pd.to_numeric(full_surface["Population_Estimate_Final"], errors="coerce").fillna(0.0))
    population_vmax = float(np.nanquantile(log_population, 0.99)) if len(log_population) else 0.0

    fig, axes = plt.subplots(2, 2, figsize=(14, 12))
    axes = axes.ravel()
    ordered_cases = selected_cases_gdf.sort_values("case_id").reset_index(drop=True)
    for ax, (_, case_row) in zip(axes, ordered_cases.iterrows()):
        _plot_surface_panel(
            ax,
            full_surface,
            value_column="Population_Estimate_Final",
            cmap="viridis",
            vmin=0.0,
            vmax=population_vmax if population_vmax > 0 else None,
            title=f"{case_row['case_id']}: {case_row['case_title']}",
        )
        outline_color = "#dc2626" if case_row["zone_type"] == "hotspot" else "#2563eb"
        gpd.GeoSeries([case_row.geometry], crs=full_surface.crs).boundary.plot(ax=ax, color=outline_color, linewidth=2.0)
        minx, miny, maxx, maxy = _case_extent(
            case_row.geometry,
            geometry_bundle.working_crs,
            buffer_meters=case_buffer_meters,
            display_crs=str(full_surface.crs),
        )
        ax.set_xlim(minx, maxx)
        ax.set_ylim(miny, maxy)
    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def run_qualitative_render(config: QualitativeValidationConfig) -> dict[str, Path]:
    output_root = _ensure_directory(config.output_dir)
    figures_dir = _ensure_directory(output_root / "figures")
    candidates_dir = output_root / "candidates"

    candidate_tables_by_city: dict[str, pd.DataFrame] = {}
    candidate_geometries_by_city: dict[str, gpd.GeoDataFrame] = {}
    for city_slug in config.city_slugs:
        candidate_csv = candidates_dir / f"{city_slug}_candidate_zones.csv"
        candidate_geojson = candidates_dir / f"{city_slug}_candidate_zones.geojson"
        if not candidate_csv.exists() or not candidate_geojson.exists():
            raise FileNotFoundError(
                f"Missing scaffold outputs for {city_slug}. Run the scaffold stage before render."
            )
        candidate_tables_by_city[city_slug] = pd.read_csv(candidate_csv)
        candidate_geometries_by_city[city_slug] = gpd.read_file(candidate_geojson)

    registry_df = validate_registry(
        pd.read_csv(config.registry_csv),
        candidate_tables_by_city=candidate_tables_by_city,
        city_slugs=config.city_slugs,
    )
    completeness_context = _load_completeness_context(config.completeness_csv)

    summary_rows: list[dict[str, object]] = []
    outputs: dict[str, Path] = {}
    for city_slug in config.city_slugs:
        city_name = config.city_slug_to_name[city_slug]
        full_surface = _load_surface(config.full_inference_dir, city_slug)
        built_surface = _load_surface(config.built_form_inference_dir, city_slug)
        selected_registry = registry_df.loc[
            (registry_df["city_slug"] == city_slug) & (registry_df["include_in_report"])
        ].copy()
        selected_cases_gdf = candidate_geometries_by_city[city_slug].merge(
            selected_registry,
            on=["city_slug", "zone_type", "source_component_id"],
            how="inner",
            validate="one_to_one",
        )
        selected_cases_gdf = selected_cases_gdf.sort_values("case_id").reset_index(drop=True)
        selected_cases_path = output_root / f"{city_slug}_selected_cases.geojson"
        selected_cases_gdf.to_file(selected_cases_path, driver="GeoJSON")
        outputs[f"{city_slug}_selected_cases_geojson_path"] = selected_cases_path

        completeness_row = completeness_context.loc[completeness_context["city_slug"] == city_slug]
        if completeness_row.empty:
            raise ValueError(f"No OSM completeness context found for {city_slug}.")
        summary_rows.extend(
            _build_case_metric_rows(
                selected_registry=selected_registry,
                candidate_table=candidate_tables_by_city[city_slug],
                full_surface=full_surface,
                built_surface=built_surface,
                completeness_row=completeness_row.iloc[0],
            )
        )

        overview_path = figures_dir / f"figure_qualitative_overview_{city_slug}.png"
        cases_path = figures_dir / f"figure_qualitative_cases_{city_slug}.png"
        _plot_overview_figure(
            city_name=city_name,
            full_surface=full_surface,
            built_surface=built_surface,
            selected_cases_gdf=selected_cases_gdf,
            output_path=overview_path,
        )
        _plot_case_figure(
            city_name=city_name,
            full_surface=full_surface,
            selected_cases_gdf=selected_cases_gdf,
            case_buffer_meters=config.case_buffer_meters,
            output_path=cases_path,
        )
        outputs[f"{city_slug}_overview_figure_path"] = overview_path
        outputs[f"{city_slug}_cases_figure_path"] = cases_path

    summary_df = pd.DataFrame(summary_rows).sort_values(["city_slug", "case_id"]).reset_index(drop=True)
    summary_path = output_root / "qualitative_validation_summary.csv"
    summary_df.to_csv(summary_path, index=False)
    report_path = save_qualitative_report(
        summary_df=summary_df,
        completeness_context=completeness_context.loc[completeness_context["city_slug"].isin(config.city_slugs)].copy(),
        output_dir=output_root,
    )
    outputs["summary_csv_path"] = summary_path
    outputs["report_path"] = report_path
    return outputs
