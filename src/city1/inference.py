from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import joblib
import numpy as np
import pandas as pd

from .city_totals import CityTotalsLookup, load_city_totals, normalize_city_name
from .config import FeaturePipelineConfig
from .feature_qa import qa_city_frame
from .osm_completeness import OSMCompletenessResult, compute_osm_completeness
from .paths import EXTERNAL_DATA_DIR, MODELS_DIR
from .pipeline import FeaturePipelineArtifacts, generate_city_features
from .training import calibrate_predictions_by_city
from .validation import DatasetValidationReport, validate_city_output, validate_feature_output

if TYPE_CHECKING:
    import geopandas as gpd


DEFAULT_TOTALS_CSV = EXTERNAL_DATA_DIR / "city_population_reference_v2.csv"


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
    model: LoadedModelArtifact
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


def slugify_place_name(place_name: str) -> str:
    cleaned = normalize_city_name(place_name.replace(",", " "))
    return cleaned.replace(" ", "_") or "city"


def _display_city_name(place_name: str) -> str:
    return place_name.split(",")[0].strip()


def list_available_models(models_dir: str | Path = MODELS_DIR) -> list[AvailableModel]:
    candidates = sorted(Path(models_dir).rglob("*_model_v2.joblib"))
    models: list[AvailableModel] = []

    for path in candidates:
        model_name = path.name.replace("_model_v2.joblib", "")
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
