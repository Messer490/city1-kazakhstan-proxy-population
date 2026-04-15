from __future__ import annotations

from dataclasses import dataclass
from math import ceil, isfinite, log
from pathlib import Path
from time import perf_counter

import numpy as np
import pandas as pd

from .config import FeaturePipelineConfig, GridConfig
from .inference import (
    DEFAULT_TOTALS_CSV,
    CityInferenceError,
    get_preferred_model_path,
    load_model_artifact,
    run_city_inference,
    save_city_inference_outputs,
    slugify_place_name,
)


@dataclass(frozen=True)
class GridBenchmarkConfig:
    place_names: tuple[str, ...]
    cell_sizes: tuple[int, ...] = (250, 500, 1000)
    model_path: Path | None = None
    totals_csv: Path = DEFAULT_TOTALS_CSV
    save_city_outputs: bool = False


@dataclass
class GridBenchmarkResult:
    run_results: pd.DataFrame
    cell_size_summary: pd.DataFrame
    city_recommendations: pd.DataFrame
    global_recommendation: dict[str, object]


def _safe_log_distance_from_one(value: float) -> float:
    if value <= 0 or not isfinite(value):
        return float("inf")
    return abs(log(value))


def _population_concentration_share(series: pd.Series, top_share: float = 0.10) -> float:
    values = pd.to_numeric(series, errors="coerce").fillna(0.0).clip(lower=0.0)
    if values.empty:
        return float("nan")
    total = float(values.sum())
    if total <= 0:
        return 0.0
    top_count = max(1, int(ceil(len(values) * top_share)))
    top_total = float(values.nlargest(top_count).sum())
    return top_total / total


def _qa_warning_count(qa_flags: pd.DataFrame) -> int:
    if qa_flags is None or qa_flags.empty or "severity" not in qa_flags.columns:
        return 0
    return int((qa_flags["severity"].astype(str) == "warning").sum())


def _qa_error_count(qa_flags: pd.DataFrame) -> int:
    if qa_flags is None or qa_flags.empty or "severity" not in qa_flags.columns:
        return 0
    return int((qa_flags["severity"].astype(str) == "error").sum())


def _city_score(row: pd.Series) -> float:
    calibration_distance = float(row.get("calibration_distance_from_one", float("inf")))
    qa_warnings = int(row.get("qa_warning_count", 0))
    osm_warnings = int(row.get("osm_warning_count", 0))
    runtime_seconds = float(row.get("runtime_seconds", 0.0))
    return calibration_distance + 0.05 * qa_warnings + 0.10 * osm_warnings + 0.001 * runtime_seconds


def _benchmark_row_from_result(
    place_name: str,
    cell_size: int,
    result,
    runtime_seconds: float,
    model_path: Path,
    save_paths: dict[str, str] | None = None,
) -> dict[str, object]:
    output = result.output_frame
    final_population = pd.to_numeric(output["Population_Estimate_Final"], errors="coerce").fillna(0.0)
    qa_summary = result.qa_city_summary or {}
    calibration_factor = float(result.calibration_factor)
    save_paths = save_paths or {}

    return {
        "place_name": place_name,
        "city_name": str(output["city_name"].iloc[0]) if "city_name" in output.columns and not output.empty else place_name,
        "normalized_city_name": str(result.normalized_city_name),
        "cell_size_meters": int(cell_size),
        "model_name": str(result.model.model_name),
        "model_path": str(model_path),
        "success": True,
        "error_message": "",
        "runtime_seconds": float(runtime_seconds),
        "zones": int(len(output)),
        "cell_area_sq_km": float((cell_size * cell_size) / 1_000_000.0),
        "official_population": int(result.official_population),
        "raw_prediction_sum": float(result.raw_prediction_sum),
        "calibration_factor": calibration_factor,
        "calibration_distance_from_one": _safe_log_distance_from_one(calibration_factor),
        "final_population_sum": float(final_population.sum()),
        "median_cell_population": float(final_population.median()) if not final_population.empty else float("nan"),
        "p95_cell_population": float(final_population.quantile(0.95)) if not final_population.empty else float("nan"),
        "top_10pct_population_share": _population_concentration_share(final_population, top_share=0.10),
        "qa_warning_count": _qa_warning_count(result.qa_flags),
        "qa_error_count": _qa_error_count(result.qa_flags),
        "osm_warning_count": int(len(result.feature_artifacts.layers.warnings)),
        "qa_high_zero_share_feature_count": int(qa_summary.get("high_zero_share_feature_count", 0)),
        "building_area_zero_share": float(qa_summary.get("building_area_zero_share", float("nan"))),
        "road_length_zero_share": float(qa_summary.get("road_length_zero_share", float("nan"))),
        "total_floor_area_zero_share": float(qa_summary.get("total_floor_area_zero_share", float("nan"))),
        "saved_csv_path": str(save_paths.get("csv_path", "")),
        "saved_geojson_path": str(save_paths.get("geojson_path", "")),
    }


def _error_row(place_name: str, cell_size: int, model_path: Path, runtime_seconds: float, exc: Exception) -> dict[str, object]:
    return {
        "place_name": place_name,
        "city_name": place_name.split(",")[0].strip(),
        "normalized_city_name": slugify_place_name(place_name).replace("_", " "),
        "cell_size_meters": int(cell_size),
        "model_name": load_model_artifact(model_path).model_name if model_path.exists() else model_path.stem,
        "model_path": str(model_path),
        "success": False,
        "error_message": str(exc),
        "runtime_seconds": float(runtime_seconds),
        "zones": 0,
        "cell_area_sq_km": float((cell_size * cell_size) / 1_000_000.0),
        "official_population": np.nan,
        "raw_prediction_sum": np.nan,
        "calibration_factor": np.nan,
        "calibration_distance_from_one": float("inf"),
        "final_population_sum": np.nan,
        "median_cell_population": np.nan,
        "p95_cell_population": np.nan,
        "top_10pct_population_share": np.nan,
        "qa_warning_count": np.nan,
        "qa_error_count": np.nan,
        "osm_warning_count": np.nan,
        "qa_high_zero_share_feature_count": np.nan,
        "building_area_zero_share": np.nan,
        "road_length_zero_share": np.nan,
        "total_floor_area_zero_share": np.nan,
        "saved_csv_path": "",
        "saved_geojson_path": "",
    }


def _city_recommendations(run_results: pd.DataFrame) -> pd.DataFrame:
    success = run_results.loc[run_results["success"]].copy()
    if success.empty:
        return pd.DataFrame(columns=["city_name", "recommended_cell_size_meters", "benchmark_score"])

    success["benchmark_score"] = success.apply(_city_score, axis=1)
    best_rows = (
        success.sort_values(
            ["city_name", "benchmark_score", "qa_warning_count", "osm_warning_count", "runtime_seconds"],
            ascending=[True, True, True, True, True],
        )
        .groupby("city_name", as_index=False)
        .first()
    )

    return best_rows[
        [
            "city_name",
            "place_name",
            "cell_size_meters",
            "benchmark_score",
            "calibration_factor",
            "calibration_distance_from_one",
            "qa_warning_count",
            "osm_warning_count",
            "zones",
            "runtime_seconds",
        ]
    ].rename(columns={"cell_size_meters": "recommended_cell_size_meters"})


def _cell_size_summary(run_results: pd.DataFrame) -> pd.DataFrame:
    success = run_results.loc[run_results["success"]].copy()
    if success.empty:
        return pd.DataFrame()

    summary = (
        success.groupby("cell_size_meters", as_index=False)
        .agg(
            cities=("city_name", "nunique"),
            total_runs=("place_name", "count"),
            mean_runtime_seconds=("runtime_seconds", "mean"),
            mean_zones=("zones", "mean"),
            mean_calibration_factor=("calibration_factor", "mean"),
            median_calibration_factor=("calibration_factor", "median"),
            mean_calibration_distance_from_one=("calibration_distance_from_one", "mean"),
            median_calibration_distance_from_one=("calibration_distance_from_one", "median"),
            mean_qa_warning_count=("qa_warning_count", "mean"),
            mean_osm_warning_count=("osm_warning_count", "mean"),
            mean_top_10pct_population_share=("top_10pct_population_share", "mean"),
        )
        .sort_values("cell_size_meters")
        .reset_index(drop=True)
    )

    summary["benchmark_score"] = (
        summary["mean_calibration_distance_from_one"]
        + 0.05 * summary["mean_qa_warning_count"]
        + 0.10 * summary["mean_osm_warning_count"]
        + 0.001 * summary["mean_runtime_seconds"]
    )
    return summary.sort_values(["benchmark_score", "cell_size_meters"], ascending=[True, True]).reset_index(drop=True)


def _global_recommendation(cell_size_summary: pd.DataFrame) -> dict[str, object]:
    if cell_size_summary.empty:
        return {}
    best = cell_size_summary.iloc[0]
    return {
        "recommended_cell_size_meters": int(best["cell_size_meters"]),
        "benchmark_score": float(best["benchmark_score"]),
        "mean_calibration_distance_from_one": float(best["mean_calibration_distance_from_one"]),
        "mean_runtime_seconds": float(best["mean_runtime_seconds"]),
        "cities": int(best["cities"]),
    }


def run_grid_size_benchmark(
    config: GridBenchmarkConfig,
    *,
    output_dir: str | Path | None = None,
) -> GridBenchmarkResult:
    model_path = Path(config.model_path) if config.model_path else get_preferred_model_path()
    rows: list[dict[str, object]] = []
    city_output_dir = Path(output_dir) / "city_runs" if output_dir and config.save_city_outputs else None

    for place_name in config.place_names:
        for cell_size in config.cell_sizes:
            started = perf_counter()
            try:
                result = run_city_inference(
                    place_name=place_name,
                    model_path=model_path,
                    totals_csv=config.totals_csv,
                    pipeline_config=FeaturePipelineConfig(grid=GridConfig(cell_size_meters=int(cell_size))),
                )
                runtime_seconds = perf_counter() - started
                save_paths: dict[str, str] = {}
                if city_output_dir is not None:
                    stem = f"{slugify_place_name(place_name)}__{int(cell_size)}m__{result.model.model_name}"
                    saved = save_city_inference_outputs(result, city_output_dir, stem=stem)
                    save_paths = {name: str(path) for name, path in saved.items()}
                rows.append(
                    _benchmark_row_from_result(
                        place_name=place_name,
                        cell_size=int(cell_size),
                        result=result,
                        runtime_seconds=runtime_seconds,
                        model_path=model_path,
                        save_paths=save_paths,
                    )
                )
            except Exception as exc:
                runtime_seconds = perf_counter() - started
                rows.append(_error_row(place_name, int(cell_size), model_path, runtime_seconds, exc))

    run_results = pd.DataFrame(rows)
    cell_size_summary = _cell_size_summary(run_results)
    city_recommendations = _city_recommendations(run_results)
    global_recommendation = _global_recommendation(cell_size_summary)

    return GridBenchmarkResult(
        run_results=run_results,
        cell_size_summary=cell_size_summary,
        city_recommendations=city_recommendations,
        global_recommendation=global_recommendation,
    )


def save_grid_size_benchmark(
    result: GridBenchmarkResult,
    output_dir: str | Path,
) -> dict[str, Path]:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)

    run_results_path = root / "grid_size_run_results.csv"
    summary_path = root / "grid_size_summary.csv"
    city_recommendations_path = root / "grid_size_city_recommendations.csv"
    report_path = root / "grid_size_benchmark_report.md"

    result.run_results.to_csv(run_results_path, index=False)
    result.cell_size_summary.to_csv(summary_path, index=False)
    result.city_recommendations.to_csv(city_recommendations_path, index=False)

    lines = ["# Grid Size Benchmark v2", ""]
    if result.global_recommendation:
        lines.extend(
            [
                "## Global recommendation",
                "",
                f"- Recommended default cell size: `{result.global_recommendation['recommended_cell_size_meters']} m`",
                f"- Benchmark score: `{result.global_recommendation['benchmark_score']:.6f}`",
                f"- Mean calibration distance from 1: `{result.global_recommendation['mean_calibration_distance_from_one']:.6f}`",
                f"- Mean runtime seconds: `{result.global_recommendation['mean_runtime_seconds']:.2f}`",
                f"- Cities evaluated: `{result.global_recommendation['cities']}`",
                "",
            ]
        )
    else:
        lines.extend(["## Global recommendation", "", "No successful benchmark runs were available.", ""])

    if not result.city_recommendations.empty:
        lines.extend(["## City recommendations", ""])
        for _, row in result.city_recommendations.iterrows():
            lines.append(
                f"- {row['city_name']}: `{int(row['recommended_cell_size_meters'])} m` "
                f"(score `{float(row['benchmark_score']):.6f}`, calibration factor `{float(row['calibration_factor']):.3f}`)"
            )
        lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")

    return {
        "run_results_path": run_results_path,
        "summary_path": summary_path,
        "city_recommendations_path": city_recommendations_path,
        "report_path": report_path,
    }
