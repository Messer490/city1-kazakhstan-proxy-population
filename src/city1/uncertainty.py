from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from .contracts import CITY_OUTPUT_COLUMNS_V3, MODEL_VERSION_V3
from .training import TrainingConfig, build_estimator


@dataclass(frozen=True)
class UncertaintyConfig:
    ensemble_size: int = 9
    quantiles: tuple[float, float, float] = (0.10, 0.50, 0.90)
    bootstrap_within_city: bool = True
    relative_epsilon: float = 1e-6
    confidence_labels: tuple[str, str, str] = ("high", "medium", "low")
    downgrade_completeness_labels: tuple[str, ...] = ("moderate", "weak")


@dataclass(frozen=True)
class EnsembleMemberArtifact:
    member_id: str
    random_state: int
    estimator: Any


@dataclass
class UncertaintyEnsembleTrainingResult:
    training_config: TrainingConfig
    uncertainty_config: UncertaintyConfig
    members: tuple[EnsembleMemberArtifact, ...]
    member_manifest: pd.DataFrame


@dataclass(frozen=True)
class LoadedUncertaintyArtifact:
    path: Path
    model_name: str
    model_version: str
    run_id: str | None
    feature_columns: tuple[str, ...]
    use_log_target: bool
    uncertainty_config: UncertaintyConfig
    members: tuple[EnsembleMemberArtifact, ...]
    member_manifest: pd.DataFrame


def resolve_ensemble_seeds(base_random_state: int, ensemble_size: int) -> tuple[int, ...]:
    if ensemble_size <= 0:
        raise ValueError("ensemble_size must be positive.")
    return tuple(int(base_random_state + 1009 * index) for index in range(ensemble_size))


def compute_model_stability_score(
    relative_uncertainty: pd.Series,
    *,
    epsilon: float = 1e-6,
) -> pd.Series:
    numeric = pd.to_numeric(relative_uncertainty, errors="coerce").fillna(float("inf"))
    q90 = float(numeric.quantile(0.90)) if not numeric.empty else 0.0
    denominator = max(q90, float(epsilon))
    clipped = np.clip(numeric / denominator, a_min=0.0, a_max=1.0)
    return pd.Series(1.0 - clipped, index=relative_uncertainty.index, dtype=float)


def compute_confidence_score(
    model_stability_score: pd.Series,
    *,
    osm_support_score: float,
    external_agreement_score: float,
    internal_support_score: float,
) -> pd.Series:
    stability = pd.to_numeric(model_stability_score, errors="coerce").fillna(0.0)
    score = (
        0.40 * stability
        + 0.25 * float(np.clip(osm_support_score, 0.0, 1.0))
        + 0.20 * float(np.clip(external_agreement_score, 0.0, 1.0))
        + 0.15 * float(np.clip(internal_support_score, 0.0, 1.0))
    )
    return pd.Series(np.clip(score, 0.0, 1.0), index=model_stability_score.index, dtype=float)


def assign_confidence_bands_from_score(confidence_score: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(confidence_score, errors="coerce").fillna(0.0)
    bands = pd.Series("medium", index=confidence_score.index, dtype="object")
    bands.loc[numeric >= 0.70] = "high"
    bands.loc[numeric < 0.40] = "low"
    return bands


def bootstrap_training_frame(
    frame: pd.DataFrame,
    *,
    random_state: int,
    group_column: str,
    within_group: bool = True,
) -> pd.DataFrame:
    if frame.empty:
        raise ValueError("Cannot bootstrap an empty training frame.")
    if group_column not in frame.columns:
        raise ValueError(f"Missing bootstrap grouping column: {group_column}")

    if not within_group:
        return frame.sample(
            n=len(frame),
            replace=True,
            random_state=random_state,
        ).reset_index(drop=True)

    rng = np.random.default_rng(int(random_state))
    bootstrapped_groups: list[pd.DataFrame] = []

    for _, group_frame in frame.groupby(group_column, sort=True):
        sample_seed = int(rng.integers(0, np.iinfo(np.int32).max))
        sampled = group_frame.sample(
            n=len(group_frame),
            replace=True,
            random_state=sample_seed,
        )
        bootstrapped_groups.append(sampled.reset_index(drop=True))

    return pd.concat(bootstrapped_groups, ignore_index=True)


def _transform_target(y: pd.Series, use_log_target: bool) -> pd.Series:
    if not use_log_target:
        return y.astype(float)
    return np.log1p(y.astype(float).clip(lower=0.0))


def _inverse_transform_predictions(values: np.ndarray, use_log_target: bool) -> np.ndarray:
    if not use_log_target:
        return values
    return np.expm1(values)


def train_uncertainty_ensemble(
    frame: pd.DataFrame,
    *,
    training_config: TrainingConfig,
    uncertainty_config: UncertaintyConfig | None = None,
) -> UncertaintyEnsembleTrainingResult:
    config = uncertainty_config or UncertaintyConfig()
    seeds = resolve_ensemble_seeds(training_config.random_state, config.ensemble_size)
    members: list[EnsembleMemberArtifact] = []
    manifest_rows: list[dict[str, object]] = []

    for member_index, seed in enumerate(seeds, start=1):
        bootstrap_frame = bootstrap_training_frame(
            frame,
            random_state=seed,
            group_column=training_config.group_column,
            within_group=config.bootstrap_within_city,
        )
        member_config = replace(training_config, random_state=seed)
        estimator = build_estimator(
            member_config.model_name,
            member_config.random_state,
            rf_n_estimators=member_config.rf_n_estimators,
            rf_min_samples_leaf=member_config.rf_min_samples_leaf,
            rf_n_jobs=member_config.rf_n_jobs,
        )
        estimator.fit(
            bootstrap_frame[list(member_config.feature_columns)],
            _transform_target(
                bootstrap_frame[member_config.target_column].astype(float),
                member_config.use_log_target,
            ),
        )
        member_id = f"member_{member_index:02d}"
        members.append(
            EnsembleMemberArtifact(
                member_id=member_id,
                random_state=int(seed),
                estimator=estimator,
            )
        )
        manifest_rows.append(
            {
                "member_id": member_id,
                "random_state": int(seed),
                "row_count": int(len(bootstrap_frame)),
                "city_count": int(bootstrap_frame[training_config.group_column].nunique()),
                "bootstrap_within_city": bool(config.bootstrap_within_city),
            }
        )

    return UncertaintyEnsembleTrainingResult(
        training_config=training_config,
        uncertainty_config=config,
        members=tuple(members),
        member_manifest=pd.DataFrame(manifest_rows),
    )


def save_uncertainty_training_run(
    result: UncertaintyEnsembleTrainingResult,
    output_dir: str | Path,
    *,
    run_id: str | None = None,
    model_version: str = MODEL_VERSION_V3,
    grid_cell_size_meters: int = 500,
    official_totals_reference: str | None = None,
    city_registry_reference: str | None = None,
    feature_schema: dict[str, object] | None = None,
    training_summary: dict[str, object] | None = None,
    city_registry_snapshot: pd.DataFrame | None = None,
    run_manifest: dict[str, object] | None = None,
) -> dict[str, Path]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    resolved_run_id = run_id or output_path.name
    artifact_path = output_path / "ensemble_model.joblib"
    config_path = output_path / "ensemble_config.json"
    summary_path = output_path / "training_summary.csv"
    feature_schema_path = output_path / "feature_schema.json"
    registry_snapshot_path = output_path / "city_registry_snapshot.csv"
    run_manifest_path = output_path / "run_manifest.json"
    member_manifest_path = output_path / "member_manifest.csv"

    uncertainty_model_name = f"{result.training_config.model_name}_uncertainty"
    artifact = {
        "artifact_kind": "city1_v3_uncertainty_ensemble",
        "model_name": uncertainty_model_name,
        "model_version": model_version,
        "run_id": resolved_run_id,
        "feature_columns": list(result.training_config.feature_columns),
        "target_column": result.training_config.target_column,
        "official_total_column": result.training_config.official_total_column,
        "group_column": result.training_config.group_column,
        "use_log_target": result.training_config.use_log_target,
        "training_config": asdict(result.training_config),
        "uncertainty_config": asdict(result.uncertainty_config),
        "members": [
            {
                "member_id": member.member_id,
                "random_state": member.random_state,
                "estimator": member.estimator,
            }
            for member in result.members
        ],
        "member_manifest": result.member_manifest.to_dict(orient="records"),
    }
    ensemble_config = {
        "run_id": resolved_run_id,
        "model_version": model_version,
        "model_name": uncertainty_model_name,
        "grid_cell_size_meters": int(grid_cell_size_meters),
        "ensemble_size": int(len(result.members)),
        "base_random_state": int(result.training_config.random_state),
        "bootstrap_within_city": bool(result.uncertainty_config.bootstrap_within_city),
        "quantiles": list(result.uncertainty_config.quantiles),
        "use_log_target": bool(result.training_config.use_log_target),
        "relative_epsilon": float(result.uncertainty_config.relative_epsilon),
        "feature_columns": list(result.training_config.feature_columns),
        "official_totals_reference": official_totals_reference or "",
        "city_registry_reference": city_registry_reference or "",
    }
    resolved_training_summary = training_summary or {
        "run_id": resolved_run_id,
        "model_version": model_version,
        "ensemble_size": int(len(result.members)),
        "training_city_count": int(result.member_manifest["city_count"].max()) if not result.member_manifest.empty else 0,
        "training_row_count": int(result.member_manifest["row_count"].max()) if not result.member_manifest.empty else 0,
        "included_cities": "",
        "skipped_file_count": 0,
        "warning_count": 0,
    }
    resolved_feature_schema = feature_schema or {
        "feature_columns": list(result.training_config.feature_columns),
        "cell_id_source_field": "Zone_ID",
        "canonical_output_fields": list(CITY_OUTPUT_COLUMNS_V3),
    }
    registry_snapshot = city_registry_snapshot if city_registry_snapshot is not None else pd.DataFrame()
    resolved_run_manifest = dict(run_manifest or {})
    generated_files = [
        artifact_path.name,
        config_path.name,
        summary_path.name,
        feature_schema_path.name,
        registry_snapshot_path.name,
        run_manifest_path.name,
        member_manifest_path.name,
    ]
    resolved_run_manifest.setdefault("run_id", resolved_run_id)
    resolved_run_manifest.setdefault("model_version", model_version)
    resolved_run_manifest.setdefault("model_name", uncertainty_model_name)
    resolved_run_manifest.setdefault("generated_files", generated_files)

    joblib.dump(artifact, artifact_path)
    config_path.write_text(json.dumps(ensemble_config, indent=2), encoding="utf-8")
    pd.DataFrame([resolved_training_summary]).to_csv(summary_path, index=False)
    feature_schema_path.write_text(json.dumps(resolved_feature_schema, indent=2), encoding="utf-8")
    registry_snapshot.to_csv(registry_snapshot_path, index=False)
    result.member_manifest.to_csv(member_manifest_path, index=False)
    run_manifest_path.write_text(json.dumps(resolved_run_manifest, indent=2, default=str), encoding="utf-8")
    return {
        "artifact_path": artifact_path,
        "ensemble_config_path": config_path,
        "training_summary_path": summary_path,
        "feature_schema_path": feature_schema_path,
        "city_registry_snapshot_path": registry_snapshot_path,
        "run_manifest_path": run_manifest_path,
        "member_manifest_path": member_manifest_path,
    }


def load_uncertainty_artifact(path: str | Path) -> LoadedUncertaintyArtifact:
    artifact_path = Path(path)
    payload = joblib.load(artifact_path)
    if not isinstance(payload, dict):
        raise ValueError(f"Unexpected uncertainty artifact structure in {artifact_path}")

    required_keys = {
        "artifact_kind",
        "model_name",
        "feature_columns",
        "use_log_target",
        "uncertainty_config",
        "members",
        "member_manifest",
    }
    missing_keys = required_keys.difference(payload.keys())
    if missing_keys:
        raise ValueError(
            f"Uncertainty artifact {artifact_path} is missing keys: {sorted(missing_keys)}"
        )

    config_payload = dict(payload["uncertainty_config"])
    members = tuple(
        EnsembleMemberArtifact(
            member_id=str(member_payload["member_id"]),
            random_state=int(member_payload["random_state"]),
            estimator=member_payload["estimator"],
        )
        for member_payload in payload["members"]
    )
    return LoadedUncertaintyArtifact(
        path=artifact_path,
        model_name=str(payload["model_name"]),
        model_version=str(payload.get("model_version", MODEL_VERSION_V3)),
        run_id=str(payload["run_id"]) if payload.get("run_id") else None,
        feature_columns=tuple(payload["feature_columns"]),
        use_log_target=bool(payload["use_log_target"]),
        uncertainty_config=UncertaintyConfig(**config_payload),
        members=members,
        member_manifest=pd.DataFrame(payload["member_manifest"]),
    )


def predict_uncertainty_ensemble(
    feature_frame: pd.DataFrame,
    artifact: LoadedUncertaintyArtifact,
) -> pd.DataFrame:
    missing_columns = [column for column in artifact.feature_columns if column not in feature_frame.columns]
    if missing_columns:
        raise ValueError(
            f"Generated feature frame is missing uncertainty model columns: {', '.join(missing_columns)}"
        )

    features = feature_frame[list(artifact.feature_columns)].copy()
    features = features.apply(pd.to_numeric, errors="coerce").fillna(0.0)
    prediction_columns: dict[str, np.ndarray] = {}

    for member in artifact.members:
        raw_pred = member.estimator.predict(features)
        raw_pred = _inverse_transform_predictions(np.asarray(raw_pred, dtype=float), artifact.use_log_target)
        prediction_columns[member.member_id] = np.clip(raw_pred, a_min=0.0, a_max=None)

    return pd.DataFrame(prediction_columns, index=feature_frame.index)


def summarize_ensemble_predictions(
    member_predictions: pd.DataFrame,
    *,
    uncertainty_config: UncertaintyConfig | None = None,
) -> pd.DataFrame:
    config = uncertainty_config or UncertaintyConfig()
    if member_predictions.empty:
        raise ValueError("Cannot summarize an empty prediction ensemble.")

    q10, q50, q90 = config.quantiles
    matrix = member_predictions.to_numpy(dtype=float)
    p10 = np.quantile(matrix, q10, axis=1)
    p50 = np.quantile(matrix, q50, axis=1)
    p90 = np.quantile(matrix, q90, axis=1)
    width = p90 - p10
    relative = width / np.maximum(p50, float(config.relative_epsilon))

    return pd.DataFrame(
        {
            "Population_Estimate_P10": p10,
            "Population_Estimate_P50": p50,
            "Population_Estimate_P90": p90,
            "Population_Uncertainty_Width": width,
            "Population_Uncertainty_Relative": relative,
            "Population_Estimate_Final": p50,
        },
        index=member_predictions.index,
    )


def align_interval_summary_to_total(
    summary_frame: pd.DataFrame,
    *,
    official_total: float,
    uncertainty_config: UncertaintyConfig | None = None,
) -> pd.DataFrame:
    config = uncertainty_config or UncertaintyConfig()
    aligned = summary_frame.copy()
    current_total = float(pd.to_numeric(aligned["Population_Estimate_P50"], errors="coerce").fillna(0.0).sum())
    if official_total <= 0 or current_total <= 0:
        return aligned

    factor = float(official_total / current_total)
    scalable_columns = [
        "Population_Estimate_P10",
        "Population_Estimate_P50",
        "Population_Estimate_P90",
        "Population_Uncertainty_Width",
        "Population_Estimate_Final",
    ]
    for column in scalable_columns:
        aligned[column] = pd.to_numeric(aligned[column], errors="coerce").fillna(0.0) * factor

    relative = (
        pd.to_numeric(aligned["Population_Uncertainty_Width"], errors="coerce").fillna(0.0)
        / np.maximum(
            pd.to_numeric(aligned["Population_Estimate_P50"], errors="coerce").fillna(0.0),
            float(config.relative_epsilon),
        )
    )
    aligned["Population_Uncertainty_Relative"] = relative
    aligned["Population_Estimate_Final"] = aligned["Population_Estimate_P50"]
    return aligned


def assign_confidence_bands(
    relative_uncertainty: pd.Series,
    *,
    completeness_label: str | None = None,
    uncertainty_config: UncertaintyConfig | None = None,
) -> pd.Series:
    config = uncertainty_config or UncertaintyConfig()
    numeric = pd.to_numeric(relative_uncertainty, errors="coerce").fillna(float("inf"))
    rank_pct = numeric.rank(method="average", pct=True)
    high_label, medium_label, low_label = config.confidence_labels

    bands = pd.Series(medium_label, index=relative_uncertainty.index, dtype="object")
    bands.loc[rank_pct <= (1.0 / 3.0)] = high_label
    bands.loc[rank_pct > (2.0 / 3.0)] = low_label

    normalized_label = str(completeness_label or "").strip().lower()
    if normalized_label in set(config.downgrade_completeness_labels):
        downgrade_map = {
            high_label: medium_label,
            medium_label: low_label,
            low_label: low_label,
        }
        bands = bands.map(lambda value: downgrade_map.get(str(value), low_label))

    return bands
