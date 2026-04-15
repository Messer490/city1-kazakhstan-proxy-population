from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import GeometryCollection, LineString, Polygon

from src.city1.district_benchmark import (
    compute_district_benchmark_metrics,
    load_district_reference,
    aggregate_predictions_to_districts,
    save_district_benchmark_report,
)


class DistrictBenchmarkTestCase(unittest.TestCase):
    def test_aggregate_predictions_to_districts_splits_cells_by_area(self) -> None:
        prediction = gpd.GeoDataFrame(
            {
                "Zone_ID": ["Z1", "Z2"],
                "Population_Estimate_Final": [100.0, 100.0],
            },
            geometry=[
                Polygon([(0, 0), (2, 0), (2, 1), (0, 1)]),
                Polygon([(0, 1), (2, 1), (2, 2), (0, 2)]),
            ],
            crs="EPSG:3857",
        )
        districts = gpd.GeoDataFrame(
            {
                "district_name": ["West", "East"],
                "normalized_district_name": ["west", "east"],
                "official_population": [100.0, 100.0],
                "district_query": ["West, Test City", "East, Test City"],
                "source_name": ["test", "test"],
                "source_url": ["", ""],
                "source_precision": ["exact", "exact"],
                "use_in_metrics": [True, True],
            },
            geometry=[
                Polygon([(0, 0), (1, 0), (1, 2), (0, 2)]),
                Polygon([(1, 0), (2, 0), (2, 2), (1, 2)]),
            ],
            crs="EPSG:3857",
        )

        result = aggregate_predictions_to_districts(prediction, districts)
        self.assertEqual(sorted(result["district_name"].tolist()), ["East", "West"])
        self.assertTrue(all(abs(value - 100.0) < 1e-4 for value in result["predicted_population"].tolist()))

    def test_metrics_and_report_outputs(self) -> None:
        frame = pd.DataFrame(
            {
                "district_name": ["A", "B"],
                "official_population": [100.0, 200.0],
                "predicted_population": [110.0, 190.0],
                "official_share": [1 / 3, 2 / 3],
                "predicted_share": [110.0 / 300.0, 190.0 / 300.0],
                "use_in_metrics": [True, True],
                "source_precision": ["exact", "exact"],
            }
        )
        metrics = compute_district_benchmark_metrics(frame, city_name="Test City")
        self.assertEqual(metrics.district_count_compared, 2)
        self.assertGreaterEqual(metrics.pearson_r, 0.99)

        with tempfile.TemporaryDirectory() as tmp_dir:
            outputs = save_district_benchmark_report(frame, metrics, output_dir=tmp_dir)
            self.assertTrue(outputs["district_table_path"].exists())
            self.assertTrue(outputs["metrics_path"].exists())
            self.assertTrue(outputs["figure_bar_path"].exists())
            self.assertTrue(outputs["figure_scatter_path"].exists())
            self.assertTrue(outputs["report_path"].exists())

    def test_aggregate_predictions_to_districts_handles_geometry_collection_boundaries(self) -> None:
        prediction = gpd.GeoDataFrame(
            {
                "Zone_ID": ["Z1"],
                "Population_Estimate_Final": [100.0],
            },
            geometry=[Polygon([(0, 0), (2, 0), (2, 2), (0, 2)])],
            crs="EPSG:3857",
        )
        districts = gpd.GeoDataFrame(
            {
                "district_name": ["Mixed"],
                "normalized_district_name": ["mixed"],
                "official_population": [100.0],
                "district_query": ["Mixed, Test City"],
                "source_name": ["test"],
                "source_url": [""],
                "source_precision": ["exact"],
                "use_in_metrics": [True],
            },
            geometry=[
                GeometryCollection(
                    [
                        Polygon([(0, 0), (2, 0), (2, 2), (0, 2)]),
                        LineString([(0, 0), (2, 2)]),
                    ]
                )
            ],
            crs="EPSG:3857",
        )

        result = aggregate_predictions_to_districts(prediction, districts)
        self.assertEqual(len(result), 1)
        self.assertAlmostEqual(float(result["predicted_population"].iloc[0]), 100.0, places=4)

    def test_aggregate_predictions_to_districts_keeps_zero_intersection_districts(self) -> None:
        prediction = gpd.GeoDataFrame(
            {
                "Zone_ID": ["Z1"],
                "Population_Estimate_Final": [100.0],
            },
            geometry=[Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])],
            crs="EPSG:3857",
        )
        districts = gpd.GeoDataFrame(
            {
                "district_name": ["Covered", "Empty"],
                "normalized_district_name": ["covered", "empty"],
                "official_population": [100.0, 50.0],
                "district_query": ["Covered, Test City", "Empty, Test City"],
                "source_name": ["test", "test"],
                "source_url": ["", ""],
                "source_precision": ["exact", "exact"],
                "use_in_metrics": [True, True],
            },
            geometry=[
                Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]),
                Polygon([(2, 2), (3, 2), (3, 3), (2, 3)]),
            ],
            crs="EPSG:3857",
        )

        result = aggregate_predictions_to_districts(prediction, districts)
        self.assertEqual(sorted(result["district_name"].tolist()), ["Covered", "Empty"])
        empty = result.loc[result["district_name"] == "Empty"].iloc[0]
        self.assertEqual(float(empty["predicted_population"]), 0.0)

    def test_load_district_reference_normalizes_flags(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "reference.csv"
            pd.DataFrame(
                [
                    {
                        "city_name": "Almaty",
                        "district_name": "Almaly",
                        "district_query": "Almaly District, Almaty, Kazakhstan",
                        "official_population": 224600,
                        "use_in_metrics": "True",
                    }
                ]
            ).to_csv(path, index=False)

            frame = load_district_reference(path)
            self.assertEqual(frame["normalized_city_name"].iloc[0], "almaty")
            self.assertTrue(bool(frame["use_in_metrics"].iloc[0]))


if __name__ == "__main__":
    unittest.main()
