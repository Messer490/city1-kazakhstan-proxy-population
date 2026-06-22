from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Mapping

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from .city_totals import normalize_city_name
from .paths import EXTERNAL_DATA_DIR, PROCESSED_DATA_DIR, PROJECT_ROOT

try:  # pragma: no cover - optional dependency in the default venv
    import rasterio
    from rasterio.features import rasterize
    from rasterio.windows import from_bounds
except ImportError:  # pragma: no cover - handled at runtime
    rasterio = None
    rasterize = None
    from_bounds = None


DEFAULT_EXTERNAL_BENCHMARK_DIR = EXTERNAL_DATA_DIR / "external_benchmarks"
DEFAULT_INFERENCE_RUNS_DIR = PROCESSED_DATA_DIR / "inference_runs"
DEFAULT_WORLDPOP_RASTER = (
    DEFAULT_EXTERNAL_BENCHMARK_DIR / "worldpop" / "worldpop_kazakhstan_2025_raw.tif"
)
DEFAULT_GHS_TILE_MAP: Mapping[str, tuple[str, ...]] = {
    "almaty": ("GHS_POP_E2025_GLOBE_R2023A_4326_3ss_V1_0_R5_C26.tif",),
    "astana": ("GHS_POP_E2025_GLOBE_R2023A_4326_3ss_V1_0_R4_C26.tif",),
    "shymkent": ("GHS_POP_E2025_GLOBE_R2023A_4326_3ss_V1_0_R5_C25.tif",),
}
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "reports" / "external_benchmark_v2"


@dataclass(frozen=True)
class ExternalBenchmarkConfig:
    inference_runs_dir: Path = DEFAULT_INFERENCE_RUNS_DIR
    worldpop_raster: Path = DEFAULT_WORLDPOP_RASTER
    ghs_pop_dir: Path = DEFAULT_EXTERNAL_BENCHMARK_DIR / "ghs_pop"
    output_dir: Path = DEFAULT_OUTPUT_DIR
    city_slugs: tuple[str, ...] = ("almaty", "astana", "shymkent")
    city_slug_to_name: Mapping[str, str] = None  # type: ignore[assignment]
    city_slug_to_ghs_tiles: Mapping[str, tuple[str, ...]] = None  # type: ignore[assignment]
    city1_population_column: str = "Population_Estimate_Final"
    city1_model_suffix: str = "random_forest"
    top_decile_fraction: float = 0.10
    rasterize_all_touched: bool = True

    def __post_init__(self) -> None:
        if self.city_slug_to_name is None:
            object.__setattr__(
                self,
                "city_slug_to_name",
                {
                    "almaty": "Almaty",
                    "astana": "Astana",
                    "shymkent": "Shymkent",
                },
            )
        if self.city_slug_to_ghs_tiles is None:
            object.__setattr__(self, "city_slug_to_ghs_tiles", DEFAULT_GHS_TILE_MAP)


@dataclass(frozen=True)
class ExternalBenchmarkMetrics:
    city_name: str
    city_slug: str
    benchmark_name: str
    cell_count: int
    raster_count: int
    coverage_ok: bool
    city1_total: float
    benchmark_total: float
    absolute_gap_total: float
    benchmark_to_city1_ratio: float
    pearson_r: float
    spearman_r: float
    top_decile_overlap: float
    hotspot_iou: float

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _require_rasterio() -> None:
    if rasterio is None or rasterize is None or from_bounds is None:
        raise ImportError(
            "City1 external benchmark pipeline requires rasterio. "
            "Run the script with an interpreter where rasterio is installed, "
            "or add rasterio to the active environment."
        )


def _safe_slug(text: str) -> str:
    normalized = normalize_city_name(text)
    return normalized.replace(" ", "_") or "city"


def _resolve_city_geojson(inference_runs_dir: Path, city_slug: str, model_suffix: str) -> Path:
    candidates = sorted(inference_runs_dir.glob(f"{city_slug}*__{model_suffix}.geojson"))
    if not candidates:
        raise FileNotFoundError(
            f"No inference GeoJSON was found for city slug {city_slug!r} under {inference_runs_dir}."
        )
    return candidates[0]


def _load_city1_surface(
    city_slug: str,
    inference_runs_dir: Path,
    population_column: str,
    *,
    model_suffix: str,
):
    import geopandas as gpd

    geojson_path = _resolve_city_geojson(inference_runs_dir, city_slug, model_suffix=model_suffix)
    gdf = gpd.read_file(geojson_path)
    required = {"Zone_ID", "latitude", "longitude", population_column, "city_name"}
    missing = required.difference(gdf.columns)
    if missing:
        raise ValueError(
            f"City1 inference GeoJSON {geojson_path} is missing columns: {sorted(missing)}"
        )
    if gdf.empty:
        raise ValueError(f"City1 inference GeoJSON {geojson_path} is empty.")
    return gdf


def _resolve_ghs_paths(config: ExternalBenchmarkConfig, city_slug: str) -> list[Path]:
    tile_names = config.city_slug_to_ghs_tiles.get(city_slug, ())
    if not tile_names:
        raise KeyError(f"No GHS tile mapping is defined for city slug {city_slug!r}.")
    paths = [config.ghs_pop_dir / tile_name for tile_name in tile_names]
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        raise FileNotFoundError(
            "The following GHS-POP files are missing:\n" + "\n".join(missing)
        )
    return paths


def _safe_corr(series_a: pd.Series, series_b: pd.Series, method: str) -> float:
    frame = pd.DataFrame({"a": pd.to_numeric(series_a, errors="coerce"), "b": pd.to_numeric(series_b, errors="coerce")})
    frame = frame.replace([np.inf, -np.inf], np.nan).dropna()
    if len(frame) < 2:
        return float("nan")
    if frame["a"].nunique() <= 1 or frame["b"].nunique() <= 1:
        return float("nan")
    value = frame["a"].corr(frame["b"], method=method)
    return float(value) if pd.notna(value) else float("nan")


def _compute_hotspot_sets(values: pd.Series, fraction: float) -> set[int]:
    if values.empty:
        return set()
    top_count = max(1, int(np.ceil(len(values) * fraction)))
    return set(values.nlargest(top_count).index.tolist())


def compute_external_surface_metrics(
    aligned_frame: pd.DataFrame,
    *,
    benchmark_column: str,
    city_name: str,
    city_slug: str,
    coverage_ok: bool,
    raster_count: int,
    city1_column: str = "city1_population",
    top_decile_fraction: float = 0.10,
) -> ExternalBenchmarkMetrics:
    city1 = pd.to_numeric(aligned_frame[city1_column], errors="coerce").fillna(0.0)
    benchmark = pd.to_numeric(aligned_frame[benchmark_column], errors="coerce").fillna(0.0)

    city_top = _compute_hotspot_sets(city1, top_decile_fraction)
    benchmark_top = _compute_hotspot_sets(benchmark, top_decile_fraction)
    intersection = len(city_top.intersection(benchmark_top))
    union = len(city_top.union(benchmark_top))
    top_count = max(1, len(city_top))

    city_total = float(city1.sum())
    benchmark_total = float(benchmark.sum())

    return ExternalBenchmarkMetrics(
        city_name=city_name,
        city_slug=city_slug,
        benchmark_name=benchmark_column.replace("_population", ""),
        cell_count=int(len(aligned_frame)),
        raster_count=int(raster_count),
        coverage_ok=bool(coverage_ok),
        city1_total=city_total,
        benchmark_total=benchmark_total,
        absolute_gap_total=float(abs(benchmark_total - city_total)),
        benchmark_to_city1_ratio=float(benchmark_total / city_total) if city_total > 0 else float("nan"),
        pearson_r=_safe_corr(city1, benchmark, method="pearson"),
        spearman_r=_safe_corr(city1, benchmark, method="spearman"),
        top_decile_overlap=float(intersection / top_count) if top_count > 0 else float("nan"),
        hotspot_iou=float(intersection / union) if union > 0 else float("nan"),
    )


def _bounds_cover_city(raster_bounds: tuple[float, float, float, float], city_bounds: tuple[float, float, float, float], tolerance: float = 1e-9) -> bool:
    left, bottom, right, top = raster_bounds
    c_left, c_bottom, c_right, c_top = city_bounds
    return (
        left <= c_left + tolerance
        and bottom <= c_bottom + tolerance
        and right >= c_right - tolerance
        and top >= c_top - tolerance
    )


def _aggregate_raster_to_grid(grid_gdf, raster_paths: list[Path], *, all_touched: bool) -> tuple[pd.Series, bool]:
    _require_rasterio()

    grid_raster = grid_gdf.copy()
    total_values = np.zeros(len(grid_raster), dtype=float)
    coverage_ok = True
    city_bounds = tuple(grid_raster.total_bounds.tolist())

    for raster_path in raster_paths:
        with rasterio.open(raster_path) as dataset:  # type: ignore[union-attr]
            if dataset.crs is None:
                raise ValueError(f"Raster {raster_path} has no CRS.")

            grid_in_raster_crs = grid_raster.to_crs(dataset.crs)
            city_bounds = tuple(grid_in_raster_crs.total_bounds.tolist())
            raster_bounds = (
                float(dataset.bounds.left),
                float(dataset.bounds.bottom),
                float(dataset.bounds.right),
                float(dataset.bounds.top),
            )
            coverage_ok = coverage_ok and _bounds_cover_city(raster_bounds, city_bounds)

            left = max(city_bounds[0], raster_bounds[0])
            bottom = max(city_bounds[1], raster_bounds[1])
            right = min(city_bounds[2], raster_bounds[2])
            top = min(city_bounds[3], raster_bounds[3])
            if not (left < right and bottom < top):
                continue

            window = from_bounds(left, bottom, right, top, transform=dataset.transform)
            window = window.round_offsets().round_lengths()
            if window.width <= 0 or window.height <= 0:
                continue

            data = dataset.read(1, window=window, masked=True)
            if data.size == 0:
                continue

            values = np.asarray(np.ma.filled(data, 0.0), dtype=float)
            values = np.where(np.isfinite(values), values, 0.0)
            values = np.clip(values, a_min=0.0, a_max=None)

            transform = dataset.window_transform(window)
            labels = rasterize(
                ((geometry, idx + 1) for idx, geometry in enumerate(grid_in_raster_crs.geometry)),
                out_shape=values.shape,
                transform=transform,
                fill=0,
                all_touched=all_touched,
                dtype="int32",
            )

            valid_mask = labels > 0
            if np.ma.isMaskedArray(data):
                valid_mask &= ~np.ma.getmaskarray(data)

            if not np.any(valid_mask):
                continue

            flat_labels = labels[valid_mask].ravel()
            flat_values = values[valid_mask].ravel()
            total_values += np.bincount(flat_labels, weights=flat_values, minlength=len(grid_in_raster_crs) + 1)[1:]

    return pd.Series(total_values, index=grid_gdf.index, dtype=float), coverage_ok


def build_city_external_benchmark_alignment(
    city_slug: str,
    config: ExternalBenchmarkConfig | None = None,
):
    pipeline_config = config or ExternalBenchmarkConfig()
    city_name = pipeline_config.city_slug_to_name.get(city_slug, city_slug.title())
    city1_gdf = _load_city1_surface(
        city_slug,
        pipeline_config.inference_runs_dir,
        population_column=pipeline_config.city1_population_column,
        model_suffix=pipeline_config.city1_model_suffix,
    )

    worldpop_paths = [pipeline_config.worldpop_raster]
    missing_worldpop = [str(path) for path in worldpop_paths if not path.exists()]
    if missing_worldpop:
        raise FileNotFoundError(
            "Missing WorldPop input raster(s):\n" + "\n".join(missing_worldpop)
        )

    ghs_paths = _resolve_ghs_paths(pipeline_config, city_slug)
    grid_display = city1_gdf.to_crs("EPSG:4326")

    worldpop_population, worldpop_coverage_ok = _aggregate_raster_to_grid(
        grid_display[["geometry"]].copy(),
        worldpop_paths,
        all_touched=pipeline_config.rasterize_all_touched,
    )
    ghs_population, ghs_coverage_ok = _aggregate_raster_to_grid(
        grid_display[["geometry"]].copy(),
        ghs_paths,
        all_touched=pipeline_config.rasterize_all_touched,
    )

    aligned = city1_gdf.copy()
    aligned["city_slug"] = city_slug
    aligned["city1_population"] = pd.to_numeric(
        aligned[pipeline_config.city1_population_column], errors="coerce"
    ).fillna(0.0)
    aligned["worldpop_population"] = worldpop_population.to_numpy()
    aligned["ghs_pop_population"] = ghs_population.to_numpy()

    worldpop_metrics = compute_external_surface_metrics(
        aligned,
        benchmark_column="worldpop_population",
        city_name=city_name,
        city_slug=city_slug,
        coverage_ok=worldpop_coverage_ok,
        raster_count=len(worldpop_paths),
        top_decile_fraction=pipeline_config.top_decile_fraction,
    )
    ghs_metrics = compute_external_surface_metrics(
        aligned,
        benchmark_column="ghs_pop_population",
        city_name=city_name,
        city_slug=city_slug,
        coverage_ok=ghs_coverage_ok,
        raster_count=len(ghs_paths),
        top_decile_fraction=pipeline_config.top_decile_fraction,
    )

    return aligned, [worldpop_metrics, ghs_metrics]


def _plot_metric_by_city(metrics_df: pd.DataFrame, value_column: str, title: str, output_path: Path) -> None:
    if metrics_df.empty or value_column not in metrics_df.columns:
        return
    fig, ax = plt.subplots(figsize=(9, 4.5))
    sns.barplot(
        data=metrics_df,
        x="city_name",
        y=value_column,
        hue="benchmark_name",
        ax=ax,
    )
    ax.set_title(title)
    ax.set_xlabel("")
    ax.set_ylabel(value_column.replace("_", " ").title())
    ax.tick_params(axis="x", labelrotation=20)
    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def _plot_city_scatter(aligned_gdf, benchmark_column: str, city_name: str, output_path: Path) -> None:
    if aligned_gdf.empty or benchmark_column not in aligned_gdf.columns:
        return

    display = aligned_gdf.copy()
    display["city1_log"] = np.log1p(pd.to_numeric(display["city1_population"], errors="coerce").fillna(0.0))
    display["benchmark_log"] = np.log1p(pd.to_numeric(display[benchmark_column], errors="coerce").fillna(0.0))

    fig, ax = plt.subplots(figsize=(5.5, 5))
    ax.scatter(display["city1_log"], display["benchmark_log"], s=8, alpha=0.45, linewidths=0)
    ax.set_title(f"{city_name}: City1 vs {benchmark_column.replace('_population', '')}")
    ax.set_xlabel("log1p(City1 population)")
    ax.set_ylabel(f"log1p({benchmark_column.replace('_population', '')})")
    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def _frame_to_markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_No rows._"

    display = frame.copy()
    for column in display.columns:
        if pd.api.types.is_float_dtype(display[column]):
            display[column] = display[column].map(
                lambda value: "" if pd.isna(value) else f"{float(value):.6f}"
            )
        else:
            display[column] = display[column].map(lambda value: "" if pd.isna(value) else str(value))

    headers = list(display.columns)
    separator = ["---"] * len(headers)
    rows = ["| " + " | ".join(headers) + " |", "| " + " | ".join(separator) + " |"]
    for record in display.to_dict(orient="records"):
        rows.append("| " + " | ".join(record[column] for column in headers) + " |")
    return "\n".join(rows)


def save_external_benchmark_report(
    aligned_by_city: Mapping[str, object],
    metrics_df: pd.DataFrame,
    output_dir: str | Path,
) -> dict[str, Path]:
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    figures_dir = output_root / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    aligned_paths: list[Path] = []
    aligned_geojson_paths: list[Path] = []

    for city_slug, aligned_gdf in aligned_by_city.items():
        city_root = output_root / city_slug
        city_root.mkdir(parents=True, exist_ok=True)

        aligned_csv = city_root / "external_benchmark_aligned.csv"
        aligned_geojson = city_root / "external_benchmark_aligned.geojson"
        aligned_gdf.drop(columns="geometry").to_csv(aligned_csv, index=False)
        aligned_gdf.to_file(aligned_geojson, driver="GeoJSON")
        aligned_paths.append(aligned_csv)
        aligned_geojson_paths.append(aligned_geojson)

        for benchmark_column in ("worldpop_population", "ghs_pop_population"):
            scatter_path = city_root / f"{benchmark_column.replace('_population', '')}_scatter.png"
            _plot_city_scatter(
                aligned_gdf,
                benchmark_column=benchmark_column,
                city_name=str(aligned_gdf["city_name"].iloc[0]),
                output_path=scatter_path,
            )

    metrics_csv = output_root / "external_benchmark_metrics.csv"
    summary_csv = output_root / "external_benchmark_summary_by_source.csv"
    report_path = output_root / "external_benchmark_report.md"
    pearson_figure = figures_dir / "figure_external_benchmark_pearson.png"
    hotspot_figure = figures_dir / "figure_external_benchmark_hotspot_iou.png"

    metrics_df.to_csv(metrics_csv, index=False)
    summary_df = (
        metrics_df.groupby("benchmark_name", dropna=False)[
            ["pearson_r", "spearman_r", "top_decile_overlap", "hotspot_iou"]
        ]
        .mean()
        .reset_index()
    )
    summary_df.to_csv(summary_csv, index=False)

    _plot_metric_by_city(
        metrics_df,
        value_column="pearson_r",
        title="External Benchmark Pearson Correlation",
        output_path=pearson_figure,
    )
    _plot_metric_by_city(
        metrics_df,
        value_column="hotspot_iou",
        title="External Benchmark Hotspot IoU",
        output_path=hotspot_figure,
    )

    lines = [
        "# External Benchmark Report v2",
        "",
        "This report compares the frozen `City1 v2` `500 m` surface against external population products without city-total rescaling.",
        "",
        "## Scope",
        "",
        "- cities: `Almaty`, `Astana`, `Shymkent`",
        "- primary benchmark: `WorldPop Kazakhstan 2025`",
        "- secondary benchmark: `GHS-POP E2025 / EPSG:4326 / 3 arc-second`",
        "- comparison mode: structural agreement on the frozen `500 m` grid",
        "",
        "## Metrics",
        "",
        _frame_to_markdown_table(metrics_df),
        "",
        "## Summary by Benchmark",
        "",
        _frame_to_markdown_table(summary_df),
        "",
        "## Notes",
        "",
        "- `coverage_ok = True` means the selected raster/tile bounds cover the city grid extent.",
        "- `top_decile_overlap` is the overlap ratio between the top `10%` City1 cells and the top `10%` benchmark cells.",
        "- `hotspot_iou` is the intersection-over-union of those hotspot sets.",
    ]
    report_path.write_text("\n".join(lines), encoding="utf-8")

    return {
        "metrics_path": metrics_csv,
        "summary_path": summary_csv,
        "report_path": report_path,
        "pearson_figure_path": pearson_figure,
        "hotspot_figure_path": hotspot_figure,
        "first_aligned_csv_path": aligned_paths[0] if aligned_paths else metrics_csv,
        "first_aligned_geojson_path": aligned_geojson_paths[0] if aligned_geojson_paths else metrics_csv,
    }


def run_external_benchmark_batch(config: ExternalBenchmarkConfig | None = None) -> dict[str, object]:
    pipeline_config = config or ExternalBenchmarkConfig()
    aligned_by_city: dict[str, object] = {}
    metric_rows: list[dict[str, object]] = []

    for city_slug in pipeline_config.city_slugs:
        aligned_gdf, metrics = build_city_external_benchmark_alignment(city_slug, config=pipeline_config)
        aligned_by_city[city_slug] = aligned_gdf
        metric_rows.extend(metric.to_dict() for metric in metrics)

    metrics_df = pd.DataFrame(metric_rows)
    outputs = save_external_benchmark_report(
        aligned_by_city=aligned_by_city,
        metrics_df=metrics_df,
        output_dir=pipeline_config.output_dir,
    )
    return {
        "aligned_by_city": aligned_by_city,
        "metrics_df": metrics_df,
        **outputs,
    }
