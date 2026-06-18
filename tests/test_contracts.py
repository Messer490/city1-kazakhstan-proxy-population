from __future__ import annotations

import unittest

from src.city1.contracts import (
    CITY_OUTPUT_COLUMNS,
    CITY_OUTPUT_COLUMNS_V3,
    GRID_FEATURE_COLUMNS,
    MODEL_VERSION_V3,
    MODEL_FEATURE_COLUMNS,
    PROBLEM_STATEMENT_V3,
    UNCERTAINTY_OUTPUT_COLUMNS,
    missing_columns,
)


class ContractsTestCase(unittest.TestCase):
    def test_model_features_extend_grid_features(self) -> None:
        self.assertTrue(set(GRID_FEATURE_COLUMNS).issubset(set(MODEL_FEATURE_COLUMNS)))

    def test_output_contains_coordinates_and_prediction(self) -> None:
        self.assertIn("latitude", CITY_OUTPUT_COLUMNS)
        self.assertIn("longitude", CITY_OUTPUT_COLUMNS)
        self.assertIn("Population_Estimate_Final", CITY_OUTPUT_COLUMNS)

    def test_v3_output_uses_frozen_canonical_fields(self) -> None:
        self.assertIn("run_id", CITY_OUTPUT_COLUMNS_V3)
        self.assertIn("city_slug", CITY_OUTPUT_COLUMNS_V3)
        self.assertIn("p50", CITY_OUTPUT_COLUMNS_V3)
        self.assertIn("confidence_band", CITY_OUTPUT_COLUMNS_V3)
        self.assertIn("population_estimate_final", CITY_OUTPUT_COLUMNS_V3)
        self.assertNotIn("Zone_ID", CITY_OUTPUT_COLUMNS_V3)

    def test_legacy_uncertainty_columns_still_exist_for_internal_compatibility(self) -> None:
        self.assertIn("Population_Estimate_P50", UNCERTAINTY_OUTPUT_COLUMNS)
        self.assertIn("Population_Confidence_Band", UNCERTAINTY_OUTPUT_COLUMNS)

    def test_v3_problem_statement_mentions_uncertainty(self) -> None:
        self.assertIn("uncertainty", PROBLEM_STATEMENT_V3.objective.lower())
        self.assertIn("ensemble", PROBLEM_STATEMENT_V3.calibration.lower())

    def test_v3_model_version_slug(self) -> None:
        self.assertTrue(MODEL_VERSION_V3.startswith("city1_v3"))

    def test_missing_columns(self) -> None:
        required = ("a", "b", "c")
        actual = ("a", "c")
        self.assertEqual(missing_columns(actual, required), ["b"])


if __name__ == "__main__":
    unittest.main()
