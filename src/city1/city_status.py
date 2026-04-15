from __future__ import annotations

from pathlib import Path

import pandas as pd

from .city_totals import city_name_from_filename, normalize_city_name
from .paths import EXTERNAL_DATA_DIR, MODELS_DIR, PROCESSED_DATA_DIR, PROJECT_ROOT


DEFAULT_STATUS_CSV = EXTERNAL_DATA_DIR / "city_status_registry_v2.csv"
DEFAULT_TOTALS_CSV = EXTERNAL_DATA_DIR / "city_population_reference_v2.csv"
DEFAULT_FEATURES_DIR = PROCESSED_DATA_DIR / "features_v2_batch1"
DEFAULT_SMOKE_DIR = PROCESSED_DATA_DIR / "smoke_tests"
DEFAULT_INFERENCE_RUNS_DIR = PROCESSED_DATA_DIR / "inference_runs"
DEFAULT_QA_CITY_SUMMARY_CSV = PROJECT_ROOT / "reports" / "feature_qa_stage1_batch1" / "city_summary.csv"
DEFAULT_QA_FLAGS_CSV = PROJECT_ROOT / "reports" / "feature_qa_stage1_batch1" / "flags.csv"
DEFAULT_DISTRICT_BENCHMARK_DIR = PROJECT_ROOT / "reports" / "district_benchmark_v2"


BOOLEAN_COLUMNS: tuple[str, ...] = (
    "official_total_available",
    "feature_generated",
    "qa_passed",
    "included_in_training",
    "validated_batch",
    "smoke_passed",
    "saved_inference_example",
    "supported_for_calibrated_inference",
    "recommended_for_baseline_use",
)


def _normalize_optional_city(value: object) -> str | None:
    text = str(value).strip()
    if not text:
        return None
    normalized = normalize_city_name(text)
    return normalized or None


def _load_city_name_from_output_csv(path: Path) -> str | None:
    try:
        frame = pd.read_csv(path, nrows=1)
    except Exception:
        return None

    if "city_name" not in frame.columns or frame.empty:
        return None
    return _normalize_optional_city(frame.iloc[0]["city_name"])


def _boolify_series(series: pd.Series) -> pd.Series:
    return series.map(lambda value: str(value).strip().lower() in {"1", "true", "yes"})


def _load_status_frame(path: str | Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    for column in BOOLEAN_COLUMNS:
        if column in frame.columns:
            frame[column] = _boolify_series(frame[column]).astype(bool)
    return frame


def _default_training_oof_csv() -> Path:
    candidates = (
        MODELS_DIR / "trained_stage1_batch1" / "random_forest__leave_one_city_out_oof_predictions.csv",
        MODELS_DIR / "trained_stage1_batch1" / "random_forest_oof_predictions.csv",
    )
    for path in candidates:
        if path.exists():
            return path
    return candidates[0]


def build_city_status_registry(
    totals_csv: str | Path = DEFAULT_TOTALS_CSV,
    features_dir: str | Path = DEFAULT_FEATURES_DIR,
    qa_city_summary_csv: str | Path = DEFAULT_QA_CITY_SUMMARY_CSV,
    qa_flags_csv: str | Path = DEFAULT_QA_FLAGS_CSV,
    training_oof_csv: str | Path | None = None,
    smoke_dir: str | Path = DEFAULT_SMOKE_DIR,
    inference_runs_dir: str | Path = DEFAULT_INFERENCE_RUNS_DIR,
    district_benchmark_dir: str | Path = DEFAULT_DISTRICT_BENCHMARK_DIR,
) -> pd.DataFrame:
    totals_frame = pd.read_csv(totals_csv).copy()
    totals_frame["normalized_city_name"] = totals_frame["normalized_city_name"].map(normalize_city_name)
    totals_frame["official_total_available"] = True
    totals_frame["supported_for_calibrated_inference"] = True

    registry = totals_frame[
        [
            "city_name",
            "normalized_city_name",
            "country",
            "population",
            "reference_date",
            "verified",
            "official_total_available",
            "supported_for_calibrated_inference",
        ]
    ].copy()

    features_map: dict[str, dict[str, object]] = {}
    for path in sorted(Path(features_dir).glob("*.csv")):
        normalized = city_name_from_filename(path)
        try:
            row_count = int(len(pd.read_csv(path)))
        except Exception:
            row_count = 0
        features_map[normalized] = {
            "feature_generated": True,
            "feature_source_file": path.name,
            "feature_row_count": row_count,
        }

    qa_summary_map: dict[str, dict[str, object]] = {}
    city_summary_path = Path(qa_city_summary_csv)
    if city_summary_path.exists():
        city_summary = pd.read_csv(city_summary_path).copy()
        city_summary["normalized_city_name"] = city_summary["city_name"].map(normalize_city_name)
        for _, row in city_summary.iterrows():
            qa_summary_map[str(row["normalized_city_name"])] = {
                "qa_feature_city_rows": int(row.get("row_count", 0)),
                "qa_high_zero_share_feature_count": int(row.get("high_zero_share_feature_count", 0)),
            }

    qa_flag_map: dict[str, dict[str, int]] = {}
    qa_flags_path = Path(qa_flags_csv)
    if qa_flags_path.exists():
        flags = pd.read_csv(qa_flags_path).copy()
        if not flags.empty:
            flags["normalized_city_name"] = flags["city_name"].map(normalize_city_name)
            grouped = flags.groupby(["normalized_city_name", "severity"]).size().unstack(fill_value=0)
            for city_name, row in grouped.iterrows():
                qa_flag_map[str(city_name)] = {
                    "qa_error_count": int(row.get("error", 0)),
                    "qa_warning_count": int(row.get("warning", 0)),
                }

    training_cities: set[str] = set()
    training_oof_path = Path(training_oof_csv) if training_oof_csv is not None else _default_training_oof_csv()
    if training_oof_path.exists():
        oof_frame = pd.read_csv(training_oof_path, usecols=["city_name"])
        training_cities = {
            normalized
            for normalized in oof_frame["city_name"].map(_normalize_optional_city).dropna().tolist()
            if normalized
        }

    smoke_cities: set[str] = set()
    for path in sorted(Path(smoke_dir).glob("*.csv")):
        city_name = _load_city_name_from_output_csv(path)
        if city_name:
            smoke_cities.add(city_name)

    inference_cities: set[str] = set()
    for path in sorted(Path(inference_runs_dir).glob("*.csv")):
        city_name = _load_city_name_from_output_csv(path)
        if city_name:
            inference_cities.add(city_name)

    district_benchmark_map: dict[str, dict[str, object]] = {}
    for path in sorted(Path(district_benchmark_dir).glob("*/district_benchmark_metrics.csv")):
        try:
            frame = pd.read_csv(path)
        except Exception:
            continue
        if frame.empty or "city_name" not in frame.columns:
            continue
        normalized = _normalize_optional_city(frame.iloc[0]["city_name"])
        if not normalized:
            continue
        district_benchmark_map[normalized] = {
            "district_benchmark_completed": True,
            "district_benchmark_metrics_file": str(path.relative_to(PROJECT_ROOT)),
            "district_benchmark_reference_row_count": int(
                frame.iloc[0].get("district_reference_row_count", frame.iloc[0].get("district_count_total", 0))
            ),
            "district_benchmark_district_count_total": int(frame.iloc[0].get("district_count_total", 0)),
            "district_benchmark_district_count_compared": int(frame.iloc[0].get("district_count_compared", 0)),
            "district_benchmark_boundary_warning_count": int(frame.iloc[0].get("boundary_warning_count", 0)),
        }

    known_cities = set(registry["normalized_city_name"].tolist())
    known_cities.update(features_map.keys())
    known_cities.update(qa_summary_map.keys())
    known_cities.update(qa_flag_map.keys())
    known_cities.update(training_cities)
    known_cities.update(smoke_cities)
    known_cities.update(inference_cities)
    known_cities.update(district_benchmark_map.keys())

    existing = set(registry["normalized_city_name"].tolist())
    extra_rows: list[dict[str, object]] = []
    for normalized in sorted(known_cities.difference(existing)):
        extra_rows.append(
            {
                "city_name": normalized.title(),
                "normalized_city_name": normalized,
                "country": "Unknown",
                "population": pd.NA,
                "reference_date": pd.NA,
                "verified": False,
                "official_total_available": False,
                "supported_for_calibrated_inference": False,
            }
        )
    if extra_rows:
        registry = pd.concat([registry, pd.DataFrame(extra_rows)], ignore_index=True)

    registry["feature_generated"] = registry["normalized_city_name"].map(
        lambda city_name: bool(features_map.get(city_name, {}).get("feature_generated", False))
    )
    registry["feature_source_file"] = registry["normalized_city_name"].map(
        lambda city_name: features_map.get(city_name, {}).get("feature_source_file", "")
    )
    registry["feature_row_count"] = registry["normalized_city_name"].map(
        lambda city_name: int(features_map.get(city_name, {}).get("feature_row_count", 0))
    )

    registry["qa_feature_city_rows"] = registry["normalized_city_name"].map(
        lambda city_name: int(qa_summary_map.get(city_name, {}).get("qa_feature_city_rows", 0))
    )
    registry["qa_high_zero_share_feature_count"] = registry["normalized_city_name"].map(
        lambda city_name: int(qa_summary_map.get(city_name, {}).get("qa_high_zero_share_feature_count", 0))
    )
    registry["qa_error_count"] = registry["normalized_city_name"].map(
        lambda city_name: int(qa_flag_map.get(city_name, {}).get("qa_error_count", 0))
    )
    registry["qa_warning_count"] = registry["normalized_city_name"].map(
        lambda city_name: int(qa_flag_map.get(city_name, {}).get("qa_warning_count", 0))
    )

    registry["qa_passed"] = registry["feature_generated"] & (registry["qa_error_count"] == 0)
    registry["included_in_training"] = registry["normalized_city_name"].isin(training_cities)
    registry["validated_batch"] = registry["qa_passed"] & registry["included_in_training"]
    registry["smoke_passed"] = registry["normalized_city_name"].isin(smoke_cities)
    registry["saved_inference_example"] = registry["normalized_city_name"].isin(inference_cities)
    registry["recommended_for_baseline_use"] = registry["validated_batch"]
    registry["district_benchmark_completed"] = registry["normalized_city_name"].map(
        lambda city_name: bool(district_benchmark_map.get(city_name, {}).get("district_benchmark_completed", False))
    )
    registry["district_benchmark_reference_row_count"] = registry["normalized_city_name"].map(
        lambda city_name: int(district_benchmark_map.get(city_name, {}).get("district_benchmark_reference_row_count", 0))
    )
    registry["district_benchmark_district_count_total"] = registry["normalized_city_name"].map(
        lambda city_name: int(district_benchmark_map.get(city_name, {}).get("district_benchmark_district_count_total", 0))
    )
    registry["district_benchmark_district_count_compared"] = registry["normalized_city_name"].map(
        lambda city_name: int(district_benchmark_map.get(city_name, {}).get("district_benchmark_district_count_compared", 0))
    )
    registry["district_benchmark_boundary_warning_count"] = registry["normalized_city_name"].map(
        lambda city_name: int(district_benchmark_map.get(city_name, {}).get("district_benchmark_boundary_warning_count", 0))
    )
    registry["district_benchmark_metrics_file"] = registry["normalized_city_name"].map(
        lambda city_name: district_benchmark_map.get(city_name, {}).get("district_benchmark_metrics_file", "")
    )
    registry["district_benchmark_reference_available"] = registry["normalized_city_name"].map(
        lambda city_name: (Path("data/external/district_benchmark") / f"{city_name.replace(' ', '_')}_district_population_reference_v2.csv").exists()
    )
    registry["district_benchmark_quality"] = registry.apply(
        lambda row: (
            "full"
            if bool(row["district_benchmark_completed"])
            and int(row["district_benchmark_reference_row_count"]) > 0
            and int(row["district_benchmark_district_count_compared"]) == int(row["district_benchmark_reference_row_count"])
            and int(row["district_benchmark_boundary_warning_count"]) == 0
            else "partial"
            if bool(row["district_benchmark_completed"])
            else "none"
        ),
        axis=1,
    )

    def _status_label(row: pd.Series) -> str:
        if bool(row["validated_batch"]) and str(row["district_benchmark_quality"]) == "full":
            return "validated_district_benchmark"
        if bool(row["validated_batch"]) and str(row["district_benchmark_quality"]) == "partial":
            return "validated_partial_district_benchmark"
        if bool(row["validated_batch"]) and bool(row["smoke_passed"]):
            return "validated_smoke_passed"
        if bool(row["validated_batch"]):
            return "validated_batch"
        if bool(row["official_total_available"]) and bool(row["saved_inference_example"]):
            return "calibrated_runtime_only"
        if bool(row["official_total_available"]):
            return "official_total_only"
        if bool(row["feature_generated"]):
            return "feature_only"
        return "untracked"

    registry["status_label"] = registry.apply(_status_label, axis=1)
    registry["display_query"] = registry.apply(
        lambda row: f"{row['city_name']}, {row['country']}" if str(row.get("country", "")).strip() else str(row["city_name"]),
        axis=1,
    )

    ordered_columns = [
        "city_name",
        "normalized_city_name",
        "display_query",
        "country",
        "population",
        "reference_date",
        "verified",
        "official_total_available",
        "supported_for_calibrated_inference",
        "feature_generated",
        "feature_source_file",
        "feature_row_count",
        "qa_passed",
        "qa_error_count",
        "qa_warning_count",
        "qa_high_zero_share_feature_count",
        "included_in_training",
        "validated_batch",
        "smoke_passed",
        "saved_inference_example",
        "district_benchmark_reference_available",
        "district_benchmark_completed",
        "district_benchmark_quality",
        "district_benchmark_reference_row_count",
        "district_benchmark_district_count_total",
        "district_benchmark_district_count_compared",
        "district_benchmark_boundary_warning_count",
        "district_benchmark_metrics_file",
        "recommended_for_baseline_use",
        "status_label",
    ]

    registry = registry[ordered_columns].sort_values(
        ["recommended_for_baseline_use", "supported_for_calibrated_inference", "city_name"],
        ascending=[False, False, True],
    )
    return registry.reset_index(drop=True)


def load_city_status_registry(path: str | Path = DEFAULT_STATUS_CSV) -> pd.DataFrame:
    status_path = Path(path)
    if not status_path.exists():
        raise FileNotFoundError(f"City status registry not found: {status_path}")
    return _load_status_frame(status_path)
