from __future__ import annotations

import unittest

import pandas as pd

from src.city1.labeling import allocate_city_total_to_cells
from src.city1.training import calibrate_predictions_by_city


class LabelingTestCase(unittest.TestCase):
    def test_allocate_city_total_sums_to_official_population(self) -> None:
        df = pd.DataFrame(
            {
                "Total_Floor_Area": [100.0, 200.0, 300.0],
                "Building_Area": [50.0, 70.0, 90.0],
                "Residential_Area": [10.0, 20.0, 30.0],
                "Building_Count": [1.0, 2.0, 3.0],
                "Road_Length": [100.0, 150.0, 200.0],
                "Bus_Stop_Count": [0.0, 1.0, 2.0],
                "Schools_Count": [0.0, 1.0, 0.0],
                "Hospitals_Count": [0.0, 0.0, 1.0],
                "Parks_Shops_Count": [1.0, 1.0, 1.0],
                "Combined_Index": [0.2, 0.5, 0.8],
            }
        )
        labeled = allocate_city_total_to_cells(df, official_population=600)
        self.assertAlmostEqual(float(labeled["Weak_Population_Target"].sum()), 600.0)
        self.assertAlmostEqual(float(labeled["Weak_Population_Share"].sum()), 1.0)

    def test_calibrate_predictions_by_city_respects_group_totals(self) -> None:
        predictions = pd.Series([1.0, 2.0, 3.0, 4.0])
        groups = pd.Series(["a", "a", "b", "b"])
        totals = pd.Series([30.0, 30.0, 70.0, 70.0])
        calibrated = calibrate_predictions_by_city(predictions, groups, totals)
        self.assertAlmostEqual(float(calibrated.iloc[:2].sum()), 30.0)
        self.assertAlmostEqual(float(calibrated.iloc[2:].sum()), 70.0)


if __name__ == "__main__":
    unittest.main()
