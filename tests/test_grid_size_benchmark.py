from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.city1.grid_size_benchmark import save_grid_size_benchmark


class GridSizeBenchmarkTestCase(unittest.TestCase):
    def test_save_grid_size_benchmark_writes_expected_outputs(self) -> None:
        class DummyResult:
            pass

        result = DummyResult()
        result.run_results = pd.DataFrame(
            [
                {
                    "city_name": "Almaty",
                    "place_name": "Almaty, Kazakhstan",
                    "cell_size_meters": 500,
                    "success": True,
                    "calibration_factor": 1.1,
                }
            ]
        )
        result.cell_size_summary = pd.DataFrame(
            [
                {
                    "cell_size_meters": 500,
                    "cities": 1,
                    "benchmark_score": 0.1,
                    "mean_calibration_distance_from_one": 0.05,
                    "mean_runtime_seconds": 12.0,
                }
            ]
        )
        result.city_recommendations = pd.DataFrame(
            [
                {
                    "city_name": "Almaty",
                    "recommended_cell_size_meters": 500,
                    "benchmark_score": 0.1,
                    "calibration_factor": 1.1,
                }
            ]
        )
        result.global_recommendation = {
            "recommended_cell_size_meters": 500,
            "benchmark_score": 0.1,
            "mean_calibration_distance_from_one": 0.05,
            "mean_runtime_seconds": 12.0,
            "cities": 1,
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_paths = save_grid_size_benchmark(result, Path(tmp_dir))
            self.assertTrue(output_paths["run_results_path"].exists())
            self.assertTrue(output_paths["summary_path"].exists())
            self.assertTrue(output_paths["city_recommendations_path"].exists())
            self.assertTrue(output_paths["report_path"].exists())

            report_text = output_paths["report_path"].read_text(encoding="utf-8")
            self.assertIn("Recommended default cell size: `500 m`", report_text)


if __name__ == "__main__":
    unittest.main()
