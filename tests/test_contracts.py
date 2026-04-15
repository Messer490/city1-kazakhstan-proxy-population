from __future__ import annotations

import unittest

from src.city1.contracts import (
    CITY_OUTPUT_COLUMNS,
    GRID_FEATURE_COLUMNS,
    MODEL_FEATURE_COLUMNS,
    missing_columns,
)


class ContractsTestCase(unittest.TestCase):
    def test_model_features_extend_grid_features(self) -> None:
        self.assertTrue(set(GRID_FEATURE_COLUMNS).issubset(set(MODEL_FEATURE_COLUMNS)))

    def test_output_contains_coordinates_and_prediction(self) -> None:
        self.assertIn("latitude", CITY_OUTPUT_COLUMNS)
        self.assertIn("longitude", CITY_OUTPUT_COLUMNS)
        self.assertIn("Population_Estimate_Final", CITY_OUTPUT_COLUMNS)

    def test_missing_columns(self) -> None:
        required = ("a", "b", "c")
        actual = ("a", "c")
        self.assertEqual(missing_columns(actual, required), ["b"])


if __name__ == "__main__":
    unittest.main()
