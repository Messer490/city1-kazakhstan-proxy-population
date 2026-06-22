from __future__ import annotations

import unittest

import pandas as pd

from src.city1.uncertainty_validation import (
    compute_confidence_band_validation_summary,
    compute_district_interval_coverage_metrics,
    compute_error_uncertainty_monotonicity,
    compute_external_disagreement_alignment,
    compute_hotspot_stability_tables,
    compute_interval_coverage_summary,
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

    def test_compute_interval_coverage_summary(self) -> None:
        frame = pd.DataFrame(
            {
                "city": ["Almaty", "Almaty", "Astana"],
                "weak_target": [10.0, 20.0, 30.0],
                "p10": [8.0, 25.0, 10.0],
                "p90": [12.0, 35.0, 40.0],
                "uncertainty_width": [4.0, 10.0, 30.0],
                "relative_uncertainty": [0.4, 0.5, 1.0],
            }
        )
        summary = compute_interval_coverage_summary(frame, protocol="locov_like")
        self.assertEqual(set(summary["city"]), {"Almaty", "Astana"})
        self.assertIn("coverage_p10_p90", summary.columns)

    def test_compute_hotspot_stability_tables(self) -> None:
        city_frames = {
            "almaty": pd.DataFrame(
                {
                    "city": ["Almaty", "Almaty", "Almaty"],
                    "cell_id": ["Z1", "Z2", "Z3"],
                    "hotspot_rank": [1, 2, 3],
                    "hotspot_priority_class": [
                        "high_value_high_confidence",
                        "high_value_low_confidence",
                        "not_priority",
                    ],
                    "p50": [100.0, 90.0, 10.0],
                    "relative_uncertainty": [0.10, 0.60, 0.20],
                    "uncertainty_width": [10.0, 60.0, 5.0],
                    "confidence_score": [0.80, 0.30, 0.55],
                }
            )
        }
        detail, summary = compute_hotspot_stability_tables(city_frames)
        self.assertFalse(detail.empty)
        self.assertFalse(summary.empty)
        self.assertIn("stability_metric", detail.columns)
        self.assertIn("mean_stability_metric", summary.columns)

    def test_compute_confidence_band_validation_summary(self) -> None:
        frame = pd.DataFrame(
            {
                "city": ["Semey", "Semey", "Semey"],
                "confidence_band": ["high", "medium", "low"],
                "p50": [50.0, 30.0, 10.0],
                "uncertainty_width": [5.0, 8.0, 20.0],
                "relative_uncertainty": [0.10, 0.26, 0.80],
                "absolute_error_p50": [2.0, 4.0, 9.0],
                "hotspot_priority_class": [
                    "high_value_high_confidence",
                    "medium_value_high_confidence",
                    "low_value_high_uncertainty",
                ],
            }
        )
        summary = compute_confidence_band_validation_summary(frame)
        self.assertEqual(set(summary["confidence_band"]), {"high", "medium", "low"})
        self.assertIn("mean_error_if_available", summary.columns)


if __name__ == "__main__":
    unittest.main()
