from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .district_benchmark import aggregate_predictions_to_districts
from .external_benchmark import ExternalBenchmarkConfig, build_city_external_benchmark_alignment
from .training import TrainingConfig, _validation_setup, calibrate_predictions_by_group
from .uncertainty import (
    LoadedUncertaintyArtifact,
    UncertaintyConfig,
    align_interval_summary_to_total,
    assign_confidence_bands,
    predict_uncertainty_ensemble,
    summarize_ensemble_predictions,
    train_uncertainty_ensemble,
)


@dataclass(frozen=True)
class ErrorUncertaintyFoldMetrics:
    fold: int
    validation_protocol: str
    rows: int
    error_uncertainty_pearson: float
    error_uncertainty_spearman: float
    low_band_mean_abs_error: float
    high_band_mean_abs_error: float

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class DistrictIntervalCoverageMetrics:
    city_name: str
    district_count_total: int
    district_count_compared: int
    coverage_rate: float
    median_interval_width: float
    median_relative_interval_width: float
    p50_rmse: float
    p50_pearson_r: float
    p50_spearman_r: float

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ExternalDisagreementAlignmentMetrics:
    city_name: str
    city_slug: str
    benchmark_name: str
    row_count: int
    disagreement_uncertainty_pearson: float
    disagreement_uncertainty_spearman: float
    high_uncertainty_mean_disagreement: float
    low_uncertainty_mean_disagreement: float

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _safe_corr(series_a: pd.Series, series_b: pd.Series, method: str) -> float:
    frame = pd.DataFrame({"a": pd.to_numeric(series_a, errors="coerce"), "b": pd.to_numeric(series_b, errors="coerce")})
    frame = frame.replace([np.inf, -np.inf], np.nan).dropna()
    if len(frame) < 2:
        return float("nan")
    if frame["a"].nunique() <= 1 or frame["b"].nunique() <= 1:
        return float("nan")
    value = frame["a"].corr(frame["b"], method=method)
    return float(value) if pd.notna(value) else float("nan")


def _load_temporary_artifact(
    result,
    training_config: TrainingConfig,
    uncertainty_config: UncertaintyConfig,
) -> LoadedUncertaintyArtifact:
    return LoadedUncertaintyArtifact(
        path=Path("."),
        model_name=f"{training_config.model_name}_uncertainty",
        model_version="city1_v3_rf500m_uncertainty",
        run_id=None,
        feature_columns=tuple(training_config.feature_columns),
        use_log_target=bool(training_config.use_log_target),
        uncertainty_config=uncertainty_config,
        members=result.members,
        member_manifest=result.member_manifest,
    )


def cross_validate_uncertainty_by_city(
    frame: pd.DataFrame,
    *,
    training_config: TrainingConfig,
    uncertainty_config: UncertaintyConfig | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    config = uncertainty_config or UncertaintyConfig()
    features = frame[list(training_config.feature_columns)].copy()
    target = frame[training_config.target_column].astype(float)
    official_totals = frame[training_config.official_total_column].astype(float)
    splitter, split_groups, calibration_groups, calibration_unit = _validation_setup(frame, training_config)

    diagnostics_rows: list[pd.DataFrame] = []
    fold_rows: list[dict[str, Any]] = []

    for fold_index, (train_idx, valid_idx) in enumerate(splitter.split(features, target, split_groups), start=1):
        train_frame = frame.iloc[train_idx].reset_index(drop=True)
        valid_frame = frame.iloc[valid_idx].reset_index(drop=True)
        result = train_uncertainty_ensemble(
            train_frame,
            training_config=training_config,
            uncertainty_config=config,
        )
        artifact = _load_temporary_artifact(result, training_config, config)
        member_raw = predict_uncertainty_ensemble(valid_frame, artifact)

        valid_calibration_groups = calibration_groups.iloc[valid_idx].reset_index(drop=True)
        y_true = target.iloc[valid_idx].reset_index(drop=True)
        if calibration_unit == "city":
            valid_totals = official_totals.iloc[valid_idx].reset_index(drop=True)
        else:
            valid_totals = y_true.groupby(valid_calibration_groups).transform("sum")

        member_calibrated = member_raw.copy()
        for column in member_calibrated.columns:
            member_calibrated[column] = calibrate_predictions_by_group(
                member_calibrated[column],
                valid_calibration_groups,
                valid_totals,
            ).to_numpy()

        summary = summarize_ensemble_predictions(member_calibrated, uncertainty_config=config)
        for group_name in valid_calibration_groups.unique():
            group_mask = valid_calibration_groups == group_name
            group_total = float(valid_totals.loc[group_mask].iloc[0])
            aligned_group = align_interval_summary_to_total(
                summary.loc[group_mask].copy(),
                official_total=group_total,
                uncertainty_config=config,
            )
            summary.loc[group_mask, aligned_group.columns] = aligned_group.to_numpy()

        confidence = assign_confidence_bands(summary["Population_Uncertainty_Relative"], uncertainty_config=config)
        diagnostics = valid_frame[[training_config.group_column, training_config.target_column]].copy()
        diagnostics["fold"] = fold_index
        diagnostics["validation_protocol"] = training_config.validation_protocol
        diagnostics["Population_Estimate_P10"] = summary["Population_Estimate_P10"].to_numpy()
        diagnostics["Population_Estimate_P50"] = summary["Population_Estimate_P50"].to_numpy()
        diagnostics["Population_Estimate_P90"] = summary["Population_Estimate_P90"].to_numpy()
        diagnostics["Population_Uncertainty_Relative"] = summary["Population_Uncertainty_Relative"].to_numpy()
        diagnostics["Population_Confidence_Band"] = confidence.to_numpy()
        diagnostics["Absolute_Error_P50"] = (
            diagnostics["Population_Estimate_P50"] - diagnostics[training_config.target_column]
        ).abs()
        diagnostics_rows.append(diagnostics)

        low_band_error = diagnostics.loc[diagnostics["Population_Confidence_Band"] == "high", "Absolute_Error_P50"]
        high_band_error = diagnostics.loc[diagnostics["Population_Confidence_Band"] == "low", "Absolute_Error_P50"]
        fold_rows.append(
            ErrorUncertaintyFoldMetrics(
                fold=fold_index,
                validation_protocol=training_config.validation_protocol,
                rows=int(len(diagnostics)),
                error_uncertainty_pearson=_safe_corr(
                    diagnostics["Population_Uncertainty_Relative"],
                    diagnostics["Absolute_Error_P50"],
                    method="pearson",
                ),
                error_uncertainty_spearman=_safe_corr(
                    diagnostics["Population_Uncertainty_Relative"],
                    diagnostics["Absolute_Error_P50"],
                    method="spearman",
                ),
                low_band_mean_abs_error=float(low_band_error.mean()) if not low_band_error.empty else float("nan"),
                high_band_mean_abs_error=float(high_band_error.mean()) if not high_band_error.empty else float("nan"),
            ).to_dict()
        )

    diagnostics_frame = pd.concat(diagnostics_rows, ignore_index=True) if diagnostics_rows else pd.DataFrame()
    fold_metrics = pd.DataFrame(fold_rows)
    return diagnostics_frame, fold_metrics


def compute_error_uncertainty_monotonicity(
    diagnostics_frame: pd.DataFrame,
    *,
    uncertainty_column: str = "Population_Uncertainty_Relative",
    error_column: str = "Absolute_Error_P50",
    bins: int = 5,
) -> tuple[pd.DataFrame, dict[str, float]]:
    if diagnostics_frame.empty:
        raise ValueError("Diagnostics frame is empty.")
    working = diagnostics_frame.copy()
    uncertainty = pd.to_numeric(working[uncertainty_column], errors="coerce")
    error = pd.to_numeric(working[error_column], errors="coerce")
    valid = uncertainty.notna() & error.notna()
    working = working.loc[valid].copy()
    if working.empty:
        raise ValueError("No valid rows remained after filtering.")

    bucket_count = min(max(2, int(bins)), max(2, int(working[uncertainty_column].nunique())))
    ranked = pd.to_numeric(working[uncertainty_column], errors="coerce").rank(method="first")
    working["uncertainty_bucket"] = pd.qcut(ranked, q=bucket_count, labels=False, duplicates="drop")
    summary = (
        working.groupby("uncertainty_bucket", as_index=False)
        .agg(
            row_count=(error_column, "size"),
            mean_uncertainty=(uncertainty_column, "mean"),
            mean_abs_error=(error_column, "mean"),
        )
        .sort_values("uncertainty_bucket")
        .reset_index(drop=True)
    )
    metrics = {
        "error_uncertainty_pearson": _safe_corr(working[uncertainty_column], working[error_column], method="pearson"),
        "error_uncertainty_spearman": _safe_corr(working[uncertainty_column], working[error_column], method="spearman"),
        "mean_abs_error_lowest_bucket": float(summary["mean_abs_error"].iloc[0]),
        "mean_abs_error_highest_bucket": float(summary["mean_abs_error"].iloc[-1]),
        "monotonic_non_decreasing": float(summary["mean_abs_error"].is_monotonic_increasing),
    }
    return summary, metrics


def aggregate_prediction_intervals_to_districts(prediction_gdf, district_gdf) -> pd.DataFrame:
    p10 = aggregate_predictions_to_districts(prediction_gdf, district_gdf, population_column="Population_Estimate_P10")
    p50 = aggregate_predictions_to_districts(prediction_gdf, district_gdf, population_column="Population_Estimate_P50")
    p90 = aggregate_predictions_to_districts(prediction_gdf, district_gdf, population_column="Population_Estimate_P90")

    merged = p50.copy()
    merged = merged.rename(columns={"predicted_population": "predicted_population_p50"})
    merged["predicted_population_p10"] = pd.to_numeric(p10["predicted_population"], errors="coerce").fillna(0.0)
    merged["predicted_population_p90"] = pd.to_numeric(p90["predicted_population"], errors="coerce").fillna(0.0)
    merged["interval_width"] = merged["predicted_population_p90"] - merged["predicted_population_p10"]
    merged["relative_interval_width"] = merged["interval_width"] / np.maximum(
        pd.to_numeric(merged["predicted_population_p50"], errors="coerce").fillna(0.0),
        1e-6,
    )
    official = pd.to_numeric(merged["official_population"], errors="coerce")
    merged["covered_by_interval"] = (
        official >= pd.to_numeric(merged["predicted_population_p10"], errors="coerce")
    ) & (
        official <= pd.to_numeric(merged["predicted_population_p90"], errors="coerce")
    )
    return merged


def compute_district_interval_coverage_metrics(
    district_interval_frame: pd.DataFrame,
    *,
    city_name: str,
) -> DistrictIntervalCoverageMetrics:
    if district_interval_frame.empty:
        raise ValueError("District interval frame is empty.")

    evaluation = district_interval_frame.loc[district_interval_frame["use_in_metrics"].fillna(False)].copy()
    if evaluation.empty:
        raise ValueError("No districts are marked with use_in_metrics=True.")

    official = pd.to_numeric(evaluation["official_population"], errors="coerce")
    predicted_p50 = pd.to_numeric(evaluation["predicted_population_p50"], errors="coerce")
    valid = official.notna() & predicted_p50.notna()
    evaluation = evaluation.loc[valid].copy()
    official = official.loc[valid]
    predicted_p50 = predicted_p50.loc[valid]
    if evaluation.empty:
        raise ValueError("No valid district rows remained after filtering.")

    rmse = float(np.sqrt(np.mean(np.square(predicted_p50 - official))))
    pearson_r = _safe_corr(official, predicted_p50, method="pearson")
    spearman_r = _safe_corr(official, predicted_p50, method="spearman")

    return DistrictIntervalCoverageMetrics(
        city_name=city_name,
        district_count_total=int(len(district_interval_frame)),
        district_count_compared=int(len(evaluation)),
        coverage_rate=float(evaluation["covered_by_interval"].mean()),
        median_interval_width=float(pd.to_numeric(evaluation["interval_width"], errors="coerce").median()),
        median_relative_interval_width=float(
            pd.to_numeric(evaluation["relative_interval_width"], errors="coerce").median()
        ),
        p50_rmse=rmse,
        p50_pearson_r=pearson_r,
        p50_spearman_r=spearman_r,
    )


def compute_external_disagreement_alignment(
    aligned_frame: pd.DataFrame,
    *,
    city_name: str,
    city_slug: str,
    uncertainty_column: str = "Population_Uncertainty_Relative",
    city1_column: str = "city1_population",
) -> pd.DataFrame:
    if uncertainty_column not in aligned_frame.columns:
        raise ValueError(f"Aligned frame is missing {uncertainty_column!r}.")

    rows: list[dict[str, object]] = []
    uncertainty = pd.to_numeric(aligned_frame[uncertainty_column], errors="coerce").fillna(0.0)
    high_threshold = float(uncertainty.quantile(0.90))
    low_threshold = float(uncertainty.quantile(0.10))

    for benchmark_column in ("worldpop_population", "ghs_pop_population"):
        if benchmark_column not in aligned_frame.columns:
            continue
        disagreement = (
            pd.to_numeric(aligned_frame[city1_column], errors="coerce").fillna(0.0)
            - pd.to_numeric(aligned_frame[benchmark_column], errors="coerce").fillna(0.0)
        ).abs()
        high_uncertainty = disagreement.loc[uncertainty >= high_threshold]
        low_uncertainty = disagreement.loc[uncertainty <= low_threshold]
        rows.append(
            ExternalDisagreementAlignmentMetrics(
                city_name=city_name,
                city_slug=city_slug,
                benchmark_name=benchmark_column.replace("_population", ""),
                row_count=int(len(aligned_frame)),
                disagreement_uncertainty_pearson=_safe_corr(uncertainty, disagreement, method="pearson"),
                disagreement_uncertainty_spearman=_safe_corr(uncertainty, disagreement, method="spearman"),
                high_uncertainty_mean_disagreement=float(high_uncertainty.mean()) if not high_uncertainty.empty else float("nan"),
                low_uncertainty_mean_disagreement=float(low_uncertainty.mean()) if not low_uncertainty.empty else float("nan"),
            ).to_dict()
        )

    return pd.DataFrame(rows)


def run_external_disagreement_alignment(
    city_slug: str,
    *,
    config: ExternalBenchmarkConfig | None = None,
    uncertainty_column: str = "Population_Uncertainty_Relative",
) -> pd.DataFrame:
    benchmark_config = config or ExternalBenchmarkConfig(city1_model_suffix="random_forest_uncertainty")
    aligned, _ = build_city_external_benchmark_alignment(city_slug, config=benchmark_config)
    city_name = str(aligned["city_name"].iloc[0]) if "city_name" in aligned.columns else city_slug.title()
    return compute_external_disagreement_alignment(
        aligned,
        city_name=city_name,
        city_slug=city_slug,
        uncertainty_column=uncertainty_column,
    )
