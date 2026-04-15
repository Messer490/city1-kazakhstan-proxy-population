from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.city1.ablation_study import (
    build_ablation_summary_frame,
    get_ablation_specs,
    save_ablation_report,
    validate_ablation_specs,
)
from src.city1.contracts import MODEL_FEATURE_COLUMNS


class AblationStudyTestCase(unittest.TestCase):
    def test_ablation_specs_reference_only_valid_columns_and_combined_index_only_in_full(self) -> None:
        validate_ablation_specs()
        valid = set(MODEL_FEATURE_COLUMNS)
        specs = get_ablation_specs()
        full_specs = [spec for spec in specs if spec.name == "full_features"]
        self.assertEqual(len(full_specs), 1)
        self.assertIn("Combined_Index", full_specs[0].feature_columns)
        for spec in specs:
            for column in spec.feature_columns:
                self.assertIn(column, valid)
            if spec.name != "full_features":
                self.assertNotIn("Combined_Index", spec.feature_columns)

    def test_build_ablation_summary_frame_selects_winner_deterministically(self) -> None:
        summary_df = build_ablation_summary_frame(
            [
                {
                    "ablation_name": "full_features",
                    "description": "full",
                    "feature_count": 17,
                    "feature_columns": "a|b",
                    "validation_protocol": "leave_one_city_out",
                    "mean_raw_mae": 10.0,
                    "mean_raw_rmse": 20.0,
                    "mean_raw_r2": 0.5,
                    "mean_calibrated_mae": 5.0,
                    "mean_calibrated_rmse": 10.0,
                    "mean_calibrated_r2": 0.9,
                    "median_calibrated_rmse": 10.0,
                    "median_calibrated_r2": 0.9,
                    "calibration_rmse_gain": 10.0,
                    "calibration_r2_gain": 0.4,
                },
                {
                    "ablation_name": "built_form_only",
                    "description": "built",
                    "feature_count": 9,
                    "feature_columns": "a|b",
                    "validation_protocol": "leave_one_city_out",
                    "mean_raw_mae": 12.0,
                    "mean_raw_rmse": 22.0,
                    "mean_raw_r2": 0.4,
                    "mean_calibrated_mae": 6.0,
                    "mean_calibrated_rmse": 11.0,
                    "mean_calibrated_r2": 0.8,
                    "median_calibrated_rmse": 11.0,
                    "median_calibrated_r2": 0.8,
                    "calibration_rmse_gain": 11.0,
                    "calibration_r2_gain": 0.4,
                },
                {
                    "ablation_name": "poi_services_only",
                    "description": "poi",
                    "feature_count": 5,
                    "feature_columns": "a|b",
                    "validation_protocol": "leave_one_city_out",
                    "mean_raw_mae": 12.0,
                    "mean_raw_rmse": 22.0,
                    "mean_raw_r2": 0.4,
                    "mean_calibrated_mae": 6.5,
                    "mean_calibrated_rmse": 11.0,
                    "mean_calibrated_r2": 0.8,
                    "median_calibrated_rmse": 11.0,
                    "median_calibrated_r2": 0.8,
                    "calibration_rmse_gain": 11.0,
                    "calibration_r2_gain": 0.4,
                },
                {
                    "ablation_name": "transport_only",
                    "description": "transport",
                    "feature_count": 2,
                    "feature_columns": "a|b",
                    "validation_protocol": "leave_one_city_out",
                    "mean_raw_mae": 13.0,
                    "mean_raw_rmse": 23.0,
                    "mean_raw_r2": 0.3,
                    "mean_calibrated_mae": 7.0,
                    "mean_calibrated_rmse": 11.0,
                    "mean_calibrated_r2": 0.8,
                    "median_calibrated_rmse": 11.0,
                    "median_calibrated_r2": 0.8,
                    "calibration_rmse_gain": 12.0,
                    "calibration_r2_gain": 0.5,
                },
            ]
        )
        winner_rows = summary_df.loc[summary_df["is_selected_non_full_winner"] == True, "ablation_name"].tolist()
        self.assertEqual(winner_rows, ["built_form_only"])

    def test_save_ablation_report_writes_outputs(self) -> None:
        summary_df = pd.DataFrame(
            [
                {
                    "ablation_name": "full_features",
                    "description": "full",
                    "feature_count": 17,
                    "feature_columns": "a|b",
                    "validation_protocol": "leave_one_city_out",
                    "mean_raw_mae": 10.0,
                    "mean_raw_rmse": 20.0,
                    "mean_raw_r2": 0.5,
                    "mean_calibrated_mae": 5.0,
                    "mean_calibrated_rmse": 10.0,
                    "mean_calibrated_r2": 0.9,
                    "median_calibrated_rmse": 10.0,
                    "median_calibrated_r2": 0.9,
                    "calibration_rmse_gain": 10.0,
                    "calibration_r2_gain": 0.4,
                    "delta_vs_full_calibrated_rmse": 0.0,
                    "delta_vs_full_calibrated_r2": 0.0,
                    "is_selected_non_full_winner": False,
                    "display_order": 0,
                },
                {
                    "ablation_name": "built_form_only",
                    "description": "built",
                    "feature_count": 9,
                    "feature_columns": "a|b",
                    "validation_protocol": "leave_one_city_out",
                    "mean_raw_mae": 12.0,
                    "mean_raw_rmse": 22.0,
                    "mean_raw_r2": 0.4,
                    "mean_calibrated_mae": 6.0,
                    "mean_calibrated_rmse": 11.0,
                    "mean_calibrated_r2": 0.8,
                    "median_calibrated_rmse": 11.0,
                    "median_calibrated_r2": 0.8,
                    "calibration_rmse_gain": 11.0,
                    "calibration_r2_gain": 0.4,
                    "delta_vs_full_calibrated_rmse": 1.0,
                    "delta_vs_full_calibrated_r2": -0.1,
                    "is_selected_non_full_winner": True,
                    "display_order": 1,
                },
            ]
        )
        selected_extras_df = pd.DataFrame(
            [
                {
                    "ablation_name": "full_features",
                    "extra_type": "spatial_block",
                    "benchmark_name": "",
                    "mean_raw_rmse": 18.0,
                    "mean_calibrated_rmse": 9.0,
                    "mean_raw_r2": 0.6,
                    "mean_calibrated_r2": 0.95,
                    "top_decile_overlap": None,
                    "hotspot_iou": None,
                    "pearson_r": None,
                    "spearman_r": None,
                }
            ]
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            outputs = save_ablation_report(summary_df, selected_extras_df, Path(tmp_dir) / "report")
            self.assertTrue(outputs["summary_csv_path"].exists())
            self.assertTrue(outputs["selected_extras_csv_path"].exists())
            self.assertTrue(outputs["report_path"].exists())
            self.assertTrue(outputs["figure_path"].exists())

    def test_cli_report_only_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            summary_csv = root / "summary.csv"
            selected_csv = root / "selected.csv"
            pd.DataFrame(
                [
                    {
                        "ablation_name": "full_features",
                        "description": "full",
                        "feature_count": 17,
                        "feature_columns": "a|b",
                        "validation_protocol": "leave_one_city_out",
                        "mean_raw_mae": 10.0,
                        "mean_raw_rmse": 20.0,
                        "mean_raw_r2": 0.5,
                        "mean_calibrated_mae": 5.0,
                        "mean_calibrated_rmse": 10.0,
                        "mean_calibrated_r2": 0.9,
                        "median_calibrated_rmse": 10.0,
                        "median_calibrated_r2": 0.9,
                        "calibration_rmse_gain": 10.0,
                        "calibration_r2_gain": 0.4,
                        "delta_vs_full_calibrated_rmse": 0.0,
                        "delta_vs_full_calibrated_r2": 0.0,
                        "is_selected_non_full_winner": False,
                        "display_order": 0,
                    },
                    {
                        "ablation_name": "built_form_only",
                        "description": "built",
                        "feature_count": 9,
                        "feature_columns": "a|b",
                        "validation_protocol": "leave_one_city_out",
                        "mean_raw_mae": 12.0,
                        "mean_raw_rmse": 22.0,
                        "mean_raw_r2": 0.4,
                        "mean_calibrated_mae": 6.0,
                        "mean_calibrated_rmse": 11.0,
                        "mean_calibrated_r2": 0.8,
                        "median_calibrated_rmse": 11.0,
                        "median_calibrated_r2": 0.8,
                        "calibration_rmse_gain": 11.0,
                        "calibration_r2_gain": 0.4,
                        "delta_vs_full_calibrated_rmse": 1.0,
                        "delta_vs_full_calibrated_r2": -0.1,
                        "is_selected_non_full_winner": True,
                        "display_order": 1,
                    },
                ]
            ).to_csv(summary_csv, index=False)
            pd.DataFrame(
                [
                    {
                        "ablation_name": "full_features",
                        "extra_type": "spatial_block",
                        "benchmark_name": "",
                        "mean_raw_rmse": 18.0,
                        "mean_calibrated_rmse": 9.0,
                        "mean_raw_r2": 0.6,
                        "mean_calibrated_r2": 0.95,
                        "top_decile_overlap": None,
                        "hotspot_iou": None,
                        "pearson_r": None,
                        "spearman_r": None,
                    }
                ]
            ).to_csv(selected_csv, index=False)
            output_dir = root / "report"
            script = Path.cwd() / "scripts" / "run_ablation_study_v2.py"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(script),
                    "--reports-root",
                    str(output_dir),
                    "--report-only-summary-csv",
                    str(summary_csv),
                    "--report-only-selected-extras-csv",
                    str(selected_csv),
                ],
                capture_output=True,
                text=True,
                check=False,
                cwd=Path.cwd(),
            )
            self.assertEqual(completed.returncode, 0, msg=completed.stderr)
            self.assertTrue((output_dir / "ablation_report.md").exists())


if __name__ == "__main__":
    unittest.main()
