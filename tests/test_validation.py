from __future__ import annotations

import unittest

import pandas as pd

from src.city1.validation import validate_city_output, validate_feature_output


class ValidationTestCase(unittest.TestCase):
    def test_feature_output_validation_does_not_require_population_column(self) -> None:
        df = pd.DataFrame(
            {
                "Zone_ID": ["Z1"],
                "latitude": [43.0],
                "longitude": [76.0],
                "Building_Count": [1.0],
                "Building_Area": [10.0],
                "Residential_Area": [2.0],
                "Commercial_Area": [1.0],
                "Retail_Area": [1.0],
                "Public_Area": [0.0],
                "Road_Length": [100.0],
                "Bus_Stop_Count": [1.0],
                "Park_Area": [0.0],
                "Building_With_Levels_Count": [1.0],
                "Mean_Building_Levels": [2.0],
                "Total_Floor_Area": [20.0],
                "Schools_Count": [0.0],
                "Hospitals_Count": [0.0],
                "Parks_Shops_Count": [1.0],
                "POI_Access_Index": [0.5],
                "Combined_Index": [1.5],
            }
        )
        report = validate_feature_output(df, "sample_features")
        self.assertFalse(report.has_errors)

    def test_detects_missing_zone_and_coordinates(self) -> None:
        df = pd.DataFrame(
            {
                "Zone_ID": ["Z1", None],
                "latitude": [43.0, None],
                "longitude": [76.0, None],
                "Population_Estimate_Final": [10.0, 12.0],
            }
        )
        report = validate_city_output(df, "sample")
        codes = {issue.code for issue in report.issues}
        self.assertIn("missing_zone_id", codes)
        self.assertIn("missing_coordinates", codes)

    def test_detects_negative_numeric_values(self) -> None:
        df = pd.DataFrame(
            {
                "Zone_ID": ["Z1"],
                "latitude": [43.0],
                "longitude": [76.0],
                "Building_Count": [1],
                "Building_Area": [-5.0],
                "Residential_Area": [0.0],
                "Commercial_Area": [0.0],
                "Retail_Area": [0.0],
                "Public_Area": [0.0],
                "Road_Length": [1.0],
                "Bus_Stop_Count": [0],
                "Park_Area": [0.0],
                "Building_With_Levels_Count": [0],
                "Mean_Building_Levels": [0.0],
                "Total_Floor_Area": [0.0],
                "Schools_Count": [0],
                "Hospitals_Count": [0],
                "Parks_Shops_Count": [0],
                "POI_Access_Index": [0.1],
                "Combined_Index": [0.2],
                "Population_Estimate_Final": [50.0],
            }
        )
        report = validate_city_output(df, "sample")
        codes = {issue.code for issue in report.issues}
        self.assertIn("negative_values", codes)


if __name__ == "__main__":
    unittest.main()
