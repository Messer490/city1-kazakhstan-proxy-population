from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd

from .contracts import (
    CITY_FEATURE_COLUMNS,
    CITY_OUTPUT_COLUMNS,
    CITY_OUTPUT_COLUMNS_V3,
    HOTSPOT_PRIORITY_CLASSES_V3,
    MODEL_FEATURE_COLUMNS,
    UNCERTAINTY_OUTPUT_COLUMNS,
    missing_columns,
)


@dataclass(frozen=True)
class ValidationIssue:
    level: str
    code: str
    message: str
    affected_rows: int = 0


@dataclass(frozen=True)
class DatasetValidationReport:
    dataset_name: str
    row_count: int
    issues: tuple[ValidationIssue, ...]

    @property
    def has_errors(self) -> bool:
        return any(issue.level == "error" for issue in self.issues)

    def to_lines(self) -> list[str]:
        lines = [f"{self.dataset_name}: {self.row_count} rows"]
        if not self.issues:
            lines.append("  OK: no issues found")
            return lines

        for issue in self.issues:
            suffix = f" (rows={issue.affected_rows})" if issue.affected_rows else ""
            lines.append(f"  [{issue.level.upper()}] {issue.code}: {issue.message}{suffix}")
        return lines


def _numeric_columns(df: pd.DataFrame, columns: Iterable[str]) -> list[str]:
    numeric: list[str] = []
    for column in columns:
        if column in df.columns and pd.api.types.is_numeric_dtype(df[column]):
            numeric.append(column)
    return numeric


def _validate_dataset(
    df: pd.DataFrame,
    dataset_name: str,
    required_columns: Iterable[str],
    non_negative_columns: Iterable[str],
    require_population_column: bool,
    coordinate_columns: tuple[str, str] = ("latitude", "longitude"),
    id_column: str = "Zone_ID",
) -> DatasetValidationReport:
    issues: list[ValidationIssue] = []

    missing = missing_columns(df.columns, required_columns)
    if missing:
        issues.append(
            ValidationIssue(
                level="error",
                code="missing_columns",
                message=f"Missing required columns: {', '.join(missing)}",
            )
        )

    empty_row_mask = df.isna().all(axis=1)
    if int(empty_row_mask.sum()) > 0:
        issues.append(
            ValidationIssue(
                level="warning",
                code="empty_rows",
                message="Dataset contains fully empty rows.",
                affected_rows=int(empty_row_mask.sum()),
            )
        )

    coord_columns = [column for column in coordinate_columns if column in df.columns]
    if coord_columns:
        coord_missing = df[coord_columns].isna().any(axis=1)
        if int(coord_missing.sum()) > 0:
            issues.append(
                ValidationIssue(
                    level="error",
                    code="missing_coordinates",
                    message=f"Rows with missing {coordinate_columns[0]}/{coordinate_columns[1]} were found.",
                    affected_rows=int(coord_missing.sum()),
                )
            )

    if id_column in df.columns:
        zone_missing = int(df[id_column].isna().sum())
        if zone_missing > 0:
            issues.append(
                ValidationIssue(
                    level="error",
                    code="missing_zone_id",
                    message=f"Rows with missing {id_column} were found.",
                    affected_rows=zone_missing,
                )
            )

        duplicated_zone_ids = int(df[id_column].dropna().duplicated().sum())
        if duplicated_zone_ids > 0:
            issues.append(
                ValidationIssue(
                    level="error",
                    code="duplicate_zone_id",
                    message=f"Duplicate {id_column} values were found.",
                    affected_rows=duplicated_zone_ids,
                )
            )

    for column in _numeric_columns(df, non_negative_columns):
        negative_mask = df[column] < 0
        negative_count = int(negative_mask.sum())
        if negative_count > 0:
            issues.append(
                ValidationIssue(
                    level="error",
                    code="negative_values",
                    message=f"Column '{column}' contains negative values.",
                    affected_rows=negative_count,
                )
            )

    if require_population_column:
        population_column = None
        if "Population_Estimate_Final" in df.columns:
            population_column = "Population_Estimate_Final"
        elif "population_estimate_final" in df.columns:
            population_column = "population_estimate_final"
        elif "p50" in df.columns:
            population_column = "p50"

        if population_column is not None:
            non_positive_mask = pd.to_numeric(df[population_column], errors="coerce").fillna(0.0) <= 0
            non_positive_count = int(non_positive_mask.sum())
            if non_positive_count > 0:
                issues.append(
                    ValidationIssue(
                        level="warning",
                        code="non_positive_population",
                        message=f"{population_column} contains zero or negative values.",
                        affected_rows=non_positive_count,
                    )
                )

    return DatasetValidationReport(
        dataset_name=dataset_name,
        row_count=len(df),
        issues=tuple(issues),
    )


def validate_feature_output(
    df: pd.DataFrame,
    dataset_name: str,
    required_columns: Iterable[str] = CITY_FEATURE_COLUMNS,
    non_negative_columns: Iterable[str] = MODEL_FEATURE_COLUMNS,
) -> DatasetValidationReport:
    return _validate_dataset(
        df=df,
        dataset_name=dataset_name,
        required_columns=required_columns,
        non_negative_columns=non_negative_columns,
        require_population_column=False,
    )


def validate_city_output(
    df: pd.DataFrame,
    dataset_name: str,
    required_columns: Iterable[str] = CITY_OUTPUT_COLUMNS,
    non_negative_columns: Iterable[str] = MODEL_FEATURE_COLUMNS,
) -> DatasetValidationReport:
    return _validate_dataset(
        df=df,
        dataset_name=dataset_name,
        required_columns=required_columns,
        non_negative_columns=non_negative_columns,
        require_population_column=True,
    )


def validate_city_output_v3(
    df: pd.DataFrame,
    dataset_name: str,
    required_columns: Iterable[str] = CITY_OUTPUT_COLUMNS_V3,
    non_negative_columns: Iterable[str] = (
        "official_city_total",
        "calibrated_member_count",
        "p10",
        "p50",
        "p90",
        "population_estimate_final",
        "uncertainty_width",
        "relative_uncertainty",
        "model_stability_score",
        "osm_completeness_score",
        "osm_support_score",
        "external_agreement_score",
        "internal_support_score",
        "confidence_score",
        "hotspot_rank",
    ),
) -> DatasetValidationReport:
    report = _validate_dataset(
        df=df,
        dataset_name=dataset_name,
        required_columns=required_columns,
        non_negative_columns=non_negative_columns,
        require_population_column=True,
        coordinate_columns=("centroid_latitude", "centroid_longitude"),
        id_column="cell_id",
    )

    issues = list(report.issues)
    if "population_estimate_final" in df.columns:
        final_gap = (
            pd.to_numeric(df["population_estimate_final"], errors="coerce")
            - pd.to_numeric(df["p50"], errors="coerce")
        ).abs()
        invalid_final_alias = int((final_gap > 1e-9).fillna(False).sum())
        if invalid_final_alias > 0:
            issues.append(
                ValidationIssue(
                    level="error",
                    code="invalid_final_alias",
                    message="population_estimate_final must equal p50 for every row.",
                    affected_rows=invalid_final_alias,
                )
            )

    if "confidence_band" in df.columns:
        invalid_mask = ~df["confidence_band"].astype(str).isin({"high", "medium", "low"})
        invalid_count = int(invalid_mask.sum())
        if invalid_count > 0:
            issues.append(
                ValidationIssue(
                    level="error",
                    code="invalid_confidence_band",
                    message="confidence_band must be one of: high, medium, low.",
                    affected_rows=invalid_count,
                )
            )

    if "confidence_score" in df.columns and "confidence_band" in df.columns:
        score = pd.to_numeric(df["confidence_score"], errors="coerce").fillna(-1.0)
        expected = pd.Series("medium", index=df.index, dtype="object")
        expected.loc[score >= 0.70] = "high"
        expected.loc[score < 0.40] = "low"
        inconsistent = int((expected != df["confidence_band"].astype(str)).sum())
        if inconsistent > 0:
            issues.append(
                ValidationIssue(
                    level="error",
                    code="confidence_band_mismatch",
                    message="confidence_band does not match the frozen confidence_score thresholds.",
                    affected_rows=inconsistent,
                )
            )

    if "hotspot_priority_class" in df.columns:
        invalid_priority = ~df["hotspot_priority_class"].astype(str).isin(set(HOTSPOT_PRIORITY_CLASSES_V3))
        invalid_priority_count = int(invalid_priority.sum())
        if invalid_priority_count > 0:
            issues.append(
                ValidationIssue(
                    level="error",
                    code="invalid_hotspot_priority_class",
                    message="hotspot_priority_class is outside the frozen v3 vocabulary.",
                    affected_rows=invalid_priority_count,
                )
            )

    return DatasetValidationReport(
        dataset_name=report.dataset_name,
        row_count=report.row_count,
        issues=tuple(issues),
    )
