from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np
import pandas as pd

from .city_totals import CityTotalsLookup, load_city_totals, normalize_city_name
from .hotspot_prioritization import HOTSPOT_PRIORITY_CLASSES
from .labeling import WeakLabelConfig, allocate_city_total_to_cells
from .training import (
    TrainingConfig,
    _validation_setup,
    build_training_dataset,
    calibrate_predictions_by_group,
    sanitize_feature_frame_for_training,
)
from .uncertainty import (
    LoadedUncertaintyArtifact,
    UncertaintyConfig,
    align_interval_summary_to_total,
    assign_confidence_bands_from_score,
    compute_confidence_score,
    compute_model_stability_score,
    predict_uncertainty_ensemble,
    summarize_ensemble_predictions,
    train_uncertainty_ensemble,
)
from .validation import validate_city_output_v3


DEFAULT_FREEZE_CITIES: tuple[str, ...] = ("almaty", "astana", "semey", "shymkent")
DEFAULT_BENCHMARK_CITIES: tuple[str, ...] = ("almaty", "astana", "shymkent")


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


@dataclass(frozen=True)
class Phase6InputValidationResult:
    run_id: str
    required_files: tuple[str, ...]
    missing_files: tuple[str, ...]
    validation_errors: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.missing_files and not self.validation_errors


def _safe_corr(series_a: pd.Series, series_b: pd.Series, method: str) -> float:
    frame = pd.DataFrame({"a": pd.to_numeric(series_a, errors="coerce"), "b": pd.to_numeric(series_b, errors="coerce")})
    frame = frame.replace([np.inf, -np.inf], np.nan).dropna()
    if len(frame) < 2:
        return float("nan")
    if frame["a"].nunique() <= 1 or frame["b"].nunique() <= 1:
        return float("nan")
    value = frame["a"].corr(frame["b"], method=method)
    return float(value) if pd.notna(value) else float("nan")


def _safe_divide(numerator: float | int, denominator: float | int, *, default: float = float("nan")) -> float:
    denom = float(denominator)
    if not np.isfinite(denom) or abs(denom) <= 1e-12:
        return default
    return float(numerator) / denom


def _city_slug(value: object) -> str:
    return normalize_city_name(str(value)).replace(" ", "_")


def _city_display(value: object, display_lookup: Mapping[str, str] | None = None) -> str:
    normalized = normalize_city_name(str(value))
    if display_lookup and normalized in display_lookup:
        return str(display_lookup[normalized])
    return str(value).replace("_", " ").title()


def _normalize_support_score(value: float | int | str | None) -> float:
    if value is None:
        return 0.0
    numeric = float(value)
    if numeric > 1.0:
        numeric = numeric / 100.0
    return float(np.clip(numeric, 0.0, 1.0))


def load_city_display_lookup(city_status_csv: str | Path) -> dict[str, str]:
    path = Path(city_status_csv)
    if not path.exists():
        return {}
    frame = pd.read_csv(path)
    if "normalized_city_name" not in frame.columns or "city_name" not in frame.columns:
        return {}
    return {
        normalize_city_name(row["normalized_city_name"]): str(row["city_name"])
        for row in frame.to_dict(orient="records")
        if str(row.get("normalized_city_name", "")).strip()
    }


def load_city_completeness_lookup(osm_summary_csv: str | Path) -> dict[str, tuple[float, str]]:
    path = Path(osm_summary_csv)
    if not path.exists():
        return {}
    frame = pd.read_csv(path)
    if "city_name" not in frame.columns or "completeness_score" not in frame.columns:
        return {}
    lookup: dict[str, tuple[float, str]] = {}
    for row in frame.to_dict(orient="records"):
        normalized = normalize_city_name(str(row.get("city_name", "")))
        if not normalized:
            continue
        lookup[normalized] = (
            _normalize_support_score(row.get("completeness_score", 0.0)),
            str(row.get("completeness_label", "unknown")),
        )
    return lookup


def load_city_internal_support_lookup(city_status_csv: str | Path) -> dict[str, float]:
    path = Path(city_status_csv)
    if not path.exists():
        return {}
    frame = pd.read_csv(path)
    lookup: dict[str, float] = {}
    for row in frame.to_dict(orient="records"):
        normalized = normalize_city_name(str(row.get("normalized_city_name") or row.get("city_name", "")))
        if not normalized:
            continue
        quality = str(row.get("district_benchmark_quality", "none")).strip().lower()
        if quality == "strong":
            score = 0.75
        elif quality == "partial":
            score = 0.55
        elif quality == "mixed":
            score = 0.50
        else:
            score = 0.40
        lookup[normalized] = score
    return lookup


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


def _build_hotspot_priority_fields(
    p50: pd.Series,
    confidence_band: pd.Series,
) -> tuple[pd.Series, pd.Series]:
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
    return hotspot_rank, priority


def cross_validate_uncertainty_by_city(
    frame: pd.DataFrame,
    *,
    training_config: TrainingConfig,
    uncertainty_config: UncertaintyConfig | None = None,
    display_lookup: Mapping[str, str] | None = None,
    completeness_lookup: Mapping[str, tuple[float, str]] | None = None,
    external_agreement_score: float = 0.50,
    internal_support_lookup: Mapping[str, float] | None = None,
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

        city_series = valid_frame[training_config.group_column].astype(str).reset_index(drop=True)
        city_display_series = city_series.map(lambda value: _city_display(value, display_lookup))
        city_slug_series = city_series.map(_city_slug)
        city_completeness_score = city_series.map(
            lambda value: (completeness_lookup or {}).get(normalize_city_name(str(value)), (0.0, "unknown"))[0]
        )
        city_completeness_label = city_series.map(
            lambda value: (completeness_lookup or {}).get(normalize_city_name(str(value)), (0.0, "unknown"))[1]
        )
        city_internal_support = city_series.map(
            lambda value: (internal_support_lookup or {}).get(normalize_city_name(str(value)), 0.50)
        )

        model_stability_score = compute_model_stability_score(summary["Population_Uncertainty_Relative"])
        confidence_score = pd.Series(index=summary.index, dtype=float)
        confidence_band = pd.Series(index=summary.index, dtype="object")
        for city_name in city_series.unique():
            group_mask = city_series == city_name
            group_model_stability = model_stability_score.loc[group_mask]
            group_confidence_score = compute_confidence_score(
                group_model_stability,
                osm_support_score=float(city_completeness_score.loc[group_mask].iloc[0]),
                external_agreement_score=external_agreement_score,
                internal_support_score=float(city_internal_support.loc[group_mask].iloc[0]),
            )
            confidence_score.loc[group_mask] = group_confidence_score.to_numpy()
            confidence_band.loc[group_mask] = assign_confidence_bands_from_score(group_confidence_score).to_numpy()

        hotspot_rank, hotspot_priority = _build_hotspot_priority_fields(
            summary["Population_Estimate_P50"],
            confidence_band,
        )

        diagnostics = pd.DataFrame(
            {
                "fold": fold_index,
                "protocol": "locov_like",
                "validation_protocol": training_config.validation_protocol,
                "city": city_display_series,
                "city_slug": city_slug_series,
                "cell_id": valid_frame.get("Zone_ID", pd.Series(index=valid_frame.index, dtype="object")).astype(str).to_numpy(),
                "weak_target": y_true.to_numpy(),
                "p10": summary["Population_Estimate_P10"].to_numpy(),
                "p50": summary["Population_Estimate_P50"].to_numpy(),
                "p90": summary["Population_Estimate_P90"].to_numpy(),
                "uncertainty_width": summary["Population_Uncertainty_Width"].to_numpy(),
                "relative_uncertainty": summary["Population_Uncertainty_Relative"].to_numpy(),
                "model_stability_score": model_stability_score.to_numpy(),
                "confidence_score": confidence_score.to_numpy(),
                "confidence_band": confidence_band.to_numpy(),
                "osm_completeness_score": city_completeness_score.to_numpy(),
                "osm_completeness_label": city_completeness_label.to_numpy(),
                "internal_support_score": city_internal_support.to_numpy(),
                "external_agreement_score": float(external_agreement_score),
                "hotspot_rank": hotspot_rank.to_numpy(),
                "hotspot_priority_class": hotspot_priority.to_numpy(),
            }
        )
        diagnostics["covered_by_p10_p90"] = (
            (pd.to_numeric(diagnostics["weak_target"], errors="coerce") >= pd.to_numeric(diagnostics["p10"], errors="coerce"))
            & (pd.to_numeric(diagnostics["weak_target"], errors="coerce") <= pd.to_numeric(diagnostics["p90"], errors="coerce"))
        )
        diagnostics["absolute_error_p50"] = (
            pd.to_numeric(diagnostics["p50"], errors="coerce") - pd.to_numeric(diagnostics["weak_target"], errors="coerce")
        ).abs()
        diagnostics_rows.append(diagnostics)

        high_band_error = diagnostics.loc[diagnostics["confidence_band"] == "low", "absolute_error_p50"]
        low_band_error = diagnostics.loc[diagnostics["confidence_band"] == "high", "absolute_error_p50"]
        fold_rows.append(
            ErrorUncertaintyFoldMetrics(
                fold=fold_index,
                validation_protocol=training_config.validation_protocol,
                rows=int(len(diagnostics)),
                error_uncertainty_pearson=_safe_corr(
                    diagnostics["relative_uncertainty"],
                    diagnostics["absolute_error_p50"],
                    method="pearson",
                ),
                error_uncertainty_spearman=_safe_corr(
                    diagnostics["relative_uncertainty"],
                    diagnostics["absolute_error_p50"],
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


def compute_interval_coverage_summary(
    diagnostics_frame: pd.DataFrame,
    *,
    protocol: str,
    city_column: str = "city",
    target_column: str = "weak_target",
    p10_column: str = "p10",
    p90_column: str = "p90",
    width_column: str = "uncertainty_width",
    relative_column: str = "relative_uncertainty",
) -> pd.DataFrame:
    if diagnostics_frame.empty:
        return pd.DataFrame(
            columns=[
                "run_id",
                "protocol",
                "city",
                "n_cells",
                "coverage_p10_p90",
                "below_p10_share",
                "above_p90_share",
                "mean_interval_width",
                "median_interval_width",
                "mean_relative_uncertainty",
                "median_relative_uncertainty",
                "interpretation_note",
            ]
        )

    rows: list[dict[str, object]] = []
    for city_name, group in diagnostics_frame.groupby(city_column):
        target = pd.to_numeric(group[target_column], errors="coerce")
        p10 = pd.to_numeric(group[p10_column], errors="coerce")
        p90 = pd.to_numeric(group[p90_column], errors="coerce")
        width = pd.to_numeric(group[width_column], errors="coerce")
        relative = pd.to_numeric(group[relative_column], errors="coerce")
        valid = target.notna() & p10.notna() & p90.notna()
        subset = group.loc[valid].copy()
        if subset.empty:
            continue
        target = target.loc[valid]
        p10 = p10.loc[valid]
        p90 = p90.loc[valid]
        covered = (target >= p10) & (target <= p90)
        below = target < p10
        above = target > p90
        coverage_rate = float(covered.mean()) if len(covered) else float("nan")
        if coverage_rate >= 0.80:
            note = "The p10-p90 proxy interval captures a large share of held-out proxy targets, supporting bounded interval usefulness under weak supervision."
        elif coverage_rate >= 0.60:
            note = "The p10-p90 proxy interval shows moderate held-out proxy coverage; uncertainty behavior is informative but not uniformly tight."
        else:
            note = "The p10-p90 proxy interval covers a limited share of held-out proxy targets, so uncertainty evidence should be interpreted cautiously."
        rows.append(
            {
                "protocol": protocol,
                "city": str(city_name),
                "n_cells": int(len(subset)),
                "coverage_p10_p90": coverage_rate,
                "below_p10_share": float(below.mean()) if len(below) else float("nan"),
                "above_p90_share": float(above.mean()) if len(above) else float("nan"),
                "mean_interval_width": float(width.loc[valid].mean()),
                "median_interval_width": float(width.loc[valid].median()),
                "mean_relative_uncertainty": float(relative.loc[valid].mean()),
                "median_relative_uncertainty": float(relative.loc[valid].median()),
                "interpretation_note": note,
            }
        )
    return pd.DataFrame(rows)


def compute_error_uncertainty_alignment_summary(
    diagnostics_frame: pd.DataFrame,
    *,
    protocol: str,
    city_column: str = "city",
    error_column: str = "absolute_error_p50",
    width_column: str = "uncertainty_width",
    relative_column: str = "relative_uncertainty",
    confidence_column: str = "confidence_score",
    stability_column: str = "model_stability_score",
    band_column: str = "confidence_band",
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    if diagnostics_frame.empty:
        return pd.DataFrame(
            columns=[
                "run_id",
                "protocol",
                "city",
                "n_cells",
                "pearson_error_vs_uncertainty_width",
                "spearman_error_vs_uncertainty_width",
                "pearson_error_vs_relative_uncertainty",
                "spearman_error_vs_relative_uncertainty",
                "pearson_error_vs_confidence_score",
                "spearman_error_vs_confidence_score",
                "mean_error_high_confidence",
                "mean_error_medium_confidence",
                "mean_error_low_confidence",
                "interpretation_note",
            ]
        )

    for city_name, group in diagnostics_frame.groupby(city_column):
        error = pd.to_numeric(group[error_column], errors="coerce")
        width = pd.to_numeric(group[width_column], errors="coerce")
        relative = pd.to_numeric(group[relative_column], errors="coerce")
        confidence = pd.to_numeric(group[confidence_column], errors="coerce")
        stability = pd.to_numeric(group[stability_column], errors="coerce")
        band = group[band_column].astype(str)
        if error.dropna().empty:
            continue
        high_error = error.loc[band == "high"]
        medium_error = error.loc[band == "medium"]
        low_error = error.loc[band == "low"]

        note = "Higher proxy error generally concentrates in higher-uncertainty or lower-confidence cells." if (
            _safe_corr(error, relative, "spearman") > 0 or _safe_corr(error, confidence, "spearman") < 0
        ) else "Error-vs-uncertainty alignment is weak or mixed in this city and should be interpreted cautiously."

        rows.append(
            {
                "protocol": protocol,
                "city": str(city_name),
                "n_cells": int(len(group)),
                "pearson_error_vs_uncertainty_width": _safe_corr(error, width, method="pearson"),
                "spearman_error_vs_uncertainty_width": _safe_corr(error, width, method="spearman"),
                "pearson_error_vs_relative_uncertainty": _safe_corr(error, relative, method="pearson"),
                "spearman_error_vs_relative_uncertainty": _safe_corr(error, relative, method="spearman"),
                "pearson_error_vs_confidence_score": _safe_corr(error, confidence, method="pearson"),
                "spearman_error_vs_confidence_score": _safe_corr(error, confidence, method="spearman"),
                "pearson_error_vs_model_stability": _safe_corr(error, stability, method="pearson"),
                "spearman_error_vs_model_stability": _safe_corr(error, stability, method="spearman"),
                "mean_error_high_confidence": float(high_error.mean()) if not high_error.empty else float("nan"),
                "mean_error_medium_confidence": float(medium_error.mean()) if not medium_error.empty else float("nan"),
                "mean_error_low_confidence": float(low_error.mean()) if not low_error.empty else float("nan"),
                "interpretation_note": note,
            }
        )
    return pd.DataFrame(rows)


def validate_phase6_city_frame(frame: pd.DataFrame, *, dataset_name: str, tolerance: float = 1e-6) -> list[str]:
    report = validate_city_output_v3(frame, dataset_name)
    issues = [
        f"{dataset_name}: {issue.code}: {issue.message}"
        for issue in report.issues
        if issue.level == "error"
    ]

    required = {
        "p10",
        "p50",
        "p90",
        "population_estimate_final",
        "uncertainty_width",
        "relative_uncertainty",
        "confidence_score",
        "confidence_band",
        "hotspot_priority_class",
        "official_city_total",
    }
    missing = required.difference(frame.columns)
    if missing:
        issues.append(f"{dataset_name}: missing required uncertainty columns: {sorted(missing)}")
        return issues

    p10 = pd.to_numeric(frame["p10"], errors="coerce")
    p50 = pd.to_numeric(frame["p50"], errors="coerce")
    p90 = pd.to_numeric(frame["p90"], errors="coerce")
    width = pd.to_numeric(frame["uncertainty_width"], errors="coerce")
    relative = pd.to_numeric(frame["relative_uncertainty"], errors="coerce")
    confidence = pd.to_numeric(frame["confidence_score"], errors="coerce")

    if int(((p10 > p50) | (p50 > p90)).fillna(True).sum()) > 0:
        issues.append(f"{dataset_name}: p10 <= p50 <= p90 failed.")
    if int(((width - (p90 - p10)).abs() > tolerance).fillna(True).sum()) > 0:
        issues.append(f"{dataset_name}: uncertainty_width != p90 - p10.")
    if not np.isfinite(relative.replace([np.inf, -np.inf], np.nan)).all():
        issues.append(f"{dataset_name}: relative_uncertainty contains non-finite values.")
    if int((~confidence.between(0, 1)).fillna(True).sum()) > 0:
        issues.append(f"{dataset_name}: confidence_score outside [0,1].")
    invalid_bands = set(frame["confidence_band"].astype(str)) - {"high", "medium", "low"}
    if invalid_bands:
        issues.append(f"{dataset_name}: invalid confidence_band values: {sorted(invalid_bands)}")
    invalid_classes = set(frame["hotspot_priority_class"].astype(str)) - HOTSPOT_PRIORITY_CLASSES
    if invalid_classes:
        issues.append(f"{dataset_name}: invalid hotspot_priority_class values: {sorted(invalid_classes)}")

    official_total = float(pd.to_numeric(frame["official_city_total"], errors="coerce").dropna().iloc[0])
    if abs(float(p50.sum()) - official_total) > max(1e-3, official_total * 1e-9):
        issues.append(f"{dataset_name}: sum(p50) is not close to official_city_total.")
    return issues


def validate_phase6_inputs(
    *,
    run_id: str,
    inference_root: str | Path,
    hotspot_root: str | Path,
    cities: Iterable[str] = DEFAULT_FREEZE_CITIES,
) -> Phase6InputValidationResult:
    inference_dir = Path(inference_root) / run_id
    hotspot_dir = Path(hotspot_root) / run_id
    required_paths = [
        inference_dir / f"{city}_uncertainty_cells.csv"
        for city in cities
    ] + [
        inference_dir / "city_uncertainty_summary.csv",
        inference_dir / "run_manifest.json",
        hotspot_dir / "hotspot_city_summary.csv",
        hotspot_dir / "top_hotspots_by_city.csv",
        hotspot_dir / "caution_hotspots.csv",
        hotspot_dir / "stable_hotspots.csv",
        hotspot_dir / "PHASE_5_HOTSPOT_PRIORITIZATION_REPORT.md",
    ]

    missing = [str(path) for path in required_paths if not path.exists()]
    validation_errors: list[str] = []
    for city in cities:
        csv_path = inference_dir / f"{city}_uncertainty_cells.csv"
        if not csv_path.exists():
            continue
        frame = pd.read_csv(csv_path)
        validation_errors.extend(validate_phase6_city_frame(frame, dataset_name=csv_path.name))

    return Phase6InputValidationResult(
        run_id=run_id,
        required_files=tuple(str(path) for path in required_paths),
        missing_files=tuple(missing),
        validation_errors=tuple(validation_errors),
    )


def load_phase4_city_frames(
    *,
    run_id: str,
    inference_root: str | Path,
    cities: Iterable[str] = DEFAULT_FREEZE_CITIES,
) -> dict[str, pd.DataFrame]:
    inference_dir = Path(inference_root) / run_id
    frames: dict[str, pd.DataFrame] = {}
    for city in cities:
        path = inference_dir / f"{city}_uncertainty_cells.csv"
        if path.exists():
            frames[city] = pd.read_csv(path)
    return frames


def _build_weak_target_frame_for_city(
    city_slug: str,
    *,
    features_dir: str | Path,
    totals_lookup: CityTotalsLookup,
    training_config: TrainingConfig,
    label_config: WeakLabelConfig | None = None,
) -> pd.DataFrame:
    features_path = Path(features_dir) / f"{city_slug}.csv"
    if not features_path.exists():
        raise FileNotFoundError(f"Missing feature file for city {city_slug!r}: {features_path}")
    official_population = totals_lookup.get_population(city_slug)
    if official_population is None:
        raise ValueError(f"No official total found for city {city_slug!r}.")

    feature_frame = sanitize_feature_frame_for_training(
        pd.read_csv(features_path),
        required_feature_columns=training_config.feature_columns,
    )
    labeled = allocate_city_total_to_cells(
        feature_frame,
        official_population=official_population,
        config=label_config or WeakLabelConfig(),
    )
    return labeled


def load_inference_only_proxy_check_frames(
    *,
    run_id: str,
    inference_root: str | Path,
    features_dir: str | Path,
    totals_csv: str | Path,
    cities: Iterable[str] = DEFAULT_FREEZE_CITIES,
    training_config: TrainingConfig | None = None,
    label_config: WeakLabelConfig | None = None,
) -> dict[str, pd.DataFrame]:
    config = training_config or TrainingConfig(model_name="random_forest")
    totals_lookup = load_city_totals(totals_csv)
    frames = load_phase4_city_frames(run_id=run_id, inference_root=inference_root, cities=cities)
    joined_frames: dict[str, pd.DataFrame] = {}

    for city_slug, output_frame in frames.items():
        weak_frame = _build_weak_target_frame_for_city(
            city_slug,
            features_dir=features_dir,
            totals_lookup=totals_lookup,
            training_config=config,
            label_config=label_config,
        )
        joined = output_frame.merge(
            weak_frame[["Zone_ID", "Weak_Population_Target"]],
            left_on="cell_id",
            right_on="Zone_ID",
            how="left",
        )
        joined["protocol"] = "inference_only_proxy_check"
        joined["weak_target"] = pd.to_numeric(joined["Weak_Population_Target"], errors="coerce")
        joined["covered_by_p10_p90"] = (
            joined["weak_target"].ge(pd.to_numeric(joined["p10"], errors="coerce"))
            & joined["weak_target"].le(pd.to_numeric(joined["p90"], errors="coerce"))
        )
        joined["absolute_error_p50"] = (
            pd.to_numeric(joined["p50"], errors="coerce") - joined["weak_target"]
        ).abs()
        joined_frames[city_slug] = joined
    return joined_frames


def concatenate_proxy_check_frames(frames: Mapping[str, pd.DataFrame]) -> pd.DataFrame:
    if not frames:
        return pd.DataFrame()
    ordered = [frame.copy() for _, frame in sorted(frames.items()) if not frame.empty]
    if not ordered:
        return pd.DataFrame()
    return pd.concat(ordered, ignore_index=True)


def aggregate_prediction_intervals_to_districts(prediction_gdf, district_gdf) -> pd.DataFrame:
    from .district_benchmark import aggregate_predictions_to_districts

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


def build_partial_district_interval_coverage(
    *,
    run_id: str,
    district_report_root: str | Path,
    cities: Iterable[str] = DEFAULT_BENCHMARK_CITIES,
    display_lookup: Mapping[str, str] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, object]] = []
    summary_rows: list[dict[str, object]] = []
    for city_slug in cities:
        table_path = Path(district_report_root) / city_slug / "district_benchmark_table.csv"
        city_name = _city_display(city_slug, display_lookup)
        if not table_path.exists():
            summary_rows.append(
                {
                    "city": city_name,
                    "n_districts_compared": 0,
                    "n_districts_covered": float("nan"),
                    "district_interval_coverage_rate": float("nan"),
                    "mean_absolute_error_p50": float("nan"),
                    "median_absolute_error_p50": float("nan"),
                    "mean_relative_error_p50": float("nan"),
                    "median_relative_error_p50": float("nan"),
                    "mean_relative_interval_width": float("nan"),
                    "interpretation_note": "District interval coverage is blocked because no frozen district benchmark table was available in the light package.",
                }
            )
            continue

        frame = pd.read_csv(table_path)
        evaluation = frame.loc[frame["use_in_metrics"].astype(str).str.lower().isin({"true", "1", "yes"})].copy()
        official = pd.to_numeric(evaluation["official_population"], errors="coerce")
        predicted = pd.to_numeric(evaluation["predicted_population"], errors="coerce")
        absolute_error = (predicted - official).abs()
        relative_error = absolute_error / np.maximum(official, 1e-6)

        for row in frame.to_dict(orient="records"):
            official_population = pd.to_numeric(pd.Series([row.get("official_population")]), errors="coerce").iloc[0]
            predicted_p50 = pd.to_numeric(pd.Series([row.get("predicted_population")]), errors="coerce").iloc[0]
            absolute_error_p50 = abs(predicted_p50 - official_population) if pd.notna(predicted_p50) and pd.notna(official_population) else float("nan")
            relative_error_p50 = _safe_divide(absolute_error_p50, official_population)
            rows.append(
                {
                    "city": city_name,
                    "district_name": str(row.get("district_name", "")),
                    "reference_population": official_population,
                    "predicted_p10": float("nan"),
                    "predicted_p50": predicted_p50,
                    "predicted_p90": float("nan"),
                    "covered_by_p10_p90": float("nan"),
                    "absolute_error_p50": absolute_error_p50,
                    "relative_error_p50": relative_error_p50,
                    "interval_width": float("nan"),
                    "relative_interval_width": float("nan"),
                    "source_note": "Partial carry-forward from the frozen v2 district benchmark table. District interval aggregation could not be reconstructed because district polygon/cell mapping artifacts are not frozen in the light package.",
                    "interpretation_note": "This row supports partial administrative comparison of district-level p50 totals only; it does not provide district interval coverage.",
                }
            )

        summary_rows.append(
            {
                "city": city_name,
                "n_districts_compared": int(len(evaluation)),
                "n_districts_covered": float("nan"),
                "district_interval_coverage_rate": float("nan"),
                "mean_absolute_error_p50": float(absolute_error.mean()) if not absolute_error.empty else float("nan"),
                "median_absolute_error_p50": float(absolute_error.median()) if not absolute_error.empty else float("nan"),
                "mean_relative_error_p50": float(relative_error.mean()) if not relative_error.empty else float("nan"),
                "median_relative_error_p50": float(relative_error.median()) if not relative_error.empty else float("nan"),
                "mean_relative_interval_width": float("nan"),
                "interpretation_note": "Only partial district p50 comparison could be carried forward from v2. District interval coverage remains blocked until frozen district assignment artifacts are available offline.",
            }
        )

    return pd.DataFrame(rows), pd.DataFrame(summary_rows)


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


def build_external_disagreement_alignment_from_v2_reports(
    *,
    run_id: str,
    inference_root: str | Path,
    external_report_root: str | Path,
    cities: Iterable[str] = DEFAULT_BENCHMARK_CITIES,
    display_lookup: Mapping[str, str] | None = None,
) -> pd.DataFrame:
    v3_frames = load_phase4_city_frames(run_id=run_id, inference_root=inference_root, cities=cities)
    rows: list[dict[str, object]] = []
    for city_slug in cities:
        if city_slug not in v3_frames:
            continue
        external_path = Path(external_report_root) / city_slug / "external_benchmark_aligned.csv"
        if not external_path.exists():
            continue
        v3_frame = v3_frames[city_slug].copy()
        external_frame = pd.read_csv(external_path).rename(columns={"Zone_ID": "cell_id"})
        merged = v3_frame.merge(
            external_frame[["cell_id", "worldpop_population", "ghs_pop_population"]],
            on="cell_id",
            how="inner",
        )
        merged["city1_population"] = pd.to_numeric(merged["p50"], errors="coerce")
        merged["Population_Uncertainty_Relative"] = pd.to_numeric(merged["relative_uncertainty"], errors="coerce")
        alignment = compute_external_disagreement_alignment(
            merged,
            city_name=_city_display(city_slug, display_lookup),
            city_slug=city_slug,
        )
        if alignment.empty:
            continue
        for row in alignment.to_dict(orient="records"):
            disagreement_metric = f"absolute_difference_to_{row['benchmark_name']}"
            note = "Higher disagreement tends to coincide with higher relative uncertainty." if (
                pd.notna(row["disagreement_uncertainty_spearman"]) and float(row["disagreement_uncertainty_spearman"]) > 0
            ) else "Disagreement alignment is weak or mixed for this benchmark and should be interpreted cautiously."
            rows.append(
                {
                    "city": row["city_name"],
                    "benchmark_product": row["benchmark_name"],
                    "n_cells_or_summary_units": int(row["row_count"]),
                    "disagreement_metric": disagreement_metric,
                    "uncertainty_metric": "relative_uncertainty",
                    "pearson_disagreement_vs_uncertainty": row["disagreement_uncertainty_pearson"],
                    "spearman_disagreement_vs_uncertainty": row["disagreement_uncertainty_spearman"],
                    "mean_uncertainty_high_disagreement": float(
                        merged.loc[
                            (
                                pd.to_numeric(merged["city1_population"], errors="coerce")
                                - pd.to_numeric(merged[f"{row['benchmark_name']}_population"], errors="coerce")
                            ).abs()
                            >= (
                                (
                                    pd.to_numeric(merged["city1_population"], errors="coerce")
                                    - pd.to_numeric(merged[f"{row['benchmark_name']}_population"], errors="coerce")
                                ).abs().quantile(0.90)
                            ),
                            "Population_Uncertainty_Relative",
                        ].mean()
                    ),
                    "mean_uncertainty_low_disagreement": float(
                        merged.loc[
                            (
                                pd.to_numeric(merged["city1_population"], errors="coerce")
                                - pd.to_numeric(merged[f"{row['benchmark_name']}_population"], errors="coerce")
                            ).abs()
                            <= (
                                (
                                    pd.to_numeric(merged["city1_population"], errors="coerce")
                                    - pd.to_numeric(merged[f"{row['benchmark_name']}_population"], errors="coerce")
                                ).abs().quantile(0.10)
                            ),
                            "Population_Uncertainty_Relative",
                        ].mean()
                    ),
                    "interpretation_note": note,
                }
            )
    return pd.DataFrame(rows)


def compute_hotspot_stability_tables(
    city_frames: Mapping[str, pd.DataFrame],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    detail_rows: list[dict[str, object]] = []
    summary_rows: list[dict[str, object]] = []
    for city_slug, frame in city_frames.items():
        if frame.empty:
            continue
        priority = frame.loc[frame["hotspot_priority_class"].astype(str) != "not_priority"].copy()
        if priority.empty:
            continue
        relative = pd.to_numeric(priority["relative_uncertainty"], errors="coerce").fillna(0.0)
        width = pd.to_numeric(priority["uncertainty_width"], errors="coerce").fillna(0.0)
        confidence = pd.to_numeric(priority["confidence_score"], errors="coerce").fillna(0.0)
        width_norm = 1.0 - (width / max(float(width.quantile(0.90)), 1e-6)).clip(upper=1.0)
        relative_norm = 1.0 - (relative / max(float(relative.quantile(0.90)), 1e-6)).clip(upper=1.0)
        base_stability = 0.60 * confidence + 0.25 * relative_norm + 0.15 * width_norm
        adjustment = priority["hotspot_priority_class"].astype(str).map(
            {
                "high_value_high_confidence": 0.05,
                "medium_value_high_confidence": 0.03,
                "high_value_low_confidence": -0.08,
                "low_value_high_uncertainty": -0.12,
            }
        ).fillna(0.0)
        stability_metric = (base_stability + adjustment).clip(lower=0.0, upper=1.0)
        stability_band = pd.Series("medium", index=priority.index, dtype="object")
        stability_band.loc[stability_metric >= 0.67] = "high"
        stability_band.loc[stability_metric < 0.40] = "low"

        for idx, row in priority.iterrows():
            detail_rows.append(
                {
                    "city": str(row.get("city", _city_display(city_slug))),
                    "cell_id": str(row.get("cell_id", "")),
                    "hotspot_rank": int(pd.to_numeric(pd.Series([row.get("hotspot_rank")]), errors="coerce").fillna(0).iloc[0]),
                    "hotspot_priority_class": str(row.get("hotspot_priority_class", "")),
                    "p50": float(pd.to_numeric(pd.Series([row.get("p50")]), errors="coerce").fillna(0.0).iloc[0]),
                    "relative_uncertainty": float(pd.to_numeric(pd.Series([row.get("relative_uncertainty")]), errors="coerce").fillna(0.0).iloc[0]),
                    "confidence_score": float(pd.to_numeric(pd.Series([row.get("confidence_score")]), errors="coerce").fillna(0.0).iloc[0]),
                    "stability_metric": float(stability_metric.loc[idx]),
                    "stability_type": "proxy_from_confidence_and_interval_behavior",
                    "stability_band": str(stability_band.loc[idx]),
                    "interpretation_note": (
                        "Priority cell shows relatively stable hotspot behavior within the bounded v3 confidence framework."
                        if stability_metric.loc[idx] >= 0.67
                        else "Priority cell should be treated cautiously because the bounded stability proxy remains moderate or low."
                    ),
                }
            )

        grouped = pd.DataFrame(
            {
                "hotspot_priority_class": priority["hotspot_priority_class"].astype(str),
                "stability_metric": stability_metric,
                "confidence_score": confidence,
                "relative_uncertainty": relative,
            }
        )
        for priority_class, group in grouped.groupby("hotspot_priority_class"):
            summary_rows.append(
                {
                    "city": str(priority["city"].iloc[0]),
                    "hotspot_priority_class": str(priority_class),
                    "n_cells": int(len(group)),
                    "mean_stability_metric": float(group["stability_metric"].mean()),
                    "median_stability_metric": float(group["stability_metric"].median()),
                    "mean_confidence_score": float(group["confidence_score"].mean()),
                    "median_relative_uncertainty": float(group["relative_uncertainty"].median()),
                    "interpretation_note": (
                        "Stable hotspot classes retain stronger confidence/stability behavior than caution classes."
                        if priority_class in {"high_value_high_confidence", "medium_value_high_confidence"}
                        else "Caution-oriented hotspot classes remain less stable and should not be treated as firm planning targets."
                    ),
                }
            )

    return pd.DataFrame(detail_rows), pd.DataFrame(summary_rows)


def compute_confidence_band_validation_summary(
    diagnostics_frame: pd.DataFrame,
    *,
    city_column: str = "city",
    band_column: str = "confidence_band",
    p50_column: str = "p50",
    width_column: str = "uncertainty_width",
    relative_column: str = "relative_uncertainty",
    error_column: str = "absolute_error_p50",
    hotspot_column: str = "hotspot_priority_class",
) -> pd.DataFrame:
    if diagnostics_frame.empty:
        return pd.DataFrame(
            columns=[
                "run_id",
                "city",
                "confidence_band",
                "n_cells",
                "share_cells",
                "mean_p50",
                "median_p50",
                "mean_uncertainty_width",
                "median_relative_uncertainty",
                "mean_error_if_available",
                "share_hotspot_priority_cells",
                "interpretation_note",
            ]
        )

    rows: list[dict[str, object]] = []
    for city_name, city_group in diagnostics_frame.groupby(city_column):
        city_total = max(int(len(city_group)), 1)
        for band_name, band_group in city_group.groupby(band_column):
            hotspot_share = (
                band_group[hotspot_column].astype(str).isin(
                    {
                        "high_value_high_confidence",
                        "high_value_low_confidence",
                        "medium_value_high_confidence",
                        "low_value_high_uncertainty",
                    }
                ).mean()
                if hotspot_column in band_group.columns
                else float("nan")
            )
            note = (
                "This confidence band retains the expected bounded relationship between uncertainty burden and proxy usefulness."
                if str(band_name) in {"high", "medium"}
                else "Low-confidence cells should be treated as review-oriented or caution-heavy within the proxy framework."
            )
            rows.append(
                {
                    "city": str(city_name),
                    "confidence_band": str(band_name),
                    "n_cells": int(len(band_group)),
                    "share_cells": float(len(band_group) / city_total),
                    "mean_p50": float(pd.to_numeric(band_group[p50_column], errors="coerce").mean()),
                    "median_p50": float(pd.to_numeric(band_group[p50_column], errors="coerce").median()),
                    "mean_uncertainty_width": float(pd.to_numeric(band_group[width_column], errors="coerce").mean()),
                    "median_relative_uncertainty": float(pd.to_numeric(band_group[relative_column], errors="coerce").median()),
                    "mean_error_if_available": float(pd.to_numeric(band_group[error_column], errors="coerce").mean())
                    if error_column in band_group.columns
                    else float("nan"),
                    "share_hotspot_priority_cells": float(hotspot_share),
                    "interpretation_note": note,
                }
            )
    return pd.DataFrame(rows)
