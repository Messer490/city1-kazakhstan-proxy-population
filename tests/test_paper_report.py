from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.city1.paper_report import PaperReportConfig, build_paper_report


class PaperReportTestCase(unittest.TestCase):
    def test_build_paper_report_creates_summary_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            status_csv = root / "status.csv"
            qa_csv = root / "qa.csv"
            metrics_dir = root / "metrics"
            benchmark_dir = root / "benchmark"
            osm_dir = root / "osm"
            district_dir = root / "district"
            external_dir = root / "external"
            ablation_dir = root / "ablation"
            qualitative_dir = root / "qualitative"
            inference_dir = root / "inference"
            output_dir = root / "paper"

            metrics_dir.mkdir()
            benchmark_dir.mkdir()
            osm_dir.mkdir()
            district_dir.mkdir()
            external_dir.mkdir()
            (external_dir / "figures").mkdir()
            ablation_dir.mkdir()
            (ablation_dir / "figures").mkdir()
            qualitative_dir.mkdir()
            (qualitative_dir / "figures").mkdir()
            inference_dir.mkdir()

            pd.DataFrame(
                [
                    {
                        "city_name": "Semey",
                        "normalized_city_name": "semey",
                        "display_query": "Semey, Kazakhstan",
                        "country": "Kazakhstan",
                        "population": 315382,
                        "supported_for_calibrated_inference": True,
                        "validated_batch": True,
                        "smoke_passed": True,
                        "status_label": "validated_smoke_passed",
                    }
                ]
            ).to_csv(status_csv, index=False)

            pd.DataFrame(
                [{"city_name": "semey", "high_zero_share_feature_count": 1}]
            ).to_csv(qa_csv, index=False)

            pd.DataFrame(
                [
                    {
                        "fold": 1,
                        "raw_mae": 1.0,
                        "raw_rmse": 1.0,
                        "raw_r2": 0.5,
                        "calibrated_mae": 1.0,
                        "calibrated_rmse": 2.0,
                        "calibrated_r2": 0.9,
                    }
                ]
            ).to_csv(metrics_dir / "random_forest_fold_metrics.csv", index=False)

            pd.DataFrame(
                [{"cell_size_meters": 500, "benchmark_score": 0.1, "mean_calibration_distance_from_one": 0.05}]
            ).to_csv(benchmark_dir / "grid_size_summary.csv", index=False)
            pd.DataFrame(
                [{"city_name": "Semey", "recommended_cell_size_meters": 500, "benchmark_score": 0.1, "calibration_factor": 1.0}]
            ).to_csv(benchmark_dir / "grid_size_city_recommendations.csv", index=False)
            pd.DataFrame(
                [
                    {
                        "city_name": "semey",
                        "completeness_score": 75.0,
                        "completeness_label": "good",
                    }
                ]
            ).to_csv(osm_dir / "osm_completeness_summary.csv", index=False)
            (district_dir / "semey").mkdir()
            pd.DataFrame(
                [
                    {
                        "city_name": "Semey",
                        "district_count_total": 2,
                        "district_count_compared": 2,
                        "official_total": 100.0,
                        "predicted_total": 98.0,
                        "absolute_gap_total": 2.0,
                        "mae": 5.0,
                        "rmse": 6.0,
                        "mape": 4.0,
                        "share_mae": 0.02,
                        "share_rmse": 0.03,
                        "pearson_r": 0.9,
                        "spearman_r": 1.0,
                    }
                ]
            ).to_csv(district_dir / "semey" / "district_benchmark_metrics.csv", index=False)

            pd.DataFrame(
                [
                    {
                        "benchmark_name": "worldpop",
                        "pearson_r": 0.88,
                        "spearman_r": 0.83,
                        "top_decile_overlap": 0.48,
                        "hotspot_iou": 0.33,
                    },
                    {
                        "benchmark_name": "ghs_pop",
                        "pearson_r": 0.72,
                        "spearman_r": 0.84,
                        "top_decile_overlap": 0.61,
                        "hotspot_iou": 0.44,
                    },
                ]
            ).to_csv(external_dir / "external_benchmark_summary_by_source.csv", index=False)
            pd.DataFrame(
                [
                    {
                        "city_name": "Almaty",
                        "city_slug": "almaty",
                        "benchmark_name": "worldpop",
                        "pearson_r": 0.88,
                        "spearman_r": 0.89,
                        "top_decile_overlap": 0.31,
                        "hotspot_iou": 0.18,
                    }
                ]
            ).to_csv(external_dir / "external_benchmark_metrics.csv", index=False)
            (external_dir / "figures" / "figure_external_benchmark_pearson.png").write_bytes(b"png")
            (external_dir / "figures" / "figure_external_benchmark_hotspot_iou.png").write_bytes(b"png")

            pd.DataFrame(
                [
                    {
                        "ablation_name": "full_features",
                        "mean_calibrated_rmse": 10.0,
                        "mean_calibrated_r2": 0.9,
                        "calibration_rmse_gain": 5.0,
                        "is_selected_non_full_winner": False,
                    },
                    {
                        "ablation_name": "built_form_only",
                        "mean_calibrated_rmse": 11.0,
                        "mean_calibrated_r2": 0.8,
                        "calibration_rmse_gain": 6.0,
                        "is_selected_non_full_winner": True,
                    },
                ]
            ).to_csv(ablation_dir / "ablation_summary.csv", index=False)
            pd.DataFrame(
                [
                    {
                        "ablation_name": "full_features",
                        "extra_type": "spatial_block",
                        "benchmark_name": "",
                        "mean_calibrated_rmse": 9.0,
                    }
                ]
            ).to_csv(ablation_dir / "selected_extras_summary.csv", index=False)
            (ablation_dir / "figures" / "figure_ablation_loco.png").write_bytes(b"png")

            pd.DataFrame(
                [
                    {
                        "city_slug": "almaty",
                        "case_id": "H1",
                        "zone_type": "hotspot",
                        "source_component_id": "hotspot_01",
                        "case_title": "Central Core",
                        "cell_count": 10,
                        "total_population_full": 100.0,
                        "mean_population_full": 10.0,
                        "mean_population_built_form": 9.0,
                        "building_area_mean": 20.0,
                        "total_floor_area_mean": 30.0,
                        "road_length_mean": 15.0,
                        "poi_access_index_mean": 0.5,
                        "completeness_score": 75.8,
                        "completeness_label": "good",
                        "interpretation_label": "central hotspot",
                        "narrative_summary": "summary",
                        "caution_note": "caution",
                    },
                    {
                        "city_slug": "astana",
                        "case_id": "L1",
                        "zone_type": "coldspot",
                        "source_component_id": "coldspot_01",
                        "case_title": "Open Belt",
                        "cell_count": 8,
                        "total_population_full": 1.0,
                        "mean_population_full": 0.1,
                        "mean_population_built_form": 0.2,
                        "building_area_mean": 0.0,
                        "total_floor_area_mean": 0.0,
                        "road_length_mean": 0.0,
                        "poi_access_index_mean": 0.01,
                        "completeness_score": 65.0,
                        "completeness_label": "moderate",
                        "interpretation_label": "coldspot",
                        "narrative_summary": "summary",
                        "caution_note": "caution",
                    },
                ]
            ).to_csv(qualitative_dir / "qualitative_validation_summary.csv", index=False)
            (qualitative_dir / "qualitative_validation_report.md").write_text("# qualitative", encoding="utf-8")
            (qualitative_dir / "figures" / "figure_qualitative_overview_almaty.png").write_bytes(b"png")
            (qualitative_dir / "figures" / "figure_qualitative_overview_astana.png").write_bytes(b"png")
            (qualitative_dir / "figures" / "figure_qualitative_cases_almaty.png").write_bytes(b"png")
            (qualitative_dir / "figures" / "figure_qualitative_cases_astana.png").write_bytes(b"png")

            pd.DataFrame(
                [{"city_name": "Semey", "longitude": 80.0, "latitude": 50.0, "Population_Estimate_Final": 10.0}]
            ).to_csv(inference_dir / "semey_kazakhstan__random_forest.csv", index=False)

            outputs = build_paper_report(
                PaperReportConfig(
                    status_csv=status_csv,
                    qa_city_summary_csv=qa_csv,
                    metrics_dir=metrics_dir,
                    grid_benchmark_dir=benchmark_dir,
                    osm_completeness_dir=osm_dir,
                    district_benchmark_dir=district_dir,
                    external_benchmark_dir=external_dir,
                    ablation_dir=ablation_dir,
                    qualitative_validation_dir=qualitative_dir,
                    inference_runs_dir=inference_dir,
                    output_dir=output_dir,
                    example_city_slugs=("semey",),
                )
            )

            self.assertTrue(outputs["report_path"].exists())
            self.assertTrue(outputs["model_comparison_figure_path"].exists())
            self.assertTrue(outputs["grid_size_figure_path"].exists())
            self.assertTrue(outputs["osm_completeness_figure_path"].exists())
            self.assertTrue(outputs["district_benchmark_figure_path"].exists())
            self.assertTrue(outputs["example_surface_figure_1"].exists())
            self.assertTrue(outputs["external_benchmark_summary_table_path"].exists())
            self.assertTrue(outputs["external_benchmark_metrics_table_path"].exists())
            self.assertTrue(outputs["ablation_summary_table_path"].exists())
            self.assertTrue(outputs["ablation_selected_extras_table_path"].exists())
            self.assertTrue(outputs["qualitative_validation_case_table_path"].exists())
            self.assertTrue(outputs["external_benchmark_pearson_figure_path"].exists())
            self.assertTrue(outputs["external_benchmark_hotspot_figure_path"].exists())
            self.assertTrue(outputs["ablation_figure_path"].exists())
            self.assertTrue(outputs["qualitative_overview_figure_almaty"].exists())
            self.assertTrue(outputs["qualitative_overview_figure_astana"].exists())
            self.assertTrue(outputs["qualitative_cases_figure_almaty"].exists())
            self.assertTrue(outputs["qualitative_cases_figure_astana"].exists())
            report_text = outputs["report_path"].read_text(encoding="utf-8")
            self.assertIn("## External benchmark", report_text)
            self.assertIn("## Ablation", report_text)
            self.assertIn("## Qualitative validation", report_text)


if __name__ == "__main__":
    unittest.main()
