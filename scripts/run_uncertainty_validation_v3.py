from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run City1 v3 uncertainty diagnostics from a frozen features batch.")
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
        help="CSV with official city totals.",
    )
    parser.add_argument(
        "--output-root",
        type=str,
        default="reports/uncertainty_validation_v3",
        help="Root directory for uncertainty validation artifacts.",
    )
    parser.add_argument(
        "--run-id",
        type=str,
        required=True,
        help="Frozen run id used to place outputs under reports/uncertainty_validation_v3/<run_id>/.",
    )
    parser.add_argument(
        "--ensemble-size",
        type=int,
        default=9,
        help="Number of ensemble members to use in each validation fold.",
    )
    return parser


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    from src.city1.city_totals import load_city_totals
    from src.city1.training import TrainingConfig, build_training_dataset
    from src.city1.uncertainty import UncertaintyConfig
    from src.city1.uncertainty_validation import (
        compute_error_uncertainty_monotonicity,
        cross_validate_uncertainty_by_city,
    )

    parser = build_parser()
    args = parser.parse_args()

    totals_lookup = load_city_totals(root / args.totals_csv)
    training_config = TrainingConfig(model_name="random_forest")
    dataset = build_training_dataset(
        features_dir=root / args.features_dir,
        totals_lookup=totals_lookup,
        required_feature_columns=training_config.feature_columns,
    )
    diagnostics, fold_metrics = cross_validate_uncertainty_by_city(
        dataset.frame,
        training_config=training_config,
        uncertainty_config=UncertaintyConfig(ensemble_size=args.ensemble_size),
    )
    monotonicity, metrics = compute_error_uncertainty_monotonicity(diagnostics)

    output_dir = root / args.output_root / args.run_id
    output_dir.mkdir(parents=True, exist_ok=True)
    diagnostics_path = output_dir / "uncertainty_diagnostics.csv"
    fold_path = output_dir / "uncertainty_fold_metrics.csv"
    monotonicity_path = output_dir / "uncertainty_monotonicity.csv"
    metrics_path = output_dir / "uncertainty_monotonicity_metrics.json"
    manifest_path = output_dir / "run_manifest.json"

    diagnostics.to_csv(diagnostics_path, index=False)
    fold_metrics.to_csv(fold_path, index=False)
    monotonicity.to_csv(monotonicity_path, index=False)
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    manifest_path.write_text(
        json.dumps(
            {
                "run_id": args.run_id,
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
                "feature_dir": args.features_dir,
                "totals_csv": args.totals_csv,
                "ensemble_size": int(args.ensemble_size),
                "generated_files": [
                    diagnostics_path.name,
                    fold_path.name,
                    monotonicity_path.name,
                    metrics_path.name,
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print("City1 v3 uncertainty validation completed.")
    print(f"Run id: {args.run_id}")
    print(f"Diagnostics: {diagnostics_path}")
    print(f"Fold metrics: {fold_path}")
    print(f"Monotonicity table: {monotonicity_path}")
    print(f"Monotonicity metrics: {metrics_path}")


if __name__ == "__main__":
    main()
