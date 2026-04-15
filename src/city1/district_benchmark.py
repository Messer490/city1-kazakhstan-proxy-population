from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Iterable, Mapping

import numpy as np
import pandas as pd
from shapely.ops import unary_union

from .city_totals import normalize_city_name
from .crs import infer_working_crs
from .osm import configure_osmnx
from .config import OSMExtractionConfig
from .paths import EXTERNAL_DATA_DIR, PROJECT_ROOT


DEFAULT_DISTRICT_REFERENCE_DIR = EXTERNAL_DATA_DIR / "district_benchmark"
DEFAULT_DISTRICT_REPORTS_DIR = PROJECT_ROOT / "reports" / "district_benchmark_v2"
DEFAULT_OVERPASS_FALLBACKS: tuple[str, ...] = (
    "https://overpass-api.de/api/interpreter",
    "https://lz4.overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
)


@dataclass(frozen=True)
class DistrictBenchmarkMetrics:
    city_name: str
    district_reference_row_count: int
    district_count_total: int
    district_count_compared: int
    boundary_warning_count: int
    official_total: float
    predicted_total: float
    absolute_gap_total: float
    mae: float
    rmse: float
    mape: float
    share_mae: float
    share_rmse: float
    pearson_r: float
    spearman_r: float

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _empty_float(value: float | int) -> float:
    return float(value) if pd.notna(value) else 0.0


def _safe_slug(text: str) -> str:
    normalized = normalize_city_name(text)
    return normalized.replace(" ", "_") or "city"


def _polygonal_only(geometry):
    if geometry is None or geometry.is_empty:
        return None
    if geometry.geom_type in {"Polygon", "MultiPolygon"}:
        return geometry
    if geometry.geom_type == "GeometryCollection":
        polygonal_parts = [
            part
            for part in geometry.geoms
            if not part.is_empty and part.geom_type in {"Polygon", "MultiPolygon"}
        ]
        if not polygonal_parts:
            return None
        return unary_union(polygonal_parts)
    return None


def load_district_reference(path: str | Path) -> pd.DataFrame:
    frame = pd.read_csv(path).copy()
    required = {
        "city_name",
        "district_name",
        "district_query",
        "official_population",
        "use_in_metrics",
    }
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"District reference is missing required columns: {sorted(missing)}")

    frame["normalized_city_name"] = frame["city_name"].map(normalize_city_name)
    frame["normalized_district_name"] = frame["district_name"].map(normalize_city_name)
    frame["official_population"] = pd.to_numeric(frame["official_population"], errors="coerce")
    frame["use_in_metrics"] = frame["use_in_metrics"].map(
        lambda value: str(value).strip().lower() in {"1", "true", "yes"}
    )
    return frame


def _normalize_boundary_label(value: object) -> str:
    import re
    import unicodedata

    text = unicodedata.normalize("NFKC", str(value)).strip().lower()
    text = text.replace("_", " ").replace("-", " ")
    text = (
        text.replace("ı", "i")
        .replace("ï", "i")
        .replace("ü", "u")
        .replace("ұ", "у")
        .replace("қ", "к")
        .replace("ғ", "г")
        .replace("ә", "а")
        .replace("ө", "о")
        .replace("ң", "н")
        .replace("і", "и")
    )
    for token in (
        " district",
        " audany",
        " audanyn",
        " audanyi",
        " rayon",
        " raion",
        " ауданы",
        " ауданынын",
        " ауданының",
        " аудан",
    ):
        text = text.replace(token, "")
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    return " ".join(text.split())


def _match_tokens(record: Mapping[str, object]) -> set[str]:
    tokens = {
        _normalize_boundary_label(record.get("district_name", "")),
        _normalize_boundary_label(record.get("district_query", "")),
    }
    raw_tokens = str(record.get("osm_match_tokens", "")).split("|")
    for token in raw_tokens:
        cleaned = _normalize_boundary_label(token)
        if cleaned:
            tokens.add(cleaned)
    return {token for token in tokens if token}


def _iter_overpass_configs(config: OSMExtractionConfig) -> Iterable[OSMExtractionConfig]:
    seen: set[str | None] = set()
    for endpoint in (config.overpass_endpoint, *DEFAULT_OVERPASS_FALLBACKS):
        if endpoint in seen:
            continue
        seen.add(endpoint)
        yield replace(config, overpass_endpoint=endpoint)


def fetch_district_boundaries(
    reference_frame: pd.DataFrame,
    *,
    osm_config: OSMExtractionConfig | None = None,
    prediction_gdf=None,
):
    import geopandas as gpd
    import osmnx as ox

    config = osm_config or OSMExtractionConfig()

    if reference_frame.empty:
        raise ValueError("District reference frame is empty.")

    city_query = str(reference_frame["city_query"].dropna().iloc[0]) if "city_query" in reference_frame.columns else ""
    if not city_query:
        sample_query = str(reference_frame["district_query"].iloc[0])
        city_query = ",".join(part.strip() for part in sample_query.split(",")[1:]).strip() or sample_query

    candidates = None
    last_error: Exception | None = None
    for active_config in _iter_overpass_configs(config):
        configure_osmnx(active_config)
        try:
            candidates = ox.features_from_place(city_query, {"boundary": "administrative"})
            break
        except Exception as exc:  # pragma: no cover - network dependent
            last_error = exc
            continue

    if candidates is None:
        raise RuntimeError(f"Failed to fetch administrative boundaries for {city_query!r}: {last_error}") from last_error

    if candidates.empty:
        raise RuntimeError(f"No administrative boundary candidates were returned for {city_query!r}.")

    candidates = candidates[candidates.geometry.notna()].copy()
    if "admin_level" in candidates.columns:
        candidates = candidates.loc[candidates["admin_level"].astype(str) == "6"].copy()
    if "boundary" in candidates.columns:
        candidates = candidates.loc[candidates["boundary"].astype(str) == "administrative"].copy()
    if candidates.empty:
        raise RuntimeError(f"No level-6 administrative district polygons were found for {city_query!r}.")

    name_columns = [column for column in ("name", "name:en", "official_name") if column in candidates.columns]
    for column in name_columns:
        candidates[f"_normalized_{column.replace(':', '_')}"] = candidates[column].map(_normalize_boundary_label)

    rows: list[gpd.GeoDataFrame] = []
    failures: list[str] = []

    for record in reference_frame.to_dict(orient="records"):
        tokens = _match_tokens(record)
        matched = pd.Series(False, index=candidates.index)
        for column in name_columns:
            normalized_column = f"_normalized_{column.replace(':', '_')}"
            matched = matched | candidates[normalized_column].isin(tokens)

        subset = candidates.loc[matched].copy()
        if subset.empty:
            failures.append(f"{record['district_name']}: no matching district polygon found in {city_query}")
            continue

        if len(subset) > 1:
            working_crs = infer_working_crs(subset.to_crs("EPSG:4326"))
            subset_working = subset.to_crs(working_crs).copy()
            if prediction_gdf is not None and getattr(prediction_gdf, "empty", True) is False:
                prediction_union = prediction_gdf.to_crs(working_crs).geometry.unary_union
                subset_working["_overlap_rank"] = subset_working.geometry.intersection(prediction_union).area
                subset_working["_area_rank"] = subset_working.geometry.area
                subset = subset_working.sort_values(
                    ["_overlap_rank", "_area_rank"],
                    ascending=[False, False],
                ).head(1).drop(columns=["_overlap_rank", "_area_rank"]).to_crs(candidates.crs)
            else:
                subset_working["_area_rank"] = subset_working.geometry.area
                subset = subset_working.sort_values("_area_rank", ascending=False).head(1).drop(columns="_area_rank").to_crs(candidates.crs)

        district_gdf = subset[["geometry"]].copy()
        for key, value in record.items():
            if key == "geometry":
                continue
            district_gdf[key] = value
        rows.append(district_gdf)

    if not rows:
        raise RuntimeError("No district boundaries could be matched from the city administrative layer.")

    districts = gpd.GeoDataFrame(pd.concat(rows, ignore_index=True), geometry="geometry", crs=rows[0].crs)
    districts = districts[districts.geometry.notna()].copy()
    if districts.empty:
        raise RuntimeError("Fetched district boundary set is empty after geometry filtering.")

    return districts, tuple(failures)


def aggregate_predictions_to_districts(
    prediction_gdf,
    district_gdf,
    *,
    population_column: str = "Population_Estimate_Final",
):
    import geopandas as gpd

    if prediction_gdf.empty:
        raise ValueError("Prediction GeoDataFrame is empty.")
    if district_gdf.empty:
        raise ValueError("District GeoDataFrame is empty.")
    if population_column not in prediction_gdf.columns:
        raise ValueError(f"Prediction GeoDataFrame is missing {population_column!r}.")

    prediction = prediction_gdf.copy()
    districts = district_gdf.copy()

    if prediction.crs is None or districts.crs is None:
        raise ValueError("Both prediction and district GeoDataFrames must have CRS metadata.")

    working_crs = infer_working_crs(prediction.to_crs("EPSG:4326"))
    prediction = prediction.to_crs(working_crs)
    districts = districts.to_crs(working_crs)

    prediction = prediction[prediction.geometry.notna()].copy()
    districts = districts[districts.geometry.notna()].copy()
    prediction["geometry"] = prediction.geometry.map(_polygonal_only)
    districts["geometry"] = districts.geometry.map(_polygonal_only)
    prediction = prediction[prediction.geometry.notna()].copy()
    districts = districts[districts.geometry.notna()].copy()
    prediction["_cell_area"] = prediction.geometry.area
    prediction = prediction.loc[prediction["_cell_area"] > 0].copy()

    intersections = gpd.overlay(
        prediction[["Zone_ID", population_column, "_cell_area", "geometry"]],
        districts,
        how="intersection",
    )
    if intersections.empty:
        raise RuntimeError("No intersections were found between prediction cells and district polygons.")

    intersections["_intersection_area"] = intersections.geometry.area
    intersections["_population_allocated"] = (
        pd.to_numeric(intersections[population_column], errors="coerce").fillna(0.0)
        * intersections["_intersection_area"]
        / intersections["_cell_area"]
    )

    grouped = intersections.groupby(
        ["district_name", "normalized_district_name"], as_index=False
    ).agg(
        predicted_population=("_population_allocated", "sum"),
        intersection_area=("_intersection_area", "sum"),
        official_population=("official_population", "first"),
        district_query=("district_query", "first"),
        source_name=("source_name", "first"),
        source_url=("source_url", "first"),
        source_precision=("source_precision", "first"),
        use_in_metrics=("use_in_metrics", "first"),
    )

    district_base = districts.drop(columns="geometry").copy()
    district_base = district_base[
        [
            "district_name",
            "normalized_district_name",
            "official_population",
            "district_query",
            "source_name",
            "source_url",
            "source_precision",
            "use_in_metrics",
        ]
    ].drop_duplicates(subset=["district_name", "normalized_district_name"])

    result = district_base.merge(
        grouped[["district_name", "normalized_district_name", "predicted_population", "intersection_area"]],
        on=["district_name", "normalized_district_name"],
        how="left",
    )

    result["official_population"] = pd.to_numeric(result["official_population"], errors="coerce")
    result["predicted_population"] = pd.to_numeric(result["predicted_population"], errors="coerce").fillna(0.0)
    result["intersection_area"] = pd.to_numeric(result["intersection_area"], errors="coerce").fillna(0.0)
    result["population_gap"] = result["predicted_population"] - result["official_population"]
    official_total = result["official_population"].sum()
    predicted_total = result["predicted_population"].sum()
    result["official_share"] = np.where(official_total > 0, result["official_population"] / official_total, np.nan)
    result["predicted_share"] = np.where(predicted_total > 0, result["predicted_population"] / predicted_total, np.nan)

    return result.sort_values("district_name").reset_index(drop=True)


def compute_district_benchmark_metrics(
    district_result_frame: pd.DataFrame,
    *,
    city_name: str,
    district_reference_row_count: int | None = None,
    boundary_warning_count: int = 0,
) -> DistrictBenchmarkMetrics:
    if district_result_frame.empty:
        raise ValueError("District result frame is empty.")

    evaluation = district_result_frame.loc[district_result_frame["use_in_metrics"].fillna(False)].copy()
    if evaluation.empty:
        raise ValueError("No districts are marked with use_in_metrics=True.")

    official = pd.to_numeric(evaluation["official_population"], errors="coerce")
    predicted = pd.to_numeric(evaluation["predicted_population"], errors="coerce").fillna(0.0)
    valid = official.notna() & predicted.notna()
    evaluation = evaluation.loc[valid].copy()
    official = official.loc[valid]
    predicted = predicted.loc[valid]

    if evaluation.empty:
        raise ValueError("No valid district rows remained after filtering.")

    errors = predicted - official
    mae = float(np.mean(np.abs(errors)))
    rmse = float(np.sqrt(np.mean(np.square(errors))))
    mape = float(np.mean(np.abs(errors) / official.replace(0, np.nan)) * 100.0)

    official_share = pd.to_numeric(evaluation["official_share"], errors="coerce")
    predicted_share = pd.to_numeric(evaluation["predicted_share"], errors="coerce")
    share_errors = predicted_share - official_share
    share_mae = float(np.mean(np.abs(share_errors)))
    share_rmse = float(np.sqrt(np.mean(np.square(share_errors))))

    pearson_r = float(official.corr(predicted, method="pearson")) if len(evaluation) > 1 else float("nan")
    spearman_r = float(official.corr(predicted, method="spearman")) if len(evaluation) > 1 else float("nan")

    official_total = float(official.sum())
    predicted_total = float(predicted.sum())

    return DistrictBenchmarkMetrics(
        city_name=city_name,
        district_reference_row_count=int(district_reference_row_count or len(district_result_frame)),
        district_count_total=int(len(district_result_frame)),
        district_count_compared=int(len(evaluation)),
        boundary_warning_count=int(boundary_warning_count),
        official_total=float(official_total),
        predicted_total=float(predicted_total),
        absolute_gap_total=float(abs(predicted_total - official_total)),
        mae=float(mae),
        rmse=float(rmse),
        mape=float(mape),
        share_mae=float(share_mae),
        share_rmse=float(share_rmse),
        pearson_r=float(pearson_r),
        spearman_r=float(spearman_r),
    )


def save_district_benchmark_report(
    district_frame: pd.DataFrame,
    metrics: DistrictBenchmarkMetrics,
    *,
    output_dir: str | Path,
) -> dict[str, Path]:
    import matplotlib.pyplot as plt
    import seaborn as sns

    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)

    district_csv = root / "district_benchmark_table.csv"
    metrics_csv = root / "district_benchmark_metrics.csv"
    figure_bar = root / "district_benchmark_bar.png"
    figure_scatter = root / "district_benchmark_scatter.png"
    summary_md = root / "district_benchmark_report.md"

    district_frame.to_csv(district_csv, index=False)
    pd.DataFrame([metrics.to_dict()]).to_csv(metrics_csv, index=False)

    plot_frame = district_frame.copy().sort_values("official_population", ascending=False)
    fig, ax = plt.subplots(figsize=(12, 5))
    x = np.arange(len(plot_frame))
    width = 0.38
    ax.bar(x - width / 2, plot_frame["official_population"], width=width, label="Official", color="#2563eb")
    ax.bar(x + width / 2, plot_frame["predicted_population"], width=width, label="Predicted", color="#059669")
    ax.set_title(f"{metrics.city_name}: District population benchmark")
    ax.set_xlabel("District")
    ax.set_ylabel("Population")
    ax.set_xticks(x)
    ax.set_xticklabels(plot_frame["district_name"], rotation=25, ha="right")
    ax.legend()
    fig.tight_layout()
    fig.savefig(figure_bar, dpi=200, bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 6))
    sns.scatterplot(
        data=district_frame,
        x="official_population",
        y="predicted_population",
        hue="source_precision",
        style="use_in_metrics",
        ax=ax,
        palette="viridis",
    )
    max_value = float(max(district_frame["official_population"].max(), district_frame["predicted_population"].max()))
    ax.plot([0, max_value], [0, max_value], linestyle="--", color="#111827", linewidth=1)
    ax.set_title(f"{metrics.city_name}: official vs predicted by district")
    ax.set_xlabel("Official population")
    ax.set_ylabel("Predicted population")
    fig.tight_layout()
    fig.savefig(figure_scatter, dpi=200, bbox_inches="tight")
    plt.close(fig)

    lines = [
        f"# {metrics.city_name} District Benchmark",
        "",
        f"- District rows in reference: `{metrics.district_reference_row_count}`",
        f"- District polygons matched in OSM: `{metrics.district_count_total}`",
        f"- Districts used in metrics: `{metrics.district_count_compared}`",
        f"- Boundary warnings: `{metrics.boundary_warning_count}`",
        f"- MAE: `{metrics.mae:.3f}`",
        f"- RMSE: `{metrics.rmse:.3f}`",
        f"- MAPE: `{metrics.mape:.3f}`",
        f"- Share MAE: `{metrics.share_mae:.6f}`",
        f"- Share RMSE: `{metrics.share_rmse:.6f}`",
        f"- Pearson r: `{metrics.pearson_r:.6f}`",
        f"- Spearman r: `{metrics.spearman_r:.6f}`",
        "",
        "## Outputs",
        "",
        f"- `{district_csv}`",
        f"- `{metrics_csv}`",
        f"- `{figure_bar}`",
        f"- `{figure_scatter}`",
    ]
    summary_md.write_text("\n".join(lines), encoding="utf-8")

    return {
        "district_table_path": district_csv,
        "metrics_path": metrics_csv,
        "figure_bar_path": figure_bar,
        "figure_scatter_path": figure_scatter,
        "report_path": summary_md,
    }


def load_prediction_geojson(path: str | Path):
    import geopandas as gpd

    return gpd.read_file(path)


def run_district_benchmark(
    *,
    city_name: str,
    prediction_geojson: str | Path,
    district_reference_csv: str | Path,
    output_dir: str | Path,
    osm_config: OSMExtractionConfig | None = None,
) -> dict[str, object]:
    reference_frame = load_district_reference(district_reference_csv)
    normalized_city = normalize_city_name(city_name)
    city_reference = reference_frame.loc[reference_frame["normalized_city_name"] == normalized_city].copy()
    if city_reference.empty:
        raise ValueError(f"No district reference rows found for city {city_name!r}.")

    prediction_gdf = load_prediction_geojson(prediction_geojson)
    district_gdf, boundary_warnings = fetch_district_boundaries(
        city_reference,
        osm_config=osm_config,
        prediction_gdf=prediction_gdf,
    )
    district_table = aggregate_predictions_to_districts(prediction_gdf, district_gdf)
    effective_boundary_warning_count = max(len(boundary_warnings), len(city_reference) - len(district_table))
    metrics = compute_district_benchmark_metrics(
        district_table,
        city_name=city_name,
        district_reference_row_count=len(city_reference),
        boundary_warning_count=effective_boundary_warning_count,
    )
    outputs = save_district_benchmark_report(district_table, metrics, output_dir=output_dir)

    return {
        "city_name": city_name,
        "district_table": district_table,
        "metrics": metrics,
        "boundary_warning_count": effective_boundary_warning_count,
        "boundary_warnings": boundary_warnings,
        **outputs,
    }
