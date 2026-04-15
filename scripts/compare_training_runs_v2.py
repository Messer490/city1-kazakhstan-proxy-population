from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compare City1 v2 training runs from fold-metrics CSV files.")
    parser.add_argument(
        "--metrics-dir",
        type=str,
        required=True,
        help="Directory with *_fold_metrics.csv files.",
    )
    parser.add_argument(
        "--output-csv",
        type=str,
        default=None,
        help="Optional path to save the aggregated model comparison CSV.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    metrics_dir = Path(args.metrics_dir)
    metric_files = sorted(metrics_dir.glob("*_fold_metrics.csv"))
    if not metric_files:
        raise ValueError(f"No fold metric files were found in {metrics_dir}")

    rows: list[dict[str, object]] = []
    for path in metric_files:
        frame = pd.read_csv(path)
        metric_stem = path.name.replace("_fold_metrics.csv", "")
        if "__" in metric_stem:
            model_name, validation_protocol = metric_stem.split("__", 1)
        else:
            model_name, validation_protocol = metric_stem, "leave_one_city_out"
        rows.append(
            {
                "model_name": model_name,
                "validation_protocol": validation_protocol,
                "folds": int(len(frame)),
                "mean_raw_mae": float(frame["raw_mae"].mean()),
                "mean_raw_rmse": float(frame["raw_rmse"].mean()),
                "mean_raw_r2": float(frame["raw_r2"].mean()),
                "mean_calibrated_mae": float(frame["calibrated_mae"].mean()),
                "mean_calibrated_rmse": float(frame["calibrated_rmse"].mean()),
                "mean_calibrated_r2": float(frame["calibrated_r2"].mean()),
                "median_calibrated_rmse": float(frame["calibrated_rmse"].median()),
                "median_calibrated_r2": float(frame["calibrated_r2"].median()),
            }
        )

    comparison = pd.DataFrame(rows).sort_values(
        ["validation_protocol", "mean_calibrated_rmse", "mean_calibrated_mae"],
        ascending=[True, True, True],
    ).reset_index(drop=True)

    if args.output_csv:
        output_path = Path(args.output_csv)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        comparison.to_csv(output_path, index=False)
        print(f"Saved comparison: {output_path}")

    print(comparison.to_string(index=False))


if __name__ == "__main__":
    main()
