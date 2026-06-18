from __future__ import annotations

import argparse
import platform
import subprocess
import sys
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Train the frozen City1 v3 uncertainty ensemble on the v2 random-forest core."
    )
    parser.add_argument(
        "--features-dir",
        type=str,
        required=True,
        help="Directory with feature CSV files, one city per file.",
    )
    parser.add_argument(
        "--totals-csv",
        type=str,
        default="data/external/city_population_reference_v2.csv",
        help="CSV with official city totals used for weak-target allocation and calibration context.",
    )
    parser.add_argument(
        "--city-registry-csv",
        type=str,
        default="data/external/city_status_registry_v2.csv",
        help="CSV with the frozen city registry snapshot source.",
    )
    parser.add_argument(
        "--output-root",
        type=str,
        default="models/v3_uncertainty",
        help="Root directory for v3 uncertainty model packages.",
    )
    parser.add_argument(
        "--run-id",
        type=str,
        default=None,
        help="Optional explicit run id. Defaults to city1_v3_rf500m_e{ensemble_size}_{UTC timestamp}.",
    )
    parser.add_argument(
        "--ensemble-size",
        type=int,
        default=30,
        help="Number of ensemble members to train for the frozen v3 package.",
    )
    parser.add_argument(
        "--random-state",
        type=int,
        default=42,
        help="Base random state used to derive deterministic ensemble seeds.",
    )
    parser.add_argument(
        "--rf-n-estimators",
        type=int,
        default=400,
        help="Number of trees per random-forest member.",
    )
    parser.add_argument(
        "--rf-min-samples-leaf",
        type=int,
        default=2,
        help="Minimum samples per leaf for each random-forest member.",
    )
    parser.add_argument(
        "--include-cities",
        nargs="*",
        default=None,
        help="Optional city subset for smoke or constrained runs, using display names or slugs.",
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Mark the run as a smoke package in the saved manifest.",
    )
    return parser


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _build_run_id(ensemble_size: int, explicit_run_id: str | None) -> str:
    if explicit_run_id:
        return explicit_run_id
    return f"city1_v3_rf500m_e{ensemble_size}_{_utc_timestamp()}"


def _git_commit(root: Path) -> str | None:
    try:
        return (
            subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                cwd=root,
                text=True,
                stderr=subprocess.DEVNULL,
            )
            .strip()
            or None
        )
    except Exception:
        return None


def _package_versions() -> dict[str, str]:
    packages = ("numpy", "pandas", "scikit-learn", "joblib", "geopandas")
    resolved: dict[str, str] = {}
    for package_name in packages:
        try:
            resolved[package_name] = version(package_name)
        except PackageNotFoundError:
            continue
    return resolved


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    from src.city1.contracts import CITY_OUTPUT_COLUMNS_V3, MODEL_VERSION_V3
    from src.city1.training import TrainingConfig, build_training_dataset
    from src.city1.city_totals import load_city_totals, normalize_city_name
    from src.city1.uncertainty import (
        UncertaintyConfig,
        resolve_ensemble_seeds,
        save_uncertainty_training_run,
        train_uncertainty_ensemble,
    )

    parser = build_parser()
    args = parser.parse_args()

    run_id = _build_run_id(args.ensemble_size, args.run_id)
    output_dir = root / args.output_root / run_id
    totals_path = root / args.totals_csv
    registry_path = root / args.city_registry_csv

    totals_lookup = load_city_totals(totals_path)
    training_config = TrainingConfig(
        model_name="random_forest",
        random_state=args.random_state,
        rf_n_estimators=args.rf_n_estimators,
        rf_min_samples_leaf=args.rf_min_samples_leaf,
    )
    allowed_cities = {normalize_city_name(city_name) for city_name in args.include_cities} if args.include_cities else None
    dataset = build_training_dataset(
        features_dir=root / args.features_dir,
        totals_lookup=totals_lookup,
        required_feature_columns=training_config.feature_columns,
        allowed_cities=allowed_cities,
    )
    uncertainty_config = UncertaintyConfig(ensemble_size=args.ensemble_size)
    result = train_uncertainty_ensemble(
        dataset.frame,
        training_config=training_config,
        uncertainty_config=uncertainty_config,
    )

    registry_snapshot = None
    if registry_path.exists():
        import pandas as pd

        registry_frame = pd.read_csv(registry_path)
        registry_frame["normalized_city_name"] = registry_frame["normalized_city_name"].astype(str).map(normalize_city_name)
        registry_snapshot = registry_frame.loc[
            registry_frame["normalized_city_name"].isin(set(dataset.included_cities))
        ].copy()

    training_summary = {
        "run_id": run_id,
        "model_version": MODEL_VERSION_V3,
        "ensemble_size": int(args.ensemble_size),
        "training_city_count": int(len(dataset.included_cities)),
        "training_row_count": int(len(dataset.frame)),
        "included_cities": ", ".join(dataset.included_cities),
        "skipped_file_count": int(len(dataset.skipped_files)),
        "warning_count": int(len(dataset.warnings)),
    }
    feature_schema = {
        "feature_columns": list(training_config.feature_columns),
        "cell_id_source_field": "Zone_ID",
        "canonical_output_fields": list(CITY_OUTPUT_COLUMNS_V3),
    }
    run_manifest = {
        "run_id": run_id,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": _git_commit(root),
        "python_version": platform.python_version(),
        "package_versions": _package_versions(),
        "feature_input_paths": sorted(str(path.relative_to(root)) for path in (root / args.features_dir).glob("*.csv")),
        "official_totals_path": str(totals_path.relative_to(root)),
        "city_registry_path": str(registry_path.relative_to(root)) if registry_path.exists() else None,
        "training_cities": list(dataset.included_cities),
        "ensemble_size": int(args.ensemble_size),
        "random_seeds": list(resolve_ensemble_seeds(args.random_state, args.ensemble_size)),
        "calibration_logic": "Official city totals anchor weak-target construction and remain mandatory in the frozen v3 path.",
        "known_limitations": [
            "Proxy, not truth: the ensemble expresses model/evidence uncertainty around a calibrated proxy surface.",
            "No city-specific external alignment scores are embedded at training time.",
            "District interval coverage is not part of the Phase 3 training artifact itself.",
        ],
        "smoke_flag": bool(args.smoke),
        "model_version": MODEL_VERSION_V3,
        "rf_n_estimators": int(args.rf_n_estimators),
        "rf_min_samples_leaf": int(args.rf_min_samples_leaf),
    }

    output_paths = save_uncertainty_training_run(
        result,
        output_dir,
        run_id=run_id,
        model_version=MODEL_VERSION_V3,
        official_totals_reference=str(totals_path.relative_to(root)),
        city_registry_reference=str(registry_path.relative_to(root)) if registry_path.exists() else None,
        feature_schema=feature_schema,
        training_summary=training_summary,
        city_registry_snapshot=registry_snapshot,
        run_manifest=run_manifest,
    )

    print("City1 v3 uncertainty training completed.")
    print(f"Run id: {run_id}")
    print(f"Rows: {len(dataset.frame)}")
    print(f"Included cities: {len(dataset.included_cities)}")
    print(f"Ensemble size: {len(result.members)}")
    print(f"Smoke run: {bool(args.smoke)}")
    print("Saved artifacts:")
    for name, path in output_paths.items():
        print(f"  - {name}: {path}")

    if dataset.warnings:
        print("Dataset warnings:")
        for warning in dataset.warnings[:20]:
            print(f"  - {warning}")


if __name__ == "__main__":
    main()
