from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import joblib
import numpy as np
import pandas as pd

from .city_totals import CityTotalsLookup, load_city_totals, normalize_city_name
from .config import FeaturePipelineConfig
from .contracts import CITY_OUTPUT_COLUMNS_V3, CITY_SUMMARY_COLUMNS_V3, MODEL_VERSION_V3
from .feature_qa import qa_city_frame
from .features import FeatureComputationResult
from .osm_completeness import OSMCompletenessResult, compute_osm_completeness
from .osm import OSMLayerBundle
from .paths import EXTERNAL_DATA_DIR, MODELS_DIR, PROCESSED_DATA_DIR, PROJECT_ROOT
from .pipeline import FeaturePipelineArtifacts, generate_city_features
from .training import calibrate_predictions_by_city
from .uncertainty import (
    LoadedUncertaintyArtifact,
    UncertaintyConfig,
    align_interval_summary_to_total,
    assign_confidence_bands_from_score,
    compute_confidence_score,
    compute_model_stability_score,
    load_uncertainty_artifact,
    predict_uncertainty_ensemble,
    summarize_ensemble_predictions,
)
from .validation import (
    DatasetValidationReport,
    validate_city_output,
    validate_city_output_v3,
    validate_feature_output,
)

if TYPE_CHECKING:
    import geopandas as gpd


DEFAULT_TOTALS_CSV = EXTERNAL_DATA_DIR / "city_population_reference_v2.csv"
DEFAULT_STATUS_REGISTRY_CSV = EXTERNAL_DATA_DIR / "city_status_registry_v2.csv"
DEFAULT_FEATURES_DIR_V3 = PROCESSED_DATA_DIR / "features_v2_batch1"
DEFAULT_FEATURES_GEOJSON_DIR_V3 = PROCESSED_DATA_DIR / "features_v2_batch1_geojson"
DEFAULT_OSM_COMPLETENESS_CSV_V3 = PROJECT_ROOT / "reports" / "osm_completeness_v2" / "osm_completeness_summary.csv"
DEFAULT_DISTRICT_SUPPORT_CSV_V3 = (
    PROJECT_ROOT / "reports" / "paper_v2_baseline" / "tables" / "district_benchmark_metrics_table.csv"
)


class CityInferenceError(RuntimeError):
    """Base error for user-facing inference failures."""


class ModelArtifactError(CityInferenceError):
    """Raised when a saved model artifact cannot be loaded or interpreted."""


class OfficialPopulationMissingError(CityInferenceError):
    """Raised when no official city total is available for calibration."""


class FeatureGenerationError(CityInferenceError):
    """Raised when generated feature data is invalid for inference."""


@dataclass(frozen=True)
class AvailableModel:
    label: str
    path: Path
    model_name: str


@dataclass(frozen=True)
class LoadedModelArtifact:
    path: Path
    model_name: str
    estimator: Any
    feature_columns: tuple[str, ...]
    use_log_target: bool


@dataclass
class CityInferenceResult:
    place_name: str
    normalized_city_name: str
    model: LoadedModelArtifact | LoadedUncertaintyArtifact
    official_population: int
    raw_prediction_sum: float
    calibration_factor: float
    feature_artifacts: FeaturePipelineArtifacts
    output_frame: pd.DataFrame
    output_gdf: "gpd.GeoDataFrame"
    feature_validation_report: DatasetValidationReport
    output_validation_report: DatasetValidationReport
    qa_city_summary: dict[str, object]
    qa_flags: pd.DataFrame
    osm_completeness: OSMCompletenessResult
    member_predictions: pd.DataFrame | None = None
    uncertainty_interval_summary: dict[str, float] | None = None


def slugify_place_name(place_name: str) -> str:
    cleaned = normalize_city_name(place_name.replace(",", " "))
    return cleaned.replace(" ", "_") or "city"


def _display_city_name(place_name: str) -> str:
    return place_name.split(",")[0].strip()


def _city_slug_from_normalized(normalized_city_name: str) -> str:
    return normalized_city_name.replace(" ", "_")


def _load_local_feature_artifacts(
    place_name: str,
    *,
    features_dir: Path = DEFAULT_FEATURES_DIR_V3,
    geojson_dir: Path = DEFAULT_FEATURES_GEOJSON_DIR_V3,
) -> FeaturePipelineArtifacts | None:
    display_slug = _city_slug_from_normalized(normalize_city_name(_display_city_name(place_name)))
    candidate_slugs = [display_slug]
    place_slug = slugify_place_name(place_name)
    if place_slug not in candidate_slugs:
        candidate_slugs.append(place_slug)

    feature_csv = None
    feature_geojson = None
    for city_slug in candidate_slugs:
        candidate_csv = features_dir / f"{city_slug}.csv"
        candidate_geojson = geojson_dir / f"{city_slug}.geojson"
        if candidate_csv.exists() and candidate_geojson.exists():
            feature_csv = candidate_csv
            feature_geojson = candidate_geojson
            break
    if feature_csv is None or feature_geojson is None:
        return None

    import geopandas as gpd

    feature_frame = pd.read_csv(feature_csv)
    display_gdf = gpd.read_file(feature_geojson)
    if len(display_gdf) == len(feature_frame):
        if "Zone_ID" in display_gdf.columns and "Zone_ID" in feature_frame.columns:
            lat_lon = feature_frame[["Zone_ID"] + [column for column in ("latitude", "longitude") if column in feature_frame.columns]].copy()
            display_gdf = display_gdf.merge(lat_lon, on="Zone_ID", how="left")
        for column in feature_frame.columns:
            if column not in display_gdf.columns:
                display_gdf[column] = feature_frame[column].to_numpy()

    feature_result = FeatureComputationResult(
        working_gdf=display_gdf.copy(),
        display_gdf=display_gdf.copy(),
        feature_frame=feature_frame.copy(),
    )
    return FeaturePipelineArtifacts(
        city_geometry=None,
        grid_working=None,
        layers=OSMLayerBundle(
            working_crs=display_gdf.crs,
            layers={},
            warnings=(),
        ),
        features=feature_result,
    )


def _load_or_generate_feature_artifacts(
    place_name: str,
    *,
    pipeline_config: FeaturePipelineConfig | None = None,
) -> FeaturePipelineArtifacts:
    local = _load_local_feature_artifacts(place_name)
    if local is not None:
        return local
    return generate_city_features(place_name, config=pipeline_config)


def _osm_result_from_row(row: pd.Series) -> OSMCompletenessResult:
    return OSMCompletenessResult(
        city_name=str(row.get("city_name", "")),
        completeness_score=float(row.get("completeness_score", 0.0)),
        completeness_label=str(row.get("completeness_label", "weak")),
        critical_coverage_score=float(row.get("critical_coverage_score", 0.0)),
        optional_coverage_score=float(row.get("optional_coverage_score", 0.0)),
        density_quality_score=float(row.get("density_quality_score", 0.0)),
        warning_quality_score=float(row.get("warning_quality_score", 0.0)),
        osm_warning_count=int(row.get("osm_warning_count", 0)),
        qa_warning_count=int(row.get("qa_warning_count", 0)),
        building_zero_share=float(row.get("building_zero_share", 1.0)),
        road_zero_share=float(row.get("road_zero_share", 1.0)),
        poi_zero_share=float(row.get("poi_zero_share", 1.0)),
        total_floor_area_zero_share=float(row.get("total_floor_area_zero_share", 1.0)),
        bus_stop_zero_share=float(row.get("bus_stop_zero_share", 1.0)),
        park_zero_share=float(row.get("park_zero_share", 1.0)),
        schools_zero_share=float(row.get("schools_zero_share", 1.0)),
        hospitals_zero_share=float(row.get("hospitals_zero_share", 1.0)),
        retail_zero_share=float(row.get("retail_zero_share", 1.0)),
        critical_nonempty_layers=int(row.get("critical_nonempty_layers", 0)),
        optional_nonempty_layers=int(row.get("optional_nonempty_layers", 0)),
    )


def _load_frozen_osm_completeness(normalized_city_name: str) -> OSMCompletenessResult | None:
    path = DEFAULT_OSM_COMPLETENESS_CSV_V3
    if not path.exists():
        return None
    frame = pd.read_csv(path)
    if frame.empty or "city_name" not in frame.columns:
        return None
    normalized = frame["city_name"].astype(str).map(normalize_city_name)
    match = frame.loc[normalized == normalized_city_name]
    if match.empty:
        return None
    return _osm_result_from_row(match.iloc[0])


def _load_status_registry_row(normalized_city_name: str) -> pd.Series | None:
    path = DEFAULT_STATUS_REGISTRY_CSV
    if not path.exists():
        return None
    frame = pd.read_csv(path)
    if frame.empty or "normalized_city_name" not in frame.columns:
        return None
    match = frame.loc[frame["normalized_city_name"].astype(str).map(normalize_city_name) == normalized_city_name]
    if match.empty:
        return None
    return match.iloc[0]


def _resolve_internal_support_context(normalized_city_name: str) -> dict[str, object]:
    path = DEFAULT_DISTRICT_SUPPORT_CSV_V3
    if not path.exists():
        return {
            "internal_support_score": 0.50,
            "district_support_flag": "not_available",
            "district_interval_coverage_available": False,
            "district_interval_coverage_rate": np.nan,
        }

    frame = pd.read_csv(path)
    if frame.empty or "city_name" not in frame.columns:
        return {
            "internal_support_score": 0.50,
            "district_support_flag": "not_available",
            "district_interval_coverage_available": False,
            "district_interval_coverage_rate": np.nan,
        }

    working = frame.copy()
    working["normalized_city_name"] = working["city_name"].astype(str).map(normalize_city_name)
    match = working.loc[working["normalized_city_name"] == normalized_city_name]
    if match.empty:
        return {
            "internal_support_score": 0.50,
            "district_support_flag": "not_available",
            "district_interval_coverage_available": False,
            "district_interval_coverage_rate": np.nan,
        }

    row = match.iloc[0]
    pearson_r = max(float(row.get("pearson_r", 0.0)), 0.0)
    spearman_r = max(float(row.get("spearman_r", 0.0)), 0.0)
    boundary_support = 1.0 if int(row.get("boundary_warning_count", 0)) == 0 else 0.5
    internal_support_score = float(np.clip(0.45 * pearson_r + 0.35 * spearman_r + 0.20 * boundary_support, 0.0, 1.0))
    if internal_support_score >= 0.60:
        district_support_flag = "strong"
    else:
        district_support_flag = "mixed"
    return {
        "internal_support_score": internal_support_score,
        "district_support_flag": district_support_flag,
        "district_interval_coverage_available": False,
        "district_interval_coverage_rate": np.nan,
    }


def _build_hotspot_priority_fields(
    p50: pd.Series,
    confidence_band: pd.Series,
) -> tuple[pd.Series, pd.Series, float]:
    numeric_p50 = pd.to_numeric(p50, errors="coerce").fillna(0.0)
    band = confidence_band.astype(str)
    hotspot_threshold = float(numeric_p50.quantile(0.90))
    p75_threshold = float(numeric_p50.quantile(0.75))
    median_threshold = float(numeric_p50.quantile(0.50))
    hotspot_rank = numeric_p50.rank(method="dense", ascending=False).astype(int)
    priority = pd.Series("not_priority", index=p50.index, dtype="object")

    high_value = numeric_p50 >= hotspot_threshold
    medium_value = (numeric_p50 >= p75_threshold) & (numeric_p50 < hotspot_threshold)
    low_value = numeric_p50 < median_threshold

    priority.loc[high_value & (band == "high")] = "high_value_high_confidence"
    priority.loc[high_value & (band == "low")] = "high_value_low_confidence"
    priority.loc[medium_value & (band == "high")] = "medium_value_high_confidence"
    priority.loc[low_value & (band == "low")] = "low_value_high_uncertainty"
    return hotspot_rank, priority, hotspot_threshold


def _build_city_uncertainty_summary(
    frame: pd.DataFrame,
    *,
    run_id: str,
    model_version: str,
    district_interval_coverage_available: bool,
    district_interval_coverage_rate: float | None,
) -> dict[str, object]:
    hotspot_threshold = float(pd.to_numeric(frame["p50"], errors="coerce").quantile(0.90))
    return {
        "run_id": run_id,
        "model_version": model_version,
        "city": str(frame["city"].iloc[0]),
        "city_slug": str(frame["city_slug"].iloc[0]),
        "n_cells": int(len(frame)),
        "official_total": int(pd.to_numeric(frame["official_city_total"], errors="coerce").iloc[0]),
        "sum_p50": float(pd.to_numeric(frame["p50"], errors="coerce").sum()),
        "p50_total_gap_abs": float(
            abs(
                pd.to_numeric(frame["p50"], errors="coerce").sum()
                - pd.to_numeric(frame["official_city_total"], errors="coerce").iloc[0]
            )
        ),
        "calibrated_member_count": int(pd.to_numeric(frame["calibrated_member_count"], errors="coerce").iloc[0]),
        "mean_uncertainty_width": float(pd.to_numeric(frame["uncertainty_width"], errors="coerce").mean()),
        "median_relative_uncertainty": float(pd.to_numeric(frame["relative_uncertainty"], errors="coerce").median()),
        "mean_confidence_score": float(pd.to_numeric(frame["confidence_score"], errors="coerce").mean()),
        "share_high_confidence": float((frame["confidence_band"].astype(str) == "high").mean()),
        "share_medium_confidence": float((frame["confidence_band"].astype(str) == "medium").mean()),
        "share_low_confidence": float((frame["confidence_band"].astype(str) == "low").mean()),
        "hotspot_threshold_p90": hotspot_threshold,
        "n_high_confidence_hotspots": int((frame["hotspot_priority_class"].astype(str) == "high_value_high_confidence").sum()),
        "n_low_confidence_hotspots": int((frame["hotspot_priority_class"].astype(str) == "high_value_low_confidence").sum()),
        "n_low_value_high_uncertainty": int((frame["hotspot_priority_class"].astype(str) == "low_value_high_uncertainty").sum()),
        "osm_completeness_score": float(pd.to_numeric(frame["osm_completeness_score"], errors="coerce").iloc[0]),
        "osm_completeness_label": str(frame["osm_completeness_label"].iloc[0]),
        "external_agreement_score": float(pd.to_numeric(frame["external_agreement_score"], errors="coerce").iloc[0]),
        "district_support_flag": str(frame["district_support_flag"].iloc[0]),
        "district_interval_coverage_available": bool(district_interval_coverage_available),
        "district_interval_coverage_rate": district_interval_coverage_rate,
    }


def list_available_models(models_dir: str | Path = MODELS_DIR) -> list[AvailableModel]:
    candidates = sorted(Path(models_dir).rglob("*_model_v2.joblib"))
    models: list[AvailableModel] = []

    for path in candidates:
        model_name = path.name.replace("_model_v2.joblib", "")
        label = f"{path.parent.name} / {model_name}"
        models.append(AvailableModel(label=label, path=path, model_name=model_name))

    return models


def list_available_uncertainty_models(models_dir: str | Path = MODELS_DIR) -> list[AvailableModel]:
    models_root = Path(models_dir)
    candidates = sorted(models_root.rglob("ensemble_model.joblib"))
    if not candidates:
        candidates = sorted(models_root.rglob("*_uncertainty_model_v3.joblib"))
    models: list[AvailableModel] = []
    for path in candidates:
        if path.name == "ensemble_model.joblib":
            model_name = path.parent.name
            label = path.parent.name
        else:
            model_name = path.name.replace("_uncertainty_model_v3.joblib", "")
            label = f"{path.parent.name} / {model_name}"
        models.append(AvailableModel(label=label, path=path, model_name=model_name))
    return models


def get_preferred_model_path(models_dir: str | Path = MODELS_DIR) -> Path:
    models_root = Path(models_dir)
    comparison_files = sorted(
        models_root.rglob("model_comparison.csv"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )

    for comparison_path in comparison_files:
        frame = pd.read_csv(comparison_path)
        if frame.empty or "model_name" not in frame.columns:
            continue
        best_model_name = str(frame.iloc[0]["model_name"]).strip()
        candidate = comparison_path.parent / f"{best_model_name}_model_v2.joblib"
        if candidate.exists():
            return candidate

    available = list_available_models(models_root)
    if not available:
        raise ModelArtifactError(f"No v2 model artifacts were found under {models_root}")
    return available[0].path


def get_preferred_uncertainty_model_path(models_dir: str | Path = MODELS_DIR) -> Path:
    available = list_available_uncertainty_models(models_dir)
    if not available:
        raise ModelArtifactError(f"No v3 uncertainty model artifacts were found under {models_dir}")
    return sorted(available, key=lambda item: item.path.stat().st_mtime, reverse=True)[0].path


def load_model_artifact(path: str | Path) -> LoadedModelArtifact:
    artifact_path = Path(path)
    payload = joblib.load(artifact_path)
    if not isinstance(payload, dict):
        raise ModelArtifactError(f"Unexpected model artifact structure in {artifact_path}")

    missing_keys = {"model_name", "estimator", "feature_columns", "use_log_target"}.difference(payload.keys())
    if missing_keys:
        raise ModelArtifactError(
            f"Model artifact {artifact_path} is missing keys: {sorted(missing_keys)}"
        )

    return LoadedModelArtifact(
        path=artifact_path,
        model_name=str(payload["model_name"]),
        estimator=payload["estimator"],
        feature_columns=tuple(payload["feature_columns"]),
        use_log_target=bool(payload["use_log_target"]),
    )


def _inverse_transform_predictions(values: np.ndarray, use_log_target: bool) -> np.ndarray:
    if not use_log_target:
        return values
    return np.expm1(values)


def _predict_raw_population(
    feature_frame: pd.DataFrame,
    model: LoadedModelArtifact,
) -> pd.Series:
    missing_columns = [column for column in model.feature_columns if column not in feature_frame.columns]
    if missing_columns:
        raise FeatureGenerationError(
            f"Generated feature frame is missing model columns: {', '.join(missing_columns)}"
        )

    features = feature_frame[list(model.feature_columns)].copy()
    features = features.apply(pd.to_numeric, errors="coerce").fillna(0.0)
    raw_pred = model.estimator.predict(features)
    raw_pred = _inverse_transform_predictions(np.asarray(raw_pred, dtype=float), model.use_log_target)
    raw_pred = np.clip(raw_pred, a_min=0.0, a_max=None)
    return pd.Series(raw_pred, index=feature_frame.index, dtype=float)


def _lookup_official_population(
    place_name: str,
    totals_lookup: CityTotalsLookup,
) -> tuple[str, int]:
    city_display_name = _display_city_name(place_name)
    normalized = normalize_city_name(city_display_name)
    official_population = totals_lookup.get_population(normalized)
    if official_population is None:
        raise OfficialPopulationMissingError(
            f"No official city total was found for {city_display_name!r} in the v2 population reference. "
            "City1 v2 currently supports calibrated-only inference for cities present in "
            "data/external/city_population_reference_v2.csv."
        )
    return normalized, int(official_population)


def _build_output_frame(
    feature_frame: pd.DataFrame,
    raw_prediction: pd.Series,
    calibrated_prediction: pd.Series,
    place_name: str,
    model: LoadedModelArtifact,
    official_population: int,
) -> pd.DataFrame:
    city_display_name = _display_city_name(place_name)
    raw_sum = float(raw_prediction.sum())
    calibration_factor = float(official_population / raw_sum) if raw_sum > 0 else 0.0

    output = feature_frame.copy()
    output["city_name"] = city_display_name
    output["model_name"] = model.model_name
    output["Official_City_Population"] = int(official_population)
    output["Population_Prediction_Raw"] = raw_prediction.to_numpy()
    output["Calibration_Factor"] = calibration_factor
    output["Population_Estimate_Final"] = calibrated_prediction.to_numpy()
    return output


def _attach_uncertainty_output(
    output_frame: pd.DataFrame,
    summary_frame: pd.DataFrame,
    confidence_band: pd.Series,
) -> pd.DataFrame:
    output = output_frame.copy()
    for column in summary_frame.columns:
        output[column] = pd.to_numeric(summary_frame[column], errors="coerce").fillna(0.0).to_numpy()
    output["Population_Confidence_Band"] = confidence_band.astype(str).to_numpy()
    output["Population_Estimate_Final"] = output["Population_Estimate_P50"].to_numpy()
    return output


def save_city_inference_outputs(
    result: CityInferenceResult,
    output_dir: str | Path,
    stem: str | None = None,
) -> dict[str, Path]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    base_name = stem or f"{slugify_place_name(result.place_name)}__{result.model.model_name}"
    csv_path = output_path / f"{base_name}.csv"
    geojson_path = output_path / f"{base_name}.geojson"

    result.output_frame.to_csv(csv_path, index=False)
    result.output_gdf.to_file(geojson_path, driver="GeoJSON")

    return {
        "csv_path": csv_path,
        "geojson_path": geojson_path,
    }


def save_city_uncertainty_outputs(
    result: CityInferenceResult,
    output_dir: str | Path,
) -> dict[str, Path]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    city_slug = str(result.output_frame["city_slug"].iloc[0])
    run_id = str(result.output_frame["run_id"].iloc[0])
    model_version = str(result.output_frame["model_version"].iloc[0])

    csv_path = output_path / f"{city_slug}_uncertainty_cells.csv"
    geojson_path = output_path / f"{city_slug}_uncertainty_cells.geojson"
    summary_path = output_path / "city_uncertainty_summary.csv"

    result.output_frame.to_csv(csv_path, index=False)
    result.output_gdf.to_file(geojson_path, driver="GeoJSON")

    summary_row = _build_city_uncertainty_summary(
        result.output_frame,
        run_id=run_id,
        model_version=model_version,
        district_interval_coverage_available=False,
        district_interval_coverage_rate=None,
    )
    if summary_path.exists():
        summary_frame = pd.read_csv(summary_path)
        summary_frame = summary_frame.loc[summary_frame["city_slug"].astype(str) != city_slug].copy()
        summary_frame = pd.concat([summary_frame, pd.DataFrame([summary_row])], ignore_index=True)
    else:
        summary_frame = pd.DataFrame([summary_row])
    for column in CITY_SUMMARY_COLUMNS_V3:
        if column not in summary_frame.columns:
            summary_frame[column] = np.nan
    summary_frame = summary_frame[list(CITY_SUMMARY_COLUMNS_V3)].sort_values("city_slug").reset_index(drop=True)
    summary_frame.to_csv(summary_path, index=False)

    return {
        "csv_path": csv_path,
        "geojson_path": geojson_path,
        "summary_path": summary_path,
    }


def run_city_inference(
    place_name: str,
    model_path: str | Path | None = None,
    totals_csv: str | Path = DEFAULT_TOTALS_CSV,
    pipeline_config: FeaturePipelineConfig | None = None,
) -> CityInferenceResult:
    totals_lookup = load_city_totals(totals_csv)
    normalized_city_name, official_population = _lookup_official_population(place_name, totals_lookup)

    selected_model_path = Path(model_path) if model_path else get_preferred_model_path()
    loaded_model = load_model_artifact(selected_model_path)

    feature_artifacts = generate_city_features(place_name, config=pipeline_config)
    feature_frame = feature_artifacts.features.feature_frame.copy()

    feature_validation = validate_feature_output(feature_frame, dataset_name=place_name)
    if feature_validation.has_errors:
        raise FeatureGenerationError("\n".join(feature_validation.to_lines()))

    qa_city_summary, _, qa_flags_list = qa_city_frame(feature_frame, city_name=normalized_city_name)
    qa_flags = pd.DataFrame(qa_flags_list)
    if not qa_flags.empty:
        hard_errors = qa_flags.loc[qa_flags["severity"] == "error"]
        if not hard_errors.empty:
            raise FeatureGenerationError(
                "Generated features failed QA checks:\n"
                + hard_errors.to_string(index=False)
            )

    raw_prediction = _predict_raw_population(feature_frame, loaded_model)
    calibrated_prediction = calibrate_predictions_by_city(
        raw_prediction,
        groups=pd.Series(normalized_city_name, index=feature_frame.index),
        official_totals=pd.Series(float(official_population), index=feature_frame.index),
    )

    output_frame = _build_output_frame(
        feature_frame=feature_frame,
        raw_prediction=raw_prediction,
        calibrated_prediction=calibrated_prediction,
        place_name=place_name,
        model=loaded_model,
        official_population=official_population,
    )

    output_gdf = feature_artifacts.features.display_gdf[["geometry"]].copy()
    for column in output_frame.columns:
        output_gdf[column] = output_frame[column].to_numpy()

    output_validation = validate_city_output(output_frame, dataset_name=place_name)
    if output_validation.has_errors:
        raise FeatureGenerationError("\n".join(output_validation.to_lines()))

    raw_prediction_sum = float(raw_prediction.sum())
    calibration_factor = float(official_population / raw_prediction_sum) if raw_prediction_sum > 0 else 0.0
    osm_completeness = compute_osm_completeness(
        feature_frame,
        city_name=normalized_city_name,
        layers=feature_artifacts.layers.layers,
        osm_warnings=feature_artifacts.layers.warnings,
        qa_flags=qa_flags,
    )

    return CityInferenceResult(
        place_name=place_name,
        normalized_city_name=normalized_city_name,
        model=loaded_model,
        official_population=official_population,
        raw_prediction_sum=raw_prediction_sum,
        calibration_factor=calibration_factor,
        feature_artifacts=feature_artifacts,
        output_frame=output_frame,
        output_gdf=output_gdf,
        feature_validation_report=feature_validation,
        output_validation_report=output_validation,
        qa_city_summary=qa_city_summary,
        qa_flags=qa_flags,
        osm_completeness=osm_completeness,
    )


def run_city_uncertainty_inference(
    place_name: str,
    model_path: str | Path | None = None,
    totals_csv: str | Path = DEFAULT_TOTALS_CSV,
    pipeline_config: FeaturePipelineConfig | None = None,
    uncertainty_config: UncertaintyConfig | None = None,
) -> CityInferenceResult:
    totals_lookup = load_city_totals(totals_csv)
    normalized_city_name, official_population = _lookup_official_population(place_name, totals_lookup)

    selected_model_path = Path(model_path) if model_path else get_preferred_uncertainty_model_path()
    loaded_model = load_uncertainty_artifact(selected_model_path)
    config = uncertainty_config or loaded_model.uncertainty_config

    feature_artifacts = _load_or_generate_feature_artifacts(place_name, pipeline_config=pipeline_config)
    feature_frame = feature_artifacts.features.feature_frame.copy()

    feature_validation = validate_feature_output(feature_frame, dataset_name=place_name)
    if feature_validation.has_errors:
        raise FeatureGenerationError("\n".join(feature_validation.to_lines()))

    qa_city_summary, _, qa_flags_list = qa_city_frame(feature_frame, city_name=normalized_city_name)
    qa_flags = pd.DataFrame(qa_flags_list)
    if not qa_flags.empty:
        hard_errors = qa_flags.loc[qa_flags["severity"] == "error"]
        if not hard_errors.empty:
            raise FeatureGenerationError(
                "Generated features failed QA checks:\n" + hard_errors.to_string(index=False)
            )

    member_raw_predictions = predict_uncertainty_ensemble(feature_frame, loaded_model)
    member_calibrated_predictions = member_raw_predictions.copy()
    for column in member_calibrated_predictions.columns:
        member_calibrated_predictions[column] = calibrate_predictions_by_city(
            member_calibrated_predictions[column],
            groups=pd.Series(normalized_city_name, index=feature_frame.index),
            official_totals=pd.Series(float(official_population), index=feature_frame.index),
        ).to_numpy()

    summary = summarize_ensemble_predictions(
        member_calibrated_predictions,
        uncertainty_config=config,
    )
    summary = align_interval_summary_to_total(
        summary,
        official_total=float(official_population),
        uncertainty_config=config,
    )

    raw_prediction = member_raw_predictions.median(axis=1).astype(float)
    model_version = loaded_model.model_version or MODEL_VERSION_V3
    run_id = loaded_model.run_id or selected_model_path.parent.name

    osm_completeness = _load_frozen_osm_completeness(normalized_city_name)
    if osm_completeness is None:
        osm_completeness = compute_osm_completeness(
            feature_frame,
            city_name=normalized_city_name,
            layers=feature_artifacts.layers.layers,
            osm_warnings=feature_artifacts.layers.warnings,
            qa_flags=qa_flags,
        )

    support_context = _resolve_internal_support_context(normalized_city_name)
    external_agreement_score = 0.50
    osm_support_score = float(np.clip(float(osm_completeness.completeness_score) / 100.0, 0.0, 1.0))
    model_stability_score = compute_model_stability_score(summary["Population_Uncertainty_Relative"])
    confidence_score = compute_confidence_score(
        model_stability_score,
        osm_support_score=osm_support_score,
        external_agreement_score=external_agreement_score,
        internal_support_score=float(support_context["internal_support_score"]),
    )
    confidence_band = assign_confidence_bands_from_score(confidence_score)
    hotspot_rank, hotspot_priority_class, _ = _build_hotspot_priority_fields(
        summary["Population_Estimate_P50"],
        confidence_band,
    )

    city_display_name = _display_city_name(place_name)
    city_slug = _city_slug_from_normalized(normalized_city_name)
    output_frame = pd.DataFrame(
        {
            "run_id": run_id,
            "model_version": model_version,
            "city": city_display_name,
            "city_slug": city_slug,
            "cell_id": feature_frame["Zone_ID"].astype(str).to_numpy(),
            "centroid_latitude": pd.to_numeric(feature_frame["latitude"], errors="coerce").to_numpy(),
            "centroid_longitude": pd.to_numeric(feature_frame["longitude"], errors="coerce").to_numpy(),
            "official_city_total": int(official_population),
            "calibrated_member_count": int(member_calibrated_predictions.shape[1]),
            "p10": pd.to_numeric(summary["Population_Estimate_P10"], errors="coerce").to_numpy(),
            "p50": pd.to_numeric(summary["Population_Estimate_P50"], errors="coerce").to_numpy(),
            "p90": pd.to_numeric(summary["Population_Estimate_P90"], errors="coerce").to_numpy(),
            "population_estimate_final": pd.to_numeric(summary["Population_Estimate_P50"], errors="coerce").to_numpy(),
            "uncertainty_width": pd.to_numeric(summary["Population_Uncertainty_Width"], errors="coerce").to_numpy(),
            "relative_uncertainty": pd.to_numeric(summary["Population_Uncertainty_Relative"], errors="coerce").to_numpy(),
            "model_stability_score": model_stability_score.to_numpy(),
            "osm_completeness_score": float(osm_completeness.completeness_score),
            "osm_completeness_label": str(osm_completeness.completeness_label),
            "osm_support_score": osm_support_score,
            "external_agreement_score": external_agreement_score,
            "internal_support_score": float(support_context["internal_support_score"]),
            "confidence_score": confidence_score.to_numpy(),
            "confidence_band": confidence_band.astype(str).to_numpy(),
            "hotspot_rank": hotspot_rank.to_numpy(),
            "hotspot_priority_class": hotspot_priority_class.astype(str).to_numpy(),
            "district_support_flag": str(support_context["district_support_flag"]),
        }
    )
    output_frame = output_frame[list(CITY_OUTPUT_COLUMNS_V3)].copy()

    output_gdf = feature_artifacts.features.display_gdf[["geometry"]].copy()
    if len(output_gdf) != len(output_frame):
        raise FeatureGenerationError(
            "Feature geometry row count does not match the canonical v3 output row count."
        )
    for column in output_frame.columns:
        output_gdf[column] = output_frame[column].to_numpy()

    output_validation = validate_city_output_v3(output_frame, dataset_name=place_name)
    if output_validation.has_errors:
        raise FeatureGenerationError("\n".join(output_validation.to_lines()))

    raw_prediction_sum = float(raw_prediction.sum())
    calibration_factor = float(official_population / raw_prediction_sum) if raw_prediction_sum > 0 else 0.0
    interval_summary = {
        "median_population_p50": float(pd.to_numeric(output_frame["p50"], errors="coerce").median()),
        "median_uncertainty_width": float(pd.to_numeric(output_frame["uncertainty_width"], errors="coerce").median()),
        "median_uncertainty_relative": float(pd.to_numeric(output_frame["relative_uncertainty"], errors="coerce").median()),
        "mean_confidence_score": float(pd.to_numeric(output_frame["confidence_score"], errors="coerce").mean()),
    }

    return CityInferenceResult(
        place_name=place_name,
        normalized_city_name=normalized_city_name,
        model=loaded_model,
        official_population=official_population,
        raw_prediction_sum=raw_prediction_sum,
        calibration_factor=calibration_factor,
        feature_artifacts=feature_artifacts,
        output_frame=output_frame,
        output_gdf=output_gdf,
        feature_validation_report=feature_validation,
        output_validation_report=output_validation,
        qa_city_summary=qa_city_summary,
        qa_flags=qa_flags,
        osm_completeness=osm_completeness,
        member_predictions=member_calibrated_predictions,
        uncertainty_interval_summary=interval_summary,
    )
