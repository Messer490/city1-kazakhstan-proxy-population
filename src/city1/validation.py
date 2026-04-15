from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd

from .contracts import CITY_FEATURE_COLUMNS, CITY_OUTPUT_COLUMNS, MODEL_FEATURE_COLUMNS, missing_columns


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

    coord_columns = [column for column in ("latitude", "longitude") if column in df.columns]
    if coord_columns:
        coord_missing = df[coord_columns].isna().any(axis=1)
        if int(coord_missing.sum()) > 0:
            issues.append(
                ValidationIssue(
                    level="error",
                    code="missing_coordinates",
                    message="Rows with missing latitude/longitude were found.",
                    affected_rows=int(coord_missing.sum()),
                )
            )

    if "Zone_ID" in df.columns:
        zone_missing = int(df["Zone_ID"].isna().sum())
        if zone_missing > 0:
            issues.append(
                ValidationIssue(
                    level="error",
                    code="missing_zone_id",
                    message="Rows with missing Zone_ID were found.",
                    affected_rows=zone_missing,
                )
            )

        duplicated_zone_ids = int(df["Zone_ID"].dropna().duplicated().sum())
        if duplicated_zone_ids > 0:
            issues.append(
                ValidationIssue(
                    level="error",
                    code="duplicate_zone_id",
                    message="Duplicate Zone_ID values were found.",
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

    if require_population_column and "Population_Estimate_Final" in df.columns:
        non_positive_mask = df["Population_Estimate_Final"] <= 0
        non_positive_count = int(non_positive_mask.sum())
        if non_positive_count > 0:
            issues.append(
                ValidationIssue(
                    level="warning",
                    code="non_positive_population",
                    message="Population_Estimate_Final contains zero or negative values.",
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
