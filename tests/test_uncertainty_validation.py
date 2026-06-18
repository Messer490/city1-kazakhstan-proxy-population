from __future__ import annotations

import unittest

import pandas as pd

from src.city1.uncertainty_validation import (
    compute_district_interval_coverage_metrics,
    compute_error_uncertainty_monotonicity,
    compute_external_disagreement_alignment,
)


class UncertaintyValidationTestCase(unittest.TestCase):
    def test_compute_error_uncertainty_monotonicity_returns_summary_and_metrics(self) -> None:
        diagnostics = pd.DataFrame(
            {
                "Population_Uncertainty_Relative": [0.1, 0.2, 0.4, 0.7, 0.9],
                "Absolute_Error_P50": [1.0, 2.0, 3.0, 5.0, 6.0],
            }
        )
        summary, metrics = compute_error_uncertainty_monotonicity(diagnostics, bins=3)
        self.assertFalse(summary.empty)
        self.assertIn("error_uncertainty_spearman", metrics)
        self.assertGreaterEqual(metrics["mean_abs_error_highest_bucket"], metrics["mean_abs_error_lowest_bucket"])

    def test_compute_district_interval_coverage_metrics(self) -> None:
        frame = pd.DataFrame(
            {
                "district_name": ["A", "B"],
                "use_in_metrics": [True, True],
                "official_population": [100.0, 200.0],
                "predicted_population_p10": [90.0, 150.0],
                "predicted_population_p50": [110.0, 210.0],
                "predicted_population_p90": [120.0, 240.0],
                "interval_width": [30.0, 90.0],
                "relative_interval_width": [0.27, 0.43],
                "covered_by_interval": [True, True],
            }
        )
        metrics = compute_district_interval_coverage_metrics(frame, city_name="Almaty")
        self.assertEqual(metrics.city_name, "Almaty")
        self.assertGreater(metrics.coverage_rate, 0.0)

    def test_compute_external_disagreement_alignment(self) -> None:
        frame = pd.DataFrame(
            {
                "city1_population": [10.0, 20.0, 30.0, 40.0],
                "worldpop_population": [11.0, 18.0, 28.0, 50.0],
                "ghs_pop_population": [9.0, 25.0, 35.0, 45.0],
                "Population_Uncertainty_Relative": [0.1, 0.2, 0.8, 0.9],
            }
        )
        result = compute_external_disagreement_alignment(frame, city_name="Astana", city_slug="astana")
        self.assertEqual(set(result["benchmark_name"]), {"worldpop", "ghs_pop"})
        self.assertIn("disagreement_uncertainty_spearman", result.columns)


if __name__ == "__main__":
    unittest.main()
