from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupKFold, LeaveOneGroupOut
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .city_totals import CityTotalsLookup, city_name_from_filename, normalize_city_name
from .contracts import MODEL_FEATURE_COLUMNS
from .labeling import WeakLabelConfig, allocate_city_total_to_cells
from .validation import validate_feature_output


@dataclass(frozen=True)
class TrainingConfig:
    model_name: str = "ridge"
    feature_columns: tuple[str, ...] = MODEL_FEATURE_COLUMNS
    target_column: str = "Weak_Population_Target"
    official_total_column: str = "Official_City_Population"
    group_column: str = "city_name"
    latitude_column: str = "latitude"
    longitude_column: str = "longitude"
    validation_protocol: str = "leave_one_city_out"
    spatial_block_size_meters: int = 2000
    spatial_block_splits: int = 5
    random_state: int = 42
    rf_n_estimators: int = 400
    rf_min_samples_leaf: int = 2
    rf_n_jobs: int = 1
    use_log_target: bool = True
    min_cities: int = 3


@dataclass
class TrainingDatasetBundle:
    frame: pd.DataFrame
    included_cities: tuple[str, ...]
    skipped_files: tuple[str, ...]
    warnings: tuple[str, ...]


@dataclass
class TrainingRunResult:
    config: TrainingConfig
    label_config: WeakLabelConfig
    final_estimator: Any
    training_frame: pd.DataFrame
    oof_predictions: pd.DataFrame
    fold_metrics: pd.DataFrame


def discover_feature_files(features_dir: str | Path) -> list[Path]:
    return sorted(Path(features_dir).glob("*.csv"))


def sanitize_feature_frame_for_training(
    frame: pd.DataFrame,
    required_feature_columns: tuple[str, ...],
) -> pd.DataFrame:
    cleaned = frame.copy()
    cleaned = cleaned.dropna(how="all")

    coordinate_columns = [column for column in ("latitude", "longitude") if column in cleaned.columns]
    if coordinate_columns:
        cleaned = cleaned.dropna(subset=coordinate_columns)

    for column in required_feature_columns:
        if column in cleaned.columns:
            cleaned[column] = pd.to_numeric(cleaned[column], errors="coerce").fillna(0.0)
            cleaned[column] = cleaned[column].clip(lower=0.0)

    return cleaned.reset_index(drop=True)


def build_training_dataset(
    features_dir: str | Path,
    totals_lookup: CityTotalsLookup,
    label_config: WeakLabelConfig | None = None,
    required_feature_columns: tuple[str, ...] = MODEL_FEATURE_COLUMNS,
    allowed_cities: set[str] | None = None,
) -> TrainingDatasetBundle:
    weak_label_config = label_config or WeakLabelConfig()
    files = discover_feature_files(features_dir)
    if not files:
        raise ValueError(f"No feature CSV files found in {features_dir}")

    frames: list[pd.DataFrame] = []
    warnings: list[str] = []
    skipped_files: list[str] = []
    included_cities: list[str] = []
    allowed_city_set = (
        {normalize_city_name(city_name) for city_name in allowed_cities}
        if allowed_cities
        else None
    )

    for path in files:
        city_name = city_name_from_filename(path)
        if allowed_city_set is not None and city_name not in allowed_city_set:
            warnings.append(f"Skipped {path.name}: city is outside the requested training subset.")
            skipped_files.append(path.name)
            continue
        official_population = totals_lookup.get_population(city_name)
        if official_population is None:
            warnings.append(f"Skipped {path.name}: no official population total found for city '{city_name}'.")
            skipped_files.append(path.name)
            continue

        frame = sanitize_feature_frame_for_training(
            pd.read_csv(path),
            required_feature_columns=tuple(required_feature_columns),
        )
        required_columns = ("latitude", "longitude") + tuple(required_feature_columns)
        report = validate_feature_output(
            frame,
            dataset_name=path.name,
            required_columns=required_columns,
        )
        if report.has_errors:
            warnings.append(f"Skipped {path.name}: feature validation failed.")
            skipped_files.append(path.name)
            continue

        labeled = allocate_city_total_to_cells(
            frame,
            official_population=official_population,
            config=weak_label_config,
        )
        labeled["city_name"] = city_name
        labeled["source_file"] = path.name
        frames.append(labeled)
        included_cities.append(city_name)

    if not frames:
        raise ValueError("No valid city datasets were available for training.")

    combined = pd.concat(frames, ignore_index=True)
    unique_cities = tuple(sorted(set(included_cities)))

    return TrainingDatasetBundle(
        frame=combined,
        included_cities=unique_cities,
        skipped_files=tuple(skipped_files),
        warnings=tuple(warnings),
    )


def build_estimator(
    model_name: str,
    random_state: int,
    *,
    rf_n_estimators: int = 400,
    rf_min_samples_leaf: int = 2,
    rf_n_jobs: int = 1,
) -> Pipeline:
    normalized_name = model_name.strip().lower()

    if normalized_name == "ridge":
        return Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                ("model", Ridge(alpha=1.0)),
            ]
        )

    if normalized_name in {"randomforest", "random_forest", "rf"}:
        return Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="median")),
                (
                    "model",
                    RandomForestRegressor(
                        n_estimators=rf_n_estimators,
                        min_samples_leaf=rf_min_samples_leaf,
                        random_state=random_state,
                        n_jobs=rf_n_jobs,
                    ),
                ),
            ]
        )

    if normalized_name == "catboost":
        try:
            from catboost import CatBoostRegressor
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise ImportError(
                "CatBoost is not installed. Add 'catboost' to the environment to use this model."
            ) from exc

        return Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="median")),
                ("model", CatBoostRegressor(verbose=0, random_state=random_state)),
            ]
        )

    raise ValueError(f"Unsupported model name: {model_name}")


def validation_protocol_slug(validation_protocol: str) -> str:
    return validation_protocol.strip().lower().replace("-", "_").replace(" ", "_")


def build_spatial_block_groups(
    frame: pd.DataFrame,
    *,
    city_column: str,
    latitude_column: str,
    longitude_column: str,
    block_size_meters: int,
) -> pd.Series:
    if city_column not in frame.columns:
        raise ValueError(f"Missing city grouping column for spatial blocks: {city_column}")
    if latitude_column not in frame.columns or longitude_column not in frame.columns:
        raise ValueError(
            f"Spatial block CV requires coordinate columns {latitude_column!r} and {longitude_column!r}."
        )
    if block_size_meters <= 0:
        raise ValueError(f"spatial block size must be positive, got {block_size_meters}")

    labels = pd.Series(index=frame.index, dtype="object")
    meters_per_degree_lat = 111_320.0

    for city_name, city_index in frame.groupby(city_column).groups.items():
        city_rows = frame.loc[city_index]
        lat = pd.to_numeric(city_rows[latitude_column], errors="coerce").astype(float)
        lon = pd.to_numeric(city_rows[longitude_column], errors="coerce").astype(float)
        if lat.isna().any() or lon.isna().any():
            raise ValueError(f"Spatial block CV found missing coordinates inside city {city_name!r}.")

        lat_origin = float(lat.min())
        lon_origin = float(lon.min())
        mean_lat_radians = float(np.deg2rad(lat.mean()))
        meters_per_degree_lon = max(111_320.0 * np.cos(mean_lat_radians), 1e-6)

        x_meters = (lon - lon_origin) * meters_per_degree_lon
        y_meters = (lat - lat_origin) * meters_per_degree_lat
        block_x = np.floor(x_meters / float(block_size_meters)).astype(int)
        block_y = np.floor(y_meters / float(block_size_meters)).astype(int)
        city_slug = normalize_city_name(str(city_name))

        city_labels = pd.Series(
            [f"{city_slug}__bx{int(x)}_by{int(y)}" for x, y in zip(block_x, block_y)],
            index=city_rows.index,
            dtype="object",
        )
        labels.loc[city_rows.index] = city_labels

    return labels


def _transform_target(y: pd.Series, use_log_target: bool) -> pd.Series:
    if not use_log_target:
        return y
    return np.log1p(y.clip(lower=0.0))


def _inverse_transform_target(values: np.ndarray, use_log_target: bool) -> np.ndarray:
    if not use_log_target:
        return values
    return np.expm1(values)


def calibrate_predictions_by_group(
    predictions: pd.Series | np.ndarray,
    groups: pd.Series,
    target_totals: pd.Series,
) -> pd.Series:
    pred = np.asarray(predictions, dtype=float).clip(min=0.0)
    calibrated = np.zeros_like(pred)
    group_series = groups.reset_index(drop=True)
    total_series = target_totals.reset_index(drop=True)

    for group_name in group_series.unique():
        group_mask = group_series == group_name
        group_indices = np.flatnonzero(group_mask.to_numpy())
        group_total = float(total_series.loc[group_mask].iloc[0])
        group_pred = pred[group_indices]
        group_sum = float(group_pred.sum())

        if group_sum <= 0:
            calibrated[group_indices] = group_total / len(group_indices)
        else:
            calibrated[group_indices] = group_pred / group_sum * group_total

    return pd.Series(calibrated, index=groups.index)


def calibrate_predictions_by_city(
    predictions: pd.Series | np.ndarray,
    groups: pd.Series,
    official_totals: pd.Series,
) -> pd.Series:
    return calibrate_predictions_by_group(predictions, groups, official_totals)


def _regression_metrics(y_true: pd.Series, y_pred: pd.Series | np.ndarray) -> dict[str, float]:
    true = np.asarray(y_true, dtype=float)
    pred = np.asarray(y_pred, dtype=float)
    return {
        "mae": float(mean_absolute_error(true, pred)),
        "rmse": float(np.sqrt(mean_squared_error(true, pred))),
        "r2": float(r2_score(true, pred)) if len(true) > 1 else float("nan"),
    }


def _validation_setup(
    frame: pd.DataFrame,
    config: TrainingConfig,
) -> tuple[object, pd.Series, pd.Series, str]:
    protocol = validation_protocol_slug(config.validation_protocol)
    if protocol in {"leave_one_city_out", "leave_one_group_out", "loco"}:
        groups = frame[config.group_column].astype(str)
        return LeaveOneGroupOut(), groups, groups, "city"

    if protocol in {"spatial_block", "spatial_block_cv"}:
        block_groups = build_spatial_block_groups(
            frame,
            city_column=config.group_column,
            latitude_column=config.latitude_column,
            longitude_column=config.longitude_column,
            block_size_meters=config.spatial_block_size_meters,
        )
        unique_groups = int(block_groups.nunique())
        if unique_groups < 2:
            raise ValueError("Spatial block CV requires at least two unique spatial blocks.")
        n_splits = min(max(2, int(config.spatial_block_splits)), unique_groups)
        return GroupKFold(n_splits=n_splits), block_groups, block_groups, "spatial_block"

    raise ValueError(f"Unsupported validation protocol: {config.validation_protocol}")


def cross_validate_by_city(
    frame: pd.DataFrame,
    config: TrainingConfig,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    city_groups = frame[config.group_column]
    unique_cities = city_groups.nunique()
    if unique_cities < config.min_cities:
        raise ValueError(
            f"Need at least {config.min_cities} cities for training; got {unique_cities}."
        )

    features = frame[list(config.feature_columns)].copy()
    target = frame[config.target_column].astype(float)
    official_totals = frame[config.official_total_column].astype(float)
    splitter, split_groups, calibration_groups, calibration_unit = _validation_setup(frame, config)
    protocol = validation_protocol_slug(config.validation_protocol)

    fold_metrics: list[dict[str, Any]] = []
    oof_frames: list[pd.DataFrame] = []

    for fold_index, (train_idx, valid_idx) in enumerate(splitter.split(features, target, split_groups), start=1):
        estimator = build_estimator(
            config.model_name,
            config.random_state,
            rf_n_estimators=config.rf_n_estimators,
            rf_min_samples_leaf=config.rf_min_samples_leaf,
            rf_n_jobs=config.rf_n_jobs,
        )
        estimator.fit(
            features.iloc[train_idx],
            _transform_target(target.iloc[train_idx], config.use_log_target),
        )

        raw_pred = _inverse_transform_target(
            estimator.predict(features.iloc[valid_idx]),
            config.use_log_target,
        )
        raw_pred = np.clip(raw_pred, a_min=0.0, a_max=None)

        valid_city_groups = city_groups.iloc[valid_idx].reset_index(drop=True)
        valid_calibration_groups = calibration_groups.iloc[valid_idx].reset_index(drop=True)
        y_true = target.iloc[valid_idx].reset_index(drop=True)
        if calibration_unit == "city":
            valid_totals = official_totals.iloc[valid_idx].reset_index(drop=True)
        else:
            valid_totals = y_true.groupby(valid_calibration_groups).transform("sum")
        calibrated_pred = calibrate_predictions_by_group(raw_pred, valid_calibration_groups, valid_totals)

        raw_metrics = _regression_metrics(y_true, raw_pred)
        calibrated_metrics = _regression_metrics(y_true, calibrated_pred)

        city_names = tuple(sorted(valid_city_groups.unique()))
        fold_metrics.append(
            {
                "fold": fold_index,
                "validation_protocol": protocol,
                "calibration_unit": calibration_unit,
                "cities": ", ".join(city_names),
                "validation_group_count": int(pd.Series(valid_calibration_groups).nunique()),
                "rows": int(len(valid_idx)),
                "raw_mae": raw_metrics["mae"],
                "raw_rmse": raw_metrics["rmse"],
                "raw_r2": raw_metrics["r2"],
                "calibrated_mae": calibrated_metrics["mae"],
                "calibrated_rmse": calibrated_metrics["rmse"],
                "calibrated_r2": calibrated_metrics["r2"],
            }
        )

        fold_frame = frame.iloc[valid_idx][["city_name", "source_file", config.target_column]].copy()
        fold_frame["validation_protocol"] = protocol
        fold_frame["validation_group"] = valid_calibration_groups.to_numpy()
        fold_frame["prediction_raw"] = raw_pred
        fold_frame["prediction_calibrated"] = calibrated_pred.to_numpy()
        oof_frames.append(fold_frame)

    return pd.DataFrame(fold_metrics), pd.concat(oof_frames, ignore_index=True)


def train_final_model(
    frame: pd.DataFrame,
    config: TrainingConfig,
) -> Any:
    estimator = build_estimator(
        config.model_name,
        config.random_state,
        rf_n_estimators=config.rf_n_estimators,
        rf_min_samples_leaf=config.rf_min_samples_leaf,
        rf_n_jobs=config.rf_n_jobs,
    )
    estimator.fit(
        frame[list(config.feature_columns)],
        _transform_target(frame[config.target_column].astype(float), config.use_log_target),
    )
    return estimator


def run_training(
    features_dir: str | Path,
    totals_lookup: CityTotalsLookup,
    label_config: WeakLabelConfig | None = None,
    training_config: TrainingConfig | None = None,
) -> TrainingRunResult:
    weak_label_config = label_config or WeakLabelConfig()
    config = training_config or TrainingConfig()

    dataset = build_training_dataset(
        features_dir=features_dir,
        totals_lookup=totals_lookup,
        label_config=weak_label_config,
        required_feature_columns=config.feature_columns,
    )
    fold_metrics, oof_predictions = cross_validate_by_city(dataset.frame, config=config)
    final_estimator = train_final_model(dataset.frame, config=config)

    return TrainingRunResult(
        config=config,
        label_config=weak_label_config,
        final_estimator=final_estimator,
        training_frame=dataset.frame,
        oof_predictions=oof_predictions,
        fold_metrics=fold_metrics,
    )


def save_training_run(
    result: TrainingRunResult,
    output_dir: str | Path,
) -> dict[str, Path]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    protocol_slug = validation_protocol_slug(result.config.validation_protocol)
    artifact_path = output_path / f"{result.config.model_name}_model_v2.joblib"
    metrics_path = output_path / f"{result.config.model_name}__{protocol_slug}_fold_metrics.csv"
    oof_path = output_path / f"{result.config.model_name}__{protocol_slug}_oof_predictions.csv"
    metadata_path = output_path / f"{result.config.model_name}__{protocol_slug}_metadata.joblib"

    artifact = {
        "model_name": result.config.model_name,
        "estimator": result.final_estimator,
        "feature_columns": list(result.config.feature_columns),
        "target_column": result.config.target_column,
        "official_total_column": result.config.official_total_column,
        "group_column": result.config.group_column,
        "use_log_target": result.config.use_log_target,
    }

    metadata = {
        "training_config": asdict(result.config),
        "label_config": asdict(result.label_config),
        "fold_metrics": result.fold_metrics.to_dict(orient="records"),
    }

    joblib.dump(artifact, artifact_path)
    joblib.dump(metadata, metadata_path)
    result.fold_metrics.to_csv(metrics_path, index=False)
    result.oof_predictions.to_csv(oof_path, index=False)

    return {
        "artifact_path": artifact_path,
        "metadata_path": metadata_path,
        "metrics_path": metrics_path,
        "oof_path": oof_path,
    }
