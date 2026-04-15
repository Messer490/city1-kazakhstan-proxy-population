from __future__ import annotations

import argparse
import sys
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train City1 v2 model with weak supervision.")
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
        help="CSV with cleaned city population reference totals.",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="ridge",
        help="Model name: ridge, random_forest, or catboost.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="models/trained",
        help="Directory to store training artifacts.",
    )
    parser.add_argument(
        "--validation-protocol",
        type=str,
        default="leave_one_city_out",
        help="Validation protocol: leave_one_city_out or spatial_block.",
    )
    parser.add_argument(
        "--spatial-block-size-meters",
        type=int,
        default=2000,
        help="Approximate spatial block size in meters for spatial_block validation.",
    )
    parser.add_argument(
        "--spatial-block-splits",
        type=int,
        default=5,
        help="Number of GroupKFold splits for spatial_block validation.",
    )
    return parser


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    from src.city1.city_totals import load_city_totals
    from src.city1.training import TrainingConfig, run_training, save_training_run

    parser = build_parser()
    args = parser.parse_args()

    totals_lookup = load_city_totals(root / args.totals_csv)
    result = run_training(
        features_dir=root / args.features_dir,
        totals_lookup=totals_lookup,
        training_config=TrainingConfig(
            model_name=args.model,
            validation_protocol=args.validation_protocol,
            spatial_block_size_meters=args.spatial_block_size_meters,
            spatial_block_splits=args.spatial_block_splits,
        ),
    )
    output_paths = save_training_run(result, root / args.output_dir)

    print("Training completed.")
    print(f"Rows: {len(result.training_frame)}")
    print(f"Cities: {result.training_frame['city_name'].nunique()}")
    print(f"Validation protocol: {result.config.validation_protocol}")
    print("Fold metrics:")
    print(result.fold_metrics.to_string(index=False))
    print("Saved artifacts:")
    for name, path in output_paths.items():
        print(f"  - {name}: {path}")

    if totals_lookup.warnings:
        print("City total parsing warnings:")
        for warning in totals_lookup.warnings[:20]:
            print(f"  - {warning}")


if __name__ == "__main__":
    main()
