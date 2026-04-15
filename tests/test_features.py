from __future__ import annotations

import unittest

import pandas as pd

from src.city1.features import compute_combined_index, min_max_scale_frame
from src.city1.grid import validate_grid_config
from src.city1.config import GridConfig


class FeatureMathTestCase(unittest.TestCase):
    def test_min_max_scale_frame_handles_constant_columns(self) -> None:
        df = pd.DataFrame(
            {
                "a": [1.0, 2.0, 3.0],
                "b": [5.0, 5.0, 5.0],
            }
        )
        scaled = min_max_scale_frame(df)
        self.assertEqual(float(scaled["a"].iloc[0]), 0.0)
        self.assertEqual(float(scaled["a"].iloc[-1]), 1.0)
        self.assertTrue((scaled["b"] == 0.0).all())

    def test_combined_index_returns_zero_when_no_columns_available(self) -> None:
        df = pd.DataFrame({"x": [1, 2, 3]})
        combined = compute_combined_index(df, ("missing_a", "missing_b"))
        self.assertTrue((combined == 0.0).all())


class GridConfigTestCase(unittest.TestCase):
    def test_validate_grid_config_rejects_non_positive_cell_size(self) -> None:
        with self.assertRaises(ValueError):
            validate_grid_config(GridConfig(cell_size_meters=0))


if __name__ == "__main__":
    unittest.main()
