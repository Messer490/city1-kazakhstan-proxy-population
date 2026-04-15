from __future__ import annotations

import unittest

import pandas as pd

from src.city1.inference import LoadedModelArtifact, _build_output_frame, _predict_raw_population


class _FakeEstimator:
    def predict(self, features):
        return pd.Series([10.0, 20.0], index=features.index)


class InferenceTestCase(unittest.TestCase):
    def test_predict_raw_population_uses_feature_columns(self) -> None:
        frame = pd.DataFrame({"f1": [1.0, 2.0], "f2": [3.0, 4.0]})
        model = LoadedModelArtifact(
            path=None,  # type: ignore[arg-type]
            model_name="fake",
            estimator=_FakeEstimator(),
            feature_columns=("f1", "f2"),
            use_log_target=False,
        )

        prediction = _predict_raw_population(frame, model)
        self.assertEqual(prediction.tolist(), [10.0, 20.0])

    def test_build_output_frame_calculates_calibration_factor(self) -> None:
        frame = pd.DataFrame({"Zone_ID": ["Z1", "Z2"], "latitude": [1.0, 2.0], "longitude": [3.0, 4.0]})
        model = LoadedModelArtifact(
            path=None,  # type: ignore[arg-type]
            model_name="fake",
            estimator=_FakeEstimator(),
            feature_columns=("f1",),
            use_log_target=False,
        )
        raw_prediction = pd.Series([10.0, 20.0])
        calibrated = pd.Series([40.0, 80.0])

        output = _build_output_frame(
            feature_frame=frame,
            raw_prediction=raw_prediction,
            calibrated_prediction=calibrated,
            place_name="Semey, Kazakhstan",
            model=model,
            official_population=120,
        )
        self.assertEqual(output["city_name"].iloc[0], "Semey")
        self.assertEqual(output["model_name"].iloc[0], "fake")
        self.assertEqual(output["Official_City_Population"].iloc[0], 120)
        self.assertAlmostEqual(float(output["Calibration_Factor"].iloc[0]), 4.0)
        self.assertAlmostEqual(float(output["Population_Estimate_Final"].sum()), 120.0)


if __name__ == "__main__":
    unittest.main()
