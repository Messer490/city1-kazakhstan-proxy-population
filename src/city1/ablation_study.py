from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
import sys
from typing import Mapping

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from .city_totals import load_city_totals, normalize_city_name
from .contracts import MODEL_FEATURE_COLUMNS
from .inference import _build_output_frame, _predict_raw_population, load_model_artifact
from .paths import EXTERNAL_DATA_DIR, MODELS_DIR, PROCESSED_DATA_DIR, PROJECT_ROOT
from .training import (
    TrainingConfig,
    calibrate_predictions_by_city,
    run_training,
    save_training_run,
    validation_protocol_slug,
)


DEFAULT_CITY_SLUG_TO_PLACE_NAME: Mapping[str, str] = {
    "almaty": "Almaty, Kazakhstan",
    "astana": "Astana, Kazakhstan",
    "shymkent": "Shymkent, Kazakhstan",
}
DEFAULT_FEATURES_DIR = PROCESSED_DATA_DIR / "features_v2_batch1"
DEFAULT_FEATURE_GEOJSON_DIR = PROCESSED_DATA_DIR / "features_v2_batch1_geojson"
DEFAULT_TOTALS_CSV = EXTERNAL_DATA_DIR / "city_population_reference_v2.csv"
DEFAULT_MODELS_DIR = MODELS_DIR / "ablation_v2"
DEFAULT_REPORTS_DIR = PROJECT_ROOT / "reports" / "ablation_v2"
DEFAULT_EXTERNAL_BENCHMARK_PYTHON = Path(r"C:\Python310\python.exe")


@dataclass(frozen=True)
class AblationSpec:
    name: str
    description: str
    feature_columns: tuple[str, ...]
    non_full_priority: int

    @property
    def is_full(self) -> bool:
        return self.name == "full_features"


@dataclass(frozen=True)
class AblationStudyConfig:
    features_dir: Path = DEFAULT_FEATURES_DIR
    feature_geojson_dir: Path = DEFAULT_FEATURE_GEOJSON_DIR
    totals_csv: Path = DEFAULT_TOTALS_CSV
    models_root: Path = DEFAULT_MODELS_DIR
    reports_root: Path = DEFAULT_REPORTS_DIR
    city_slugs: tuple[str, ...] = ("almaty", "astana", "shymkent")
    city_slug_to_place_name: Mapping[str, str] | None = None
    external_benchmark_python: Path | None = None
    random_state: int = 42
    use_log_target: bool = True

    def __post_init__(self) -> None:
        if self.city_slug_to_place_name is None:
            object.__setattr__(self, "city_slug_to_place_name", DEFAULT_CITY_SLUG_TO_PLACE_NAME)


ABLATION_SPECS: tuple[AblationSpec, ...] = (
    AblationSpec("full_features", "All frozen City1 v2 model features.", MODEL_FEATURE_COLUMNS, 999),
    AblationSpec(
        "built_form_only",
        "Built form and morphology only, without Combined_Index.",
        (
            "Building_Count",
            "Building_Area",
            "Residential_Area",
            "Commercial_Area",
            "Retail_Area",
            "Public_Area",
            "Building_With_Levels_Count",
            "Mean_Building_Levels",
            "Total_Floor_Area",
        ),
        0,
    ),
    AblationSpec("transport_only", "Transport intensity only.", ("Road_Length", "Bus_Stop_Count"), 2),
    AblationSpec(
        "poi_services_only",
        "POI and service access only, without Combined_Index.",
        ("Park_Area", "Schools_Count", "Hospitals_Count", "Parks_Shops_Count", "POI_Access_Index"),
        1,
    ),
)


def get_ablation_specs() -> tuple[AblationSpec, ...]:
    return ABLATION_SPECS


def validate_ablation_specs(specs: tuple[AblationSpec, ...] | None = None) -> None:
    valid_columns = set(MODEL_FEATURE_COLUMNS)
    seen: set[str] = set()
    for spec in specs or ABLATION_SPECS:
        if spec.name in seen:
            raise ValueError(f"Duplicate ablation name: {spec.name}")
        seen.add(spec.name)
        missing = [column for column in spec.feature_columns if column not in valid_columns]
        if missing:
            raise ValueError(f"Ablation {spec.name} uses unknown feature columns: {missing}")
        if spec.is_full and "Combined_Index" not in spec.feature_columns:
            raise ValueError("full_features must include Combined_Index.")
        if not spec.is_full and "Combined_Index" in spec.feature_columns:
            raise ValueError(f"{spec.name} must not include Combined_Index.")


def _get_spec(spec_name: str) -> AblationSpec:
    for spec in ABLATION_SPECS:
        if spec.name == spec_name:
            return spec
    raise KeyError(f"Unknown ablation spec: {spec_name}")


def _frame_to_markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_No rows._"
    display = frame.copy()
    for column in display.columns:
        if pd.api.types.is_float_dtype(display[column]):
            display[column] = display[column].map(lambda value: "" if pd.isna(value) else f"{float(value):.6f}")
        else:
            display[column] = display[column].map(lambda value: "" if pd.isna(value) else str(value))
    headers = list(display.columns)
    rows = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for record in display.to_dict(orient="records"):
        rows.append("| " + " | ".join(record[column] for column in headers) + " |")
    return "\n".join(rows)


def summarize_ablation_metrics(spec: AblationSpec, fold_metrics: pd.DataFrame, *, validation_protocol: str) -> dict[str, object]:
    row = {
        "ablation_name": spec.name,
        "description": spec.description,
        "feature_count": int(len(spec.feature_columns)),
        "feature_columns": "|".join(spec.feature_columns),
        "validation_protocol": validation_protocol,
        "mean_raw_mae": float(fold_metrics["raw_mae"].mean()),
        "mean_raw_rmse": float(fold_metrics["raw_rmse"].mean()),
        "mean_raw_r2": float(fold_metrics["raw_r2"].mean()),
        "mean_calibrated_mae": float(fold_metrics["calibrated_mae"].mean()),
        "mean_calibrated_rmse": float(fold_metrics["calibrated_rmse"].mean()),
        "mean_calibrated_r2": float(fold_metrics["calibrated_r2"].mean()),
        "median_calibrated_rmse": float(fold_metrics["calibrated_rmse"].median()),
        "median_calibrated_r2": float(fold_metrics["calibrated_r2"].median()),
    }
    row["calibration_rmse_gain"] = float(row["mean_raw_rmse"] - row["mean_calibrated_rmse"])
    row["calibration_r2_gain"] = float(row["mean_calibrated_r2"] - row["mean_raw_r2"])
    return row


def choose_strongest_non_full_ablation(summary_df: pd.DataFrame) -> str:
    non_full = summary_df.loc[summary_df["ablation_name"] != "full_features"].copy()
    if non_full.empty:
        raise ValueError("No non-full ablations are available to rank.")
    priority_map = {spec.name: spec.non_full_priority for spec in ABLATION_SPECS}
    non_full["tie_priority"] = non_full["ablation_name"].map(priority_map).fillna(999).astype(int)
    ordered = non_full.sort_values(
        ["mean_calibrated_rmse", "mean_calibrated_r2", "tie_priority"],
        ascending=[True, False, True],
    ).reset_index(drop=True)
    return str(ordered.iloc[0]["ablation_name"])


def build_ablation_summary_frame(rows: list[dict[str, object]]) -> pd.DataFrame:
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    full_row = frame.loc[frame["ablation_name"] == "full_features"]
    if full_row.empty:
        raise ValueError("Ablation summary must include full_features.")
    full_rmse = float(full_row.iloc[0]["mean_calibrated_rmse"])
    full_r2 = float(full_row.iloc[0]["mean_calibrated_r2"])
    frame["delta_vs_full_calibrated_rmse"] = frame["mean_calibrated_rmse"] - full_rmse
    frame["delta_vs_full_calibrated_r2"] = frame["mean_calibrated_r2"] - full_r2
    frame["is_selected_non_full_winner"] = False
    winner = choose_strongest_non_full_ablation(frame)
    frame.loc[frame["ablation_name"] == winner, "is_selected_non_full_winner"] = True
    order_map = {spec.name: idx for idx, spec in enumerate(ABLATION_SPECS)}
    frame["display_order"] = frame["ablation_name"].map(order_map).fillna(999).astype(int)
    return frame.sort_values("display_order").reset_index(drop=True)


def _plot_ablation_summary(summary_df: pd.DataFrame, output_path: Path) -> None:
    if summary_df.empty:
        return
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    sns.barplot(data=summary_df, x="ablation_name", y="mean_calibrated_rmse", ax=axes[0], color="#2563eb")
    axes[0].set_title("LOCO Calibrated RMSE by Ablation")
    axes[0].set_xlabel("")
    axes[0].set_ylabel("Mean calibrated RMSE")
    axes[0].tick_params(axis="x", labelrotation=20)
    sns.barplot(data=summary_df, x="ablation_name", y="mean_calibrated_r2", ax=axes[1], color="#059669")
    axes[1].set_title("LOCO Calibrated R2 by Ablation")
    axes[1].set_xlabel("")
    axes[1].set_ylabel("Mean calibrated R2")
    axes[1].tick_params(axis="x", labelrotation=20)
    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def _build_training_config(spec: AblationSpec, *, validation_protocol: str, random_state: int, use_log_target: bool) -> TrainingConfig:
    return TrainingConfig(
        model_name="random_forest",
        feature_columns=spec.feature_columns,
        validation_protocol=validation_protocol,
        random_state=random_state,
        use_log_target=use_log_target,
    )


def _predict_from_saved_features(
    *,
    city_slug: str,
    place_name: str,
    model_artifact_path: Path,
    totals_csv: Path,
    feature_csv_dir: Path,
    feature_geojson_dir: Path,
    output_dir: Path,
) -> dict[str, Path]:
    import geopandas as gpd

    output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{city_slug}__random_forest"
    csv_path = output_dir / f"{stem}.csv"
    geojson_path = output_dir / f"{stem}.geojson"
    if csv_path.exists() and geojson_path.exists():
        return {"csv_path": csv_path, "geojson_path": geojson_path}

    feature_csv = feature_csv_dir / f"{city_slug}.csv"
    feature_geojson = feature_geojson_dir / f"{city_slug}.geojson"
    if not feature_csv.exists() or not feature_geojson.exists():
        raise FileNotFoundError(f"Missing saved features for city slug {city_slug}.")

    feature_frame = pd.read_csv(feature_csv)
    geometry_frame = gpd.read_file(feature_geojson)[["Zone_ID", "geometry"]]
    merged = feature_frame.merge(geometry_frame, on="Zone_ID", how="left", validate="one_to_one")
    if merged["geometry"].isna().any():
        raise ValueError(f"Missing geometry after joining feature CSV and GeoJSON for {city_slug}.")

    totals_lookup = load_city_totals(totals_csv)
    city_display_name = place_name.split(",")[0].strip()
    normalized_city_name = normalize_city_name(city_display_name)
    official_population = totals_lookup.get_population(normalized_city_name)
    if official_population is None:
        raise ValueError(f"No official population total found for {city_display_name}.")

    loaded_model = load_model_artifact(model_artifact_path)
    raw_prediction = _predict_raw_population(merged.drop(columns="geometry"), loaded_model)
    calibrated_prediction = calibrate_predictions_by_city(
        raw_prediction,
        groups=pd.Series(normalized_city_name, index=merged.index),
        official_totals=pd.Series(float(official_population), index=merged.index),
    )
    output_frame = _build_output_frame(
        feature_frame=merged.drop(columns="geometry"),
        raw_prediction=raw_prediction,
        calibrated_prediction=calibrated_prediction,
        place_name=place_name,
        model=loaded_model,
        official_population=int(official_population),
    )
    output_gdf = gpd.GeoDataFrame(output_frame.copy(), geometry=merged["geometry"], crs=geometry_frame.crs)
    output_frame.to_csv(csv_path, index=False)
    output_gdf.to_file(geojson_path, driver="GeoJSON")
    return {"csv_path": csv_path, "geojson_path": geojson_path}


def _current_python_has_rasterio() -> bool:
    try:
        import rasterio  # noqa: F401
    except ImportError:
        return False
    return True


def resolve_external_benchmark_python(python_override: str | Path | None = None) -> Path:
    if python_override:
        path = Path(python_override)
        if not path.exists():
            raise FileNotFoundError(f"Configured external benchmark Python was not found: {path}")
        return path
    if _current_python_has_rasterio():
        return Path(sys.executable)
    if DEFAULT_EXTERNAL_BENCHMARK_PYTHON.exists():
        return DEFAULT_EXTERNAL_BENCHMARK_PYTHON
    raise FileNotFoundError(
        "No Python interpreter with rasterio could be resolved. "
        "Pass --external-benchmark-python explicitly, or install rasterio in the active environment."
    )


def run_external_benchmark_for_inference_dir(
    *,
    inference_runs_dir: Path,
    output_dir: Path,
    city_slugs: tuple[str, ...],
    python_executable: Path,
) -> dict[str, object]:
    command = [
        str(python_executable),
        str(PROJECT_ROOT / "scripts" / "run_external_benchmark_v2.py"),
        "--output-dir",
        str(output_dir),
        "--inference-runs-dir",
        str(inference_runs_dir),
        "--city-slugs",
        *city_slugs,
    ]
    completed = subprocess.run(command, cwd=PROJECT_ROOT, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(
            "External benchmark subprocess failed.\n"
            f"Command: {' '.join(command)}\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    metrics_path = output_dir / "external_benchmark_metrics.csv"
    summary_path = output_dir / "external_benchmark_summary_by_source.csv"
    return {
        "command": " ".join(command),
        "metrics_path": metrics_path,
        "summary_path": summary_path,
        "metrics_df": pd.read_csv(metrics_path) if metrics_path.exists() else pd.DataFrame(),
        "summary_df": pd.read_csv(summary_path) if summary_path.exists() else pd.DataFrame(),
    }


def save_ablation_report(summary_df: pd.DataFrame, selected_extras_df: pd.DataFrame, output_dir: str | Path) -> dict[str, Path]:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    figures_dir = root / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    summary_csv = root / "ablation_summary.csv"
    selected_csv = root / "selected_extras_summary.csv"
    report_path = root / "ablation_report.md"
    figure_path = figures_dir / "figure_ablation_loco.png"

    summary_df.to_csv(summary_csv, index=False)
    selected_extras_df.to_csv(selected_csv, index=False)
    _plot_ablation_summary(summary_df, figure_path)

    winner_rows = summary_df.loc[summary_df["is_selected_non_full_winner"] == True, "ablation_name"]
    winner_name = str(winner_rows.iloc[0]) if not winner_rows.empty else "unknown"
    calibration_frame = summary_df[
        [
            "ablation_name",
            "mean_raw_rmse",
            "mean_calibrated_rmse",
            "mean_raw_r2",
            "mean_calibrated_r2",
            "calibration_rmse_gain",
            "calibration_r2_gain",
        ]
    ].copy()
    selected_spatial = selected_extras_df.loc[selected_extras_df["extra_type"] == "spatial_block"].copy()
    selected_external = selected_extras_df.loc[selected_extras_df["extra_type"] == "external_benchmark"].copy()

    lines = [
        "# Ablation Study Report v2",
        "",
        "This report compares frozen `City1 v2` feature-family ablations under `random_forest` and `LOCO`.",
        "",
        "## Winner Among Non-Full Ablations",
        "",
        f"- strongest non-full ablation: `{winner_name}`",
        "",
        "## LOCO Ablation Summary",
        "",
        _frame_to_markdown_table(
            summary_df[
                [
                    "ablation_name",
                    "feature_count",
                    "mean_calibrated_rmse",
                    "mean_calibrated_r2",
                    "delta_vs_full_calibrated_rmse",
                    "delta_vs_full_calibrated_r2",
                    "is_selected_non_full_winner",
                ]
            ]
        ),
        "",
        "## Calibration Effect",
        "",
        _frame_to_markdown_table(calibration_frame),
        "",
        "## Selected Extras: Spatial Block",
        "",
        _frame_to_markdown_table(selected_spatial),
        "",
        "## Selected Extras: External Benchmark",
        "",
        _frame_to_markdown_table(selected_external),
    ]
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return {
        "summary_csv_path": summary_csv,
        "selected_extras_csv_path": selected_csv,
        "report_path": report_path,
        "figure_path": figure_path,
    }


def _run_single_training(
    *,
    spec: AblationSpec,
    features_dir: Path,
    totals_csv: Path,
    output_dir: Path,
    validation_protocol: str,
    random_state: int,
    use_log_target: bool,
) -> tuple[pd.DataFrame, dict[str, Path]]:
    protocol_slug = validation_protocol_slug(validation_protocol)
    artifact_path = output_dir / "random_forest_model_v2.joblib"
    metrics_path = output_dir / f"random_forest__{protocol_slug}_fold_metrics.csv"
    oof_path = output_dir / f"random_forest__{protocol_slug}_oof_predictions.csv"
    metadata_path = output_dir / f"random_forest__{protocol_slug}_metadata.joblib"
    if artifact_path.exists() and metrics_path.exists() and oof_path.exists() and metadata_path.exists():
        return pd.read_csv(metrics_path), {
            "artifact_path": artifact_path,
            "metadata_path": metadata_path,
            "metrics_path": metrics_path,
            "oof_path": oof_path,
        }

    totals_lookup = load_city_totals(totals_csv)
    result = run_training(
        features_dir=features_dir,
        totals_lookup=totals_lookup,
        training_config=_build_training_config(
            spec,
            validation_protocol=validation_protocol,
            random_state=random_state,
            use_log_target=use_log_target,
        ),
    )
    return result.fold_metrics.copy(), save_training_run(result, output_dir)


def run_ablation_study(config: AblationStudyConfig | None = None) -> dict[str, object]:
    study_config = config or AblationStudyConfig()
    validate_ablation_specs()

    summary_rows: list[dict[str, object]] = []
    saved_paths: dict[str, dict[str, dict[str, Path]]] = {}

    for spec in ABLATION_SPECS:
        fold_metrics, saved = _run_single_training(
            spec=spec,
            features_dir=study_config.features_dir,
            totals_csv=study_config.totals_csv,
            output_dir=study_config.models_root / spec.name / "loco",
            validation_protocol="leave_one_city_out",
            random_state=study_config.random_state,
            use_log_target=study_config.use_log_target,
        )
        saved_paths.setdefault(spec.name, {})["loco"] = saved
        summary_rows.append(summarize_ablation_metrics(spec, fold_metrics, validation_protocol="leave_one_city_out"))

    summary_df = build_ablation_summary_frame(summary_rows)
    winner_name = choose_strongest_non_full_ablation(summary_df)
    selected_specs = [_get_spec("full_features"), _get_spec(winner_name)]
    external_python = resolve_external_benchmark_python(study_config.external_benchmark_python)
    selected_extra_rows: list[dict[str, object]] = []

    for spec in selected_specs:
        spatial_metrics, saved = _run_single_training(
            spec=spec,
            features_dir=study_config.features_dir,
            totals_csv=study_config.totals_csv,
            output_dir=study_config.models_root / spec.name / "spatial_block",
            validation_protocol="spatial_block",
            random_state=study_config.random_state,
            use_log_target=study_config.use_log_target,
        )
        saved_paths.setdefault(spec.name, {})["spatial_block"] = saved
        spatial_summary = summarize_ablation_metrics(spec, spatial_metrics, validation_protocol="spatial_block")
        selected_extra_rows.append(
            {
                "ablation_name": spec.name,
                "extra_type": "spatial_block",
                "benchmark_name": "",
                "mean_raw_rmse": spatial_summary["mean_raw_rmse"],
                "mean_calibrated_rmse": spatial_summary["mean_calibrated_rmse"],
                "mean_raw_r2": spatial_summary["mean_raw_r2"],
                "mean_calibrated_r2": spatial_summary["mean_calibrated_r2"],
                "top_decile_overlap": np.nan,
                "hotspot_iou": np.nan,
                "pearson_r": np.nan,
                "spearman_r": np.nan,
            }
        )

        inference_dir = study_config.reports_root / "selected_extras" / "external_benchmark_inputs" / spec.name
        artifact_path = saved_paths[spec.name]["loco"]["artifact_path"]
        for city_slug in study_config.city_slugs:
            _predict_from_saved_features(
                city_slug=city_slug,
                place_name=study_config.city_slug_to_place_name[city_slug],
                model_artifact_path=artifact_path,
                totals_csv=study_config.totals_csv,
                feature_csv_dir=study_config.features_dir,
                feature_geojson_dir=study_config.feature_geojson_dir,
                output_dir=inference_dir,
            )

        external_dir = study_config.reports_root / "selected_extras" / "external_benchmark" / spec.name
        summary_path = external_dir / "external_benchmark_summary_by_source.csv"
        metrics_path = external_dir / "external_benchmark_metrics.csv"
        if summary_path.exists() and metrics_path.exists():
            external_outputs = {
                "summary_df": pd.read_csv(summary_path),
                "metrics_df": pd.read_csv(metrics_path),
                "summary_path": summary_path,
                "metrics_path": metrics_path,
            }
        else:
            external_outputs = run_external_benchmark_for_inference_dir(
                inference_runs_dir=inference_dir,
                output_dir=external_dir,
                city_slugs=study_config.city_slugs,
                python_executable=external_python,
            )
        for row in external_outputs["summary_df"].to_dict(orient="records"):
            selected_extra_rows.append(
                {
                    "ablation_name": spec.name,
                    "extra_type": "external_benchmark",
                    "benchmark_name": row.get("benchmark_name", ""),
                    "mean_raw_rmse": np.nan,
                    "mean_calibrated_rmse": np.nan,
                    "mean_raw_r2": np.nan,
                    "mean_calibrated_r2": np.nan,
                    "top_decile_overlap": row.get("top_decile_overlap"),
                    "hotspot_iou": row.get("hotspot_iou"),
                    "pearson_r": row.get("pearson_r"),
                    "spearman_r": row.get("spearman_r"),
                }
            )

    selected_extras_df = pd.DataFrame(selected_extra_rows)
    outputs = save_ablation_report(summary_df, selected_extras_df, study_config.reports_root)
    return {
        "summary_df": summary_df,
        "selected_extras_df": selected_extras_df,
        "winner_name": winner_name,
        "saved_paths": saved_paths,
        **outputs,
    }


def build_report_only(*, summary_csv: str | Path, selected_extras_csv: str | Path, output_dir: str | Path) -> dict[str, Path]:
    return save_ablation_report(pd.read_csv(summary_csv), pd.read_csv(selected_extras_csv), output_dir)
