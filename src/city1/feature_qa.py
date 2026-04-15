from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .contracts import MODEL_FEATURE_COLUMNS


KEY_SCALE_COLUMNS: tuple[str, ...] = (
    "Building_Area",
    "Road_Length",
    "Total_Floor_Area",
    "POI_Access_Index",
    "Combined_Index",
)
CRITICAL_CITYWIDE_ZERO_COLUMNS: tuple[str, ...] = (
    "Road_Length",
    "POI_Access_Index",
)


@dataclass(frozen=True)
class FeatureQABundle:
    city_summary: pd.DataFrame
    feature_summary: pd.DataFrame
    flags: pd.DataFrame


def discover_feature_csvs(features_dir: str | Path) -> list[Path]:
    return sorted(Path(features_dir).glob("*.csv"))


def _coerce_numeric(frame: pd.DataFrame, columns: tuple[str, ...]) -> pd.DataFrame:
    converted = frame.copy()
    for column in columns:
        if column in converted.columns:
            converted[column] = pd.to_numeric(converted[column], errors="coerce")
    return converted


def _safe_quantile(series: pd.Series, q: float) -> float:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    if clean.empty:
        return float("nan")
    return float(clean.quantile(q))


def qa_city_frame(
    frame: pd.DataFrame,
    city_name: str,
) -> tuple[dict[str, object], list[dict[str, object]], list[dict[str, object]]]:
    numeric_frame = _coerce_numeric(frame, MODEL_FEATURE_COLUMNS)
    row_count = int(len(frame))

    negative_feature_count = 0
    missing_feature_columns = [column for column in MODEL_FEATURE_COLUMNS if column not in frame.columns]
    constant_feature_count = 0
    highly_sparse_feature_count = 0
    feature_rows: list[dict[str, object]] = []
    flags: list[dict[str, object]] = []

    for column in MODEL_FEATURE_COLUMNS:
        if column not in numeric_frame.columns:
            flags.append(
                {
                    "city_name": city_name,
                    "severity": "error",
                    "column": column,
                    "issue": "missing_feature_column",
                    "details": "Column is absent from the generated feature dataset.",
                }
            )
            continue

        series = pd.to_numeric(numeric_frame[column], errors="coerce")
        non_null = series.dropna()
        negative_count = int((non_null < 0).sum())
        zero_share = float((non_null == 0).mean()) if not non_null.empty else float("nan")
        unique_count = int(non_null.nunique())

        if negative_count > 0:
            negative_feature_count += negative_count
            flags.append(
                {
                    "city_name": city_name,
                    "severity": "error",
                    "column": column,
                    "issue": "negative_values",
                    "details": f"Found {negative_count} negative values.",
                }
            )

        if unique_count <= 1 and row_count > 1:
            constant_feature_count += 1
            flags.append(
                {
                    "city_name": city_name,
                    "severity": "warning",
                    "column": column,
                    "issue": "constant_feature",
                    "details": "Feature has one unique numeric value across the city.",
                }
            )

        if zero_share == zero_share and zero_share >= 0.98:
            highly_sparse_feature_count += 1
            flags.append(
                {
                    "city_name": city_name,
                    "severity": "warning",
                    "column": column,
                    "issue": "extreme_zero_share",
                    "details": f"Zero share is {zero_share:.3f}.",
                }
            )

        if column in CRITICAL_CITYWIDE_ZERO_COLUMNS and unique_count == 1 and not non_null.empty:
            unique_value = float(non_null.iloc[0])
            if unique_value == 0.0:
                flags.append(
                    {
                        "city_name": city_name,
                        "severity": "error",
                        "column": column,
                        "issue": "citywide_zero_critical_feature",
                        "details": "Critical feature collapsed to zero across the whole city.",
                    }
                )

        feature_rows.append(
            {
                "city_name": city_name,
                "column": column,
                "count": int(non_null.shape[0]),
                "mean": float(non_null.mean()) if not non_null.empty else float("nan"),
                "median": float(non_null.median()) if not non_null.empty else float("nan"),
                "p95": _safe_quantile(non_null, 0.95),
                "max": float(non_null.max()) if not non_null.empty else float("nan"),
                "zero_share": zero_share,
                "unique_count": unique_count,
            }
        )

    if row_count == 0:
        flags.append(
            {
                "city_name": city_name,
                "severity": "error",
                "column": "",
                "issue": "empty_dataset",
                "details": "Feature CSV contains zero rows.",
            }
        )

    null_lat = int(frame["latitude"].isna().sum()) if "latitude" in frame.columns else row_count
    null_lon = int(frame["longitude"].isna().sum()) if "longitude" in frame.columns else row_count
    duplicate_zone_ids = int(frame["Zone_ID"].duplicated().sum()) if "Zone_ID" in frame.columns else row_count

    if null_lat or null_lon:
        flags.append(
            {
                "city_name": city_name,
                "severity": "error",
                "column": "latitude/longitude",
                "issue": "missing_coordinates",
                "details": f"latitude NaN={null_lat}, longitude NaN={null_lon}.",
            }
        )

    if duplicate_zone_ids:
        flags.append(
            {
                "city_name": city_name,
                "severity": "error",
                "column": "Zone_ID",
                "issue": "duplicate_zone_ids",
                "details": f"Found {duplicate_zone_ids} duplicated Zone_ID values.",
            }
        )

    city_summary = {
        "city_name": city_name,
        "row_count": row_count,
        "missing_feature_columns": len(missing_feature_columns),
        "negative_feature_values": negative_feature_count,
        "constant_feature_count": constant_feature_count,
        "high_zero_share_feature_count": highly_sparse_feature_count,
        "null_latitude": null_lat,
        "null_longitude": null_lon,
        "duplicate_zone_ids": duplicate_zone_ids,
        "building_area_zero_share": float((numeric_frame["Building_Area"] == 0).mean())
        if "Building_Area" in numeric_frame.columns and row_count
        else float("nan"),
        "road_length_zero_share": float((numeric_frame["Road_Length"] == 0).mean())
        if "Road_Length" in numeric_frame.columns and row_count
        else float("nan"),
        "total_floor_area_zero_share": float((numeric_frame["Total_Floor_Area"] == 0).mean())
        if "Total_Floor_Area" in numeric_frame.columns and row_count
        else float("nan"),
    }

    return city_summary, feature_rows, flags


def qa_single_city(path: str | Path) -> tuple[dict[str, object], list[dict[str, object]], list[dict[str, object]]]:
    city_name = Path(path).stem
    frame = pd.read_csv(path)
    return qa_city_frame(frame, city_name=city_name)


def run_feature_qa(features_dir: str | Path) -> FeatureQABundle:
    feature_files = discover_feature_csvs(features_dir)
    if not feature_files:
        raise ValueError(f"No feature CSV files found in {features_dir}")

    city_rows: list[dict[str, object]] = []
    feature_rows: list[dict[str, object]] = []
    flag_rows: list[dict[str, object]] = []

    for path in feature_files:
        city_summary, city_feature_rows, city_flags = qa_single_city(path)
        city_rows.append(city_summary)
        feature_rows.extend(city_feature_rows)
        flag_rows.extend(city_flags)

    city_summary_frame = pd.DataFrame(city_rows).sort_values("city_name").reset_index(drop=True)
    feature_summary_frame = pd.DataFrame(feature_rows).sort_values(["city_name", "column"]).reset_index(drop=True)
    flags_frame = pd.DataFrame(flag_rows)
    if flags_frame.empty:
        flags_frame = pd.DataFrame(columns=["city_name", "severity", "column", "issue", "details"])
    else:
        flags_frame = flags_frame.sort_values(["severity", "city_name", "column", "issue"]).reset_index(drop=True)

    return FeatureQABundle(
        city_summary=city_summary_frame,
        feature_summary=feature_summary_frame,
        flags=flags_frame,
    )


def summarize_feature_qa(bundle: FeatureQABundle) -> list[str]:
    city_summary = bundle.city_summary
    flags = bundle.flags
    lines = [f"QA cities: {len(city_summary)}"]

    if not city_summary.empty:
        lines.append(f"Total rows: {int(city_summary['row_count'].sum())}")
        lines.append(
            "Cities with hard errors: "
            f"{int(flags.loc[flags['severity'] == 'error', 'city_name'].nunique()) if not flags.empty else 0}"
        )

    error_count = int((flags["severity"] == "error").sum()) if not flags.empty else 0
    warning_count = int((flags["severity"] == "warning").sum()) if not flags.empty else 0
    lines.append(f"QA errors: {error_count}")
    lines.append(f"QA warnings: {warning_count}")

    for column in KEY_SCALE_COLUMNS:
        subset = bundle.feature_summary.loc[bundle.feature_summary["column"] == column]
        if subset.empty:
            continue
        lines.append(
            f"{column}: median(mean)={subset['median'].median():.3f}, "
            f"median(p95)={subset['p95'].median():.3f}, "
            f"median(max)={subset['max'].median():.3f}"
        )

    return lines
