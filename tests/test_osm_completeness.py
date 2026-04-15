from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.city1.osm_completeness import (
    build_osm_completeness_batch,
    compute_osm_completeness,
    save_osm_completeness_report,
)


class OSMCompletenessTestCase(unittest.TestCase):
    def test_compute_osm_completeness_rewards_nonzero_coverage(self) -> None:
        frame = pd.DataFrame(
            {
                "Building_Area": [10.0, 5.0],
                "Road_Length": [50.0, 20.0],
                "POI_Access_Index": [0.5, 0.3],
                "Total_Floor_Area": [20.0, 8.0],
                "Bus_Stop_Count": [1.0, 0.0],
                "Park_Area": [0.0, 2.0],
                "Schools_Count": [0.0, 1.0],
                "Hospitals_Count": [0.0, 0.0],
                "Retail_Area": [0.0, 3.0],
            }
        )
        result = compute_osm_completeness(frame, city_name="semey")
        self.assertGreater(result.completeness_score, 55.0)
        self.assertIn(result.completeness_label, {"moderate", "good", "excellent"})

    def test_build_and_save_osm_completeness_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            features_dir = root / "features"
            features_dir.mkdir()
            pd.DataFrame(
                {
                    "Building_Area": [10.0],
                    "Road_Length": [20.0],
                    "POI_Access_Index": [0.5],
                    "Total_Floor_Area": [15.0],
                    "Bus_Stop_Count": [0.0],
                    "Park_Area": [0.0],
                    "Schools_Count": [1.0],
                    "Hospitals_Count": [0.0],
                    "Retail_Area": [0.0],
                }
            ).to_csv(features_dir / "semey.csv", index=False)

            summary = build_osm_completeness_batch(features_dir)
            outputs = save_osm_completeness_report(summary, root / "report")

            self.assertTrue(outputs["summary_path"].exists())
            self.assertTrue(outputs["figure_path"].exists())
            self.assertTrue(outputs["report_path"].exists())


if __name__ == "__main__":
    unittest.main()
