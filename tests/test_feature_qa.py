from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.city1.feature_qa import run_feature_qa


class FeatureQATestCase(unittest.TestCase):
    def test_run_feature_qa_detects_clean_dataset(self) -> None:
        frame = pd.DataFrame(
            {
                "Zone_ID": ["Z1", "Z2"],
                "latitude": [43.1, 43.2],
                "longitude": [76.9, 77.0],
                "Building_Count": [1, 2],
                "Building_Area": [100.0, 150.0],
                "Residential_Area": [80.0, 110.0],
                "Commercial_Area": [10.0, 15.0],
                "Retail_Area": [5.0, 7.0],
                "Public_Area": [5.0, 8.0],
                "Road_Length": [50.0, 55.0],
                "Bus_Stop_Count": [1.0, 0.0],
                "Park_Area": [20.0, 30.0],
                "Building_With_Levels_Count": [1.0, 2.0],
                "Mean_Building_Levels": [2.0, 3.0],
                "Total_Floor_Area": [200.0, 450.0],
                "Schools_Count": [0.0, 1.0],
                "Hospitals_Count": [0.0, 0.0],
                "Parks_Shops_Count": [1.0, 2.0],
                "POI_Access_Index": [0.01, 0.02],
                "Combined_Index": [2.5, 4.0],
            }
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "semey.csv"
            frame.to_csv(path, index=False)

            bundle = run_feature_qa(tmp_dir)
            self.assertEqual(len(bundle.city_summary), 1)
            self.assertEqual(int(bundle.city_summary.iloc[0]["negative_feature_values"]), 0)
            self.assertEqual(int(bundle.city_summary.iloc[0]["missing_feature_columns"]), 0)
            error_flags = bundle.flags.loc[bundle.flags["severity"] == "error"]
            self.assertTrue(error_flags.empty)


if __name__ == "__main__":
    unittest.main()
