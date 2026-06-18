from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.city1.training import TrainingConfig
from src.city1.uncertainty import (
    LoadedUncertaintyArtifact,
    UncertaintyConfig,
    align_interval_summary_to_total,
    assign_confidence_bands,
    bootstrap_training_frame,
    load_uncertainty_artifact,
    predict_uncertainty_ensemble,
    resolve_ensemble_seeds,
    save_uncertainty_training_run,
    summarize_ensemble_predictions,
    train_uncertainty_ensemble,
)


class UncertaintyTestCase(unittest.TestCase):
    def test_resolve_ensemble_seeds_is_deterministic(self) -> None:
        self.assertEqual(resolve_ensemble_seeds(42, 3), (42, 1051, 2060))

    def test_bootstrap_training_frame_preserves_city_coverage(self) -> None:
        frame = pd.DataFrame(
            {
                "city_name": ["a", "a", "b", "b"],
                "value": [1, 2, 3, 4],
            }
        )
        bootstrapped = bootstrap_training_frame(
            frame,
            random_state=42,
            group_column="city_name",
            within_group=True,
        )
        self.assertEqual(len(bootstrapped), len(frame))
        self.assertEqual(sorted(bootstrapped["city_name"].unique().tolist()), ["a", "b"])

    def test_summarize_ensemble_predictions_adds_expected_columns(self) -> None:
        frame = pd.DataFrame(
            {
                "member_01": [10.0, 20.0],
                "member_02": [12.0, 18.0],
                "member_03": [11.0, 24.0],
            }
        )
        summary = summarize_ensemble_predictions(frame)
        self.assertIn("Population_Estimate_P10", summary.columns)
        self.assertIn("Population_Estimate_P50", summary.columns)
        self.assertIn("Population_Estimate_P90", summary.columns)
        self.assertIn("Population_Uncertainty_Relative", summary.columns)
        self.assertTrue((summary["Population_Estimate_P90"] >= summary["Population_Estimate_P50"]).all())
        self.assertTrue((summary["Population_Estimate_P50"] >= summary["Population_Estimate_P10"]).all())

    def test_assign_confidence_bands_downgrades_under_moderate_completeness(self) -> None:
        relative = pd.Series([0.1, 0.3, 0.9], index=["a", "b", "c"])
        bands = assign_confidence_bands(relative, completeness_label="moderate")
        self.assertEqual(bands.loc["a"], "medium")
        self.assertEqual(bands.loc["b"], "low")
        self.assertEqual(bands.loc["c"], "low")

    def test_align_interval_summary_to_total_preserves_final_alias(self) -> None:
        summary = pd.DataFrame(
            {
                "Population_Estimate_P10": [8.0, 12.0],
                "Population_Estimate_P50": [10.0, 15.0],
                "Population_Estimate_P90": [12.0, 18.0],
                "Population_Uncertainty_Width": [4.0, 6.0],
                "Population_Uncertainty_Relative": [0.4, 0.4],
                "Population_Estimate_Final": [10.0, 15.0],
            }
        )
        aligned = align_interval_summary_to_total(summary, official_total=50.0)
        self.assertAlmostEqual(float(aligned["Population_Estimate_P50"].sum()), 50.0)
        self.assertTrue(aligned["Population_Estimate_Final"].equals(aligned["Population_Estimate_P50"]))

    def test_train_save_and_load_uncertainty_artifact(self) -> None:
        frame = pd.DataFrame(
            {
                "city_name": ["a", "a", "b", "b"],
                "Weak_Population_Target": [10.0, 20.0, 15.0, 25.0],
                "Building_Count": [1.0, 2.0, 1.5, 2.5],
                "Building_Area": [10.0, 15.0, 11.0, 16.0],
                "Residential_Area": [7.0, 8.0, 6.0, 7.0],
                "Commercial_Area": [1.0, 2.0, 1.0, 2.0],
                "Retail_Area": [1.0, 1.0, 1.0, 1.0],
                "Public_Area": [0.5, 0.5, 0.5, 0.5],
                "Road_Length": [20.0, 30.0, 25.0, 35.0],
                "Bus_Stop_Count": [1.0, 2.0, 1.0, 2.0],
                "Park_Area": [0.0, 1.0, 0.0, 1.0],
                "Building_With_Levels_Count": [1.0, 2.0, 1.0, 2.0],
                "Mean_Building_Levels": [2.0, 3.0, 2.0, 3.0],
                "Total_Floor_Area": [20.0, 45.0, 22.0, 48.0],
                "Schools_Count": [0.0, 1.0, 0.0, 1.0],
                "Hospitals_Count": [0.0, 0.0, 0.0, 1.0],
                "Parks_Shops_Count": [1.0, 2.0, 1.0, 2.0],
                "POI_Access_Index": [0.2, 0.8, 0.3, 0.9],
                "Combined_Index": [0.4, 0.9, 0.5, 1.0],
            }
        )
        training_config = TrainingConfig(model_name="random_forest", random_state=7)
        uncertainty_config = UncertaintyConfig(ensemble_size=3)
        result = train_uncertainty_ensemble(
            frame,
            training_config=training_config,
            uncertainty_config=uncertainty_config,
        )
        self.assertEqual(len(result.members), 3)
        self.assertEqual(len(result.member_manifest), 3)

        with tempfile.TemporaryDirectory() as tmp_dir:
            paths = save_uncertainty_training_run(result, Path(tmp_dir))
            loaded = load_uncertainty_artifact(paths["artifact_path"])
            self.assertIsInstance(loaded, LoadedUncertaintyArtifact)
            self.assertEqual(len(loaded.members), 3)

            feature_frame = frame[list(training_config.feature_columns)].copy()
            predictions = predict_uncertainty_ensemble(feature_frame, loaded)
            self.assertEqual(predictions.shape, (len(frame), 3))


if __name__ == "__main__":
    unittest.main()
