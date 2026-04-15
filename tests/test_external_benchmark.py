from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import Polygon

from src.city1.external_benchmark import (
    compute_external_surface_metrics,
    save_external_benchmark_report,
)


class ExternalBenchmarkTestCase(unittest.TestCase):
    def test_compute_external_surface_metrics_returns_expected_fields(self) -> None:
        frame = pd.DataFrame(
            {
                "city1_population": [1.0, 2.0, 3.0, 10.0, 12.0],
                "worldpop_population": [1.1, 1.9, 2.8, 9.5, 11.5],
            }
        )
        metrics = compute_external_surface_metrics(
            frame,
            benchmark_column="worldpop_population",
            city_name="Test City",
            city_slug="test_city",
            coverage_ok=True,
            raster_count=1,
        )
        self.assertEqual(metrics.city_name, "Test City")
        self.assertEqual(metrics.benchmark_name, "worldpop")
        self.assertEqual(metrics.cell_count, 5)
        self.assertTrue(metrics.coverage_ok)
        self.assertGreater(metrics.pearson_r, 0.99)
        self.assertGreaterEqual(metrics.top_decile_overlap, 1.0)

    def test_save_external_benchmark_report_writes_outputs(self) -> None:
        aligned = gpd.GeoDataFrame(
            {
                "Zone_ID": ["Z1", "Z2"],
                "city_name": ["Test City", "Test City"],
                "city1_population": [10.0, 20.0],
                "worldpop_population": [9.0, 19.0],
                "ghs_pop_population": [8.0, 22.0],
            },
            geometry=[
                Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]),
                Polygon([(1, 0), (2, 0), (2, 1), (1, 1)]),
            ],
            crs="EPSG:4326",
        )
        metrics_df = pd.DataFrame(
            [
                {
                    "city_name": "Test City",
                    "city_slug": "test_city",
                    "benchmark_name": "worldpop",
                    "cell_count": 2,
                    "raster_count": 1,
                    "coverage_ok": True,
                    "city1_total": 30.0,
                    "benchmark_total": 28.0,
                    "absolute_gap_total": 2.0,
                    "benchmark_to_city1_ratio": 28.0 / 30.0,
                    "pearson_r": 0.99,
                    "spearman_r": 1.0,
                    "top_decile_overlap": 1.0,
                    "hotspot_iou": 1.0,
                },
                {
                    "city_name": "Test City",
                    "city_slug": "test_city",
                    "benchmark_name": "ghs_pop",
                    "cell_count": 2,
                    "raster_count": 1,
                    "coverage_ok": True,
                    "city1_total": 30.0,
                    "benchmark_total": 30.0,
                    "absolute_gap_total": 0.0,
                    "benchmark_to_city1_ratio": 1.0,
                    "pearson_r": 0.95,
                    "spearman_r": 1.0,
                    "top_decile_overlap": 1.0,
                    "hotspot_iou": 1.0,
                },
            ]
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            outputs = save_external_benchmark_report(
                aligned_by_city={"test_city": aligned},
                metrics_df=metrics_df,
                output_dir=Path(tmp_dir) / "report",
            )
            self.assertTrue(outputs["metrics_path"].exists())
            self.assertTrue(outputs["summary_path"].exists())
            self.assertTrue(outputs["report_path"].exists())
            self.assertTrue(outputs["pearson_figure_path"].exists())
            self.assertTrue(outputs["hotspot_figure_path"].exists())


if __name__ == "__main__":
    unittest.main()
