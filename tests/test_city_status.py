from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.city1.city_status import build_city_status_registry


class CityStatusRegistryTestCase(unittest.TestCase):
    def test_build_city_status_registry_tracks_validated_and_runtime_only_cities(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)

            totals_path = root / "city_population_reference_v2.csv"
            totals_path.write_text(
                "\n".join(
                    [
                        "city_name,normalized_city_name,country,population,reference_date,source_tier,verified,source_name,source_url,notes",
                        "Semey,semey,Kazakhstan,315382,2026-02-01,official,True,src,url,notes",
                        "Kurchatov,kurchatov,Kazakhstan,9822,2026-02-01,official,True,src,url,notes",
                    ]
                ),
                encoding="utf-8",
            )

            features_dir = root / "features"
            features_dir.mkdir()
            pd.DataFrame(
                {
                    "Zone_ID": ["Z1"],
                    "latitude": [50.0],
                    "longitude": [80.0],
                    "Building_Count": [1.0],
                    "Building_Area": [10.0],
                    "Residential_Area": [10.0],
                    "Commercial_Area": [0.0],
                    "Retail_Area": [0.0],
                    "Public_Area": [0.0],
                    "Road_Length": [5.0],
                    "Bus_Stop_Count": [0.0],
                    "Park_Area": [0.0],
                    "Building_With_Levels_Count": [1.0],
                    "Mean_Building_Levels": [2.0],
                    "Total_Floor_Area": [20.0],
                    "Schools_Count": [0.0],
                    "Hospitals_Count": [0.0],
                    "Parks_Shops_Count": [0.0],
                    "POI_Access_Index": [0.5],
                    "Combined_Index": [1.0],
                }
            ).to_csv(features_dir / "semey.csv", index=False)

            city_summary_path = root / "city_summary.csv"
            pd.DataFrame(
                [
                    {
                        "city_name": "semey",
                        "row_count": 1,
                        "missing_feature_columns": 0,
                        "negative_feature_values": 0,
                        "constant_feature_count": 0,
                        "high_zero_share_feature_count": 0,
                        "null_latitude": 0,
                        "null_longitude": 0,
                        "duplicate_zone_ids": 0,
                        "building_area_zero_share": 0.0,
                        "road_length_zero_share": 0.0,
                        "total_floor_area_zero_share": 0.0,
                    }
                ]
            ).to_csv(city_summary_path, index=False)

            qa_flags_path = root / "flags.csv"
            pd.DataFrame(
                [{"city_name": "semey", "severity": "warning", "column": "Park_Area", "issue": "extreme_zero_share", "details": "Zero share is 1.000."}]
            ).to_csv(qa_flags_path, index=False)

            training_oof_path = root / "random_forest_oof_predictions.csv"
            pd.DataFrame(
                [{"city_name": "semey", "source_file": "semey.csv", "Weak_Population_Target": 1.0, "prediction_raw": 1.0, "prediction_calibrated": 1.0}]
            ).to_csv(training_oof_path, index=False)

            smoke_dir = root / "smoke"
            smoke_dir.mkdir()
            pd.DataFrame([{"city_name": "Semey"}]).to_csv(smoke_dir / "smoke_test_output.csv", index=False)

            inference_dir = root / "inference"
            inference_dir.mkdir()
            pd.DataFrame([{"city_name": "Kurchatov"}]).to_csv(inference_dir / "kurchatov_kazakhstan__random_forest.csv", index=False)

            frame = build_city_status_registry(
                totals_csv=totals_path,
                features_dir=features_dir,
                qa_city_summary_csv=city_summary_path,
                qa_flags_csv=qa_flags_path,
                training_oof_csv=training_oof_path,
                smoke_dir=smoke_dir,
                inference_runs_dir=inference_dir,
            )

            semey = frame.loc[frame["normalized_city_name"] == "semey"].iloc[0]
            kurchatov = frame.loc[frame["normalized_city_name"] == "kurchatov"].iloc[0]

            self.assertTrue(bool(semey["validated_batch"]))
            self.assertTrue(bool(semey["smoke_passed"]))
            self.assertEqual(str(semey["district_benchmark_quality"]), "none")
            self.assertEqual(str(semey["status_label"]), "validated_smoke_passed")

            self.assertTrue(bool(kurchatov["official_total_available"]))
            self.assertFalse(bool(kurchatov["validated_batch"]))
            self.assertTrue(bool(kurchatov["saved_inference_example"]))
            self.assertEqual(str(kurchatov["district_benchmark_quality"]), "none")
            self.assertEqual(str(kurchatov["status_label"]), "calibrated_runtime_only")


if __name__ == "__main__":
    unittest.main()
