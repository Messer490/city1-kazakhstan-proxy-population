from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.city1.training import (
    TrainingConfig,
    build_spatial_block_groups,
    sanitize_feature_frame_for_training,
    save_training_run,
    validation_protocol_slug,
)
from src.city1.labeling import WeakLabelConfig


class TrainingSanitizationTestCase(unittest.TestCase):
    def test_sanitize_feature_frame_clips_negative_features_and_drops_missing_coordinates(self) -> None:
        df = pd.DataFrame(
            {
                "latitude": [43.0, None],
                "longitude": [76.0, 77.0],
                "Building_Count": [1.0, -2.0],
                "Combined_Index": [0.5, -1.0],
            }
        )
        cleaned = sanitize_feature_frame_for_training(
            df,
            required_feature_columns=("Building_Count", "Combined_Index"),
        )
        self.assertEqual(len(cleaned), 1)
        self.assertEqual(float(cleaned.iloc[0]["Building_Count"]), 1.0)
        self.assertEqual(float(cleaned.iloc[0]["Combined_Index"]), 0.5)

    def test_build_spatial_block_groups_creates_multiple_blocks_within_city(self) -> None:
        df = pd.DataFrame(
            {
                "city_name": ["semey", "semey", "astana"],
                "latitude": [50.0, 50.03, 51.0],
                "longitude": [80.0, 80.03, 71.0],
            }
        )
        groups = build_spatial_block_groups(
            df,
            city_column="city_name",
            latitude_column="latitude",
            longitude_column="longitude",
            block_size_meters=2000,
        )
        self.assertEqual(len(groups), 3)
        self.assertNotEqual(str(groups.iloc[0]), str(groups.iloc[1]))
        self.assertTrue(str(groups.iloc[0]).startswith("semey__bx"))
        self.assertTrue(str(groups.iloc[2]).startswith("astana__bx"))

    def test_save_training_run_uses_protocol_specific_metric_names(self) -> None:
        class DummyResult:
            pass

        result = DummyResult()
        result.config = TrainingConfig(model_name="ridge", validation_protocol="spatial_block")
        result.label_config = WeakLabelConfig()
        result.final_estimator = object()
        result.training_frame = pd.DataFrame({"a": [1]})
        result.oof_predictions = pd.DataFrame({"city_name": ["semey"]})
        result.fold_metrics = pd.DataFrame(
            [
                {
                    "fold": 1,
                    "validation_protocol": "spatial_block",
                    "calibration_unit": "spatial_block",
                    "cities": "semey",
                    "validation_group_count": 1,
                    "rows": 1,
                    "raw_mae": 1.0,
                    "raw_rmse": 1.0,
                    "raw_r2": 1.0,
                    "calibrated_mae": 1.0,
                    "calibrated_rmse": 1.0,
                    "calibrated_r2": 1.0,
                }
            ]
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_paths = save_training_run(result, Path(tmp_dir))
            self.assertEqual(output_paths["metrics_path"].name, "ridge__spatial_block_fold_metrics.csv")
            self.assertEqual(output_paths["oof_path"].name, "ridge__spatial_block_oof_predictions.csv")
            self.assertEqual(output_paths["metadata_path"].name, "ridge__spatial_block_metadata.joblib")
            self.assertEqual(output_paths["artifact_path"].name, "ridge_model_v2.joblib")

    def test_validation_protocol_slug_normalizes_names(self) -> None:
        self.assertEqual(validation_protocol_slug("Leave One City Out"), "leave_one_city_out")


if __name__ == "__main__":
    unittest.main()
