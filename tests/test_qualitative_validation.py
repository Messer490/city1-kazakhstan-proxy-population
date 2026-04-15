from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import Polygon

from src.city1.qualitative_validation import (
    QualitativeValidationConfig,
    extract_candidate_components,
    run_qualitative_render,
    run_qualitative_scaffold,
    validate_registry,
)


def _build_grid_surface(city_name: str) -> gpd.GeoDataFrame:
    rows: list[dict[str, object]] = []
    size = 8
    for y in range(size):
        for x in range(size):
            population = 5.0
            if x in (0, 1) and y in (0, 1):
                population = 100.0
            elif x in (6, 7) and y in (6, 7):
                population = 90.0
            elif x in (0, 1) and y in (6, 7):
                population = 0.0
            elif x in (6, 7) and y in (0, 1):
                population = 1.0
            rows.append(
                {
                    "Zone_ID": f"{city_name[:3]}_{y}_{x}",
                    "Population_Estimate_Final": population,
                    "Building_Area": population * 2.0 + x,
                    "Road_Length": population * 0.5 + y,
                    "Total_Floor_Area": population * 3.0,
                    "POI_Access_Index": population / 100.0,
                    "geometry": Polygon([(x, y), (x + 1, y), (x + 1, y + 1), (x, y + 1)]),
                }
            )
    return gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:4326")


class QualitativeValidationTestCase(unittest.TestCase):
    def test_extract_candidate_components_returns_hotspots_and_coldspots_without_combined_index(self) -> None:
        surface = _build_grid_surface("Almaty")
        candidate_table, candidate_geometries = extract_candidate_components(
            surface,
            city_slug="almaty",
            hotspot_quantile=0.90,
            coldspot_quantile=0.10,
            minimum_component_cells=3,
            top_components_per_zone=5,
        )
        self.assertFalse(candidate_table.empty)
        self.assertNotIn("Combined_Index", candidate_table.columns)
        self.assertIn("hotspot", set(candidate_table["zone_type"]))
        self.assertIn("coldspot", set(candidate_table["zone_type"]))
        self.assertEqual(set(candidate_table["source_component_id"]), set(candidate_geometries["source_component_id"]))

    def test_validate_registry_rejects_missing_required_case_ids(self) -> None:
        candidate_table = pd.DataFrame(
            [
                {"source_component_id": "hotspot_01"},
                {"source_component_id": "hotspot_02"},
                {"source_component_id": "coldspot_01"},
                {"source_component_id": "coldspot_02"},
            ]
        )
        registry = pd.DataFrame(
            [
                {
                    "city_slug": "almaty",
                    "zone_type": "hotspot",
                    "case_id": "H1",
                    "source_component_id": "hotspot_01",
                    "case_title": "Case 1",
                    "interpretation_label": "dense residential",
                    "include_in_report": True,
                    "narrative_summary": "Summary",
                    "caution_note": "Caution",
                },
                {
                    "city_slug": "almaty",
                    "zone_type": "hotspot",
                    "case_id": "H2",
                    "source_component_id": "hotspot_02",
                    "case_title": "Case 2",
                    "interpretation_label": "dense residential",
                    "include_in_report": True,
                    "narrative_summary": "Summary",
                    "caution_note": "Caution",
                },
                {
                    "city_slug": "almaty",
                    "zone_type": "coldspot",
                    "case_id": "L1",
                    "source_component_id": "coldspot_01",
                    "case_title": "Case 3",
                    "interpretation_label": "open fringe",
                    "include_in_report": True,
                    "narrative_summary": "Summary",
                    "caution_note": "Caution",
                },
            ]
        )
        with self.assertRaisesRegex(ValueError, "exactly 4 cases"):
            validate_registry(
                registry,
                candidate_tables_by_city={"almaty": candidate_table},
                city_slugs=("almaty",),
            )

    def test_render_writes_expected_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            full_dir = root / "full"
            built_dir = root / "built"
            full_dir.mkdir()
            built_dir.mkdir()
            for city_slug, city_name in (("almaty", "Almaty"), ("astana", "Astana")):
                full_surface = _build_grid_surface(city_name)
                built_surface = full_surface.copy()
                built_surface["Population_Estimate_Final"] = built_surface["Population_Estimate_Final"] * 0.9
                full_surface.to_file(full_dir / f"{city_slug}__random_forest.geojson", driver="GeoJSON")
                built_surface.to_file(built_dir / f"{city_slug}__random_forest.geojson", driver="GeoJSON")

            completeness_csv = root / "completeness.csv"
            pd.DataFrame(
                [
                    {"city_name": "Almaty", "completeness_score": 75.8, "completeness_label": "good"},
                    {"city_name": "Astana", "completeness_score": 65.0, "completeness_label": "moderate"},
                ]
            ).to_csv(completeness_csv, index=False)

            output_dir = root / "report"
            registry_csv = root / "registry.csv"
            config = QualitativeValidationConfig(
                full_inference_dir=full_dir,
                built_form_inference_dir=built_dir,
                completeness_csv=completeness_csv,
                registry_csv=registry_csv,
                output_dir=output_dir,
            )
            run_qualitative_scaffold(config)

            registry = pd.read_csv(registry_csv)
            selected_rows: list[dict[str, object]] = []
            for city_slug in ("almaty", "astana"):
                city_rows = registry.loc[registry["city_slug"] == city_slug].copy()
                hotspots = city_rows.loc[city_rows["zone_type"] == "hotspot"].head(2).copy().reset_index(drop=True)
                coldspots = city_rows.loc[city_rows["zone_type"] == "coldspot"].head(2).copy().reset_index(drop=True)
                for frame, case_ids, label in (
                    (hotspots, ("H1", "H2"), "dense built-form hotspot"),
                    (coldspots, ("L1", "L2"), "peripheral open coldspot"),
                ):
                    for idx, case_id in enumerate(case_ids):
                        row = frame.iloc[idx].to_dict()
                        row["case_id"] = case_id
                        row["include_in_report"] = True
                        row["case_title"] = f"{city_slug.title()} {case_id}"
                        row["interpretation_label"] = label
                        row["narrative_summary"] = f"{case_id} summary for {city_slug}"
                        row["caution_note"] = f"{case_id} caution for {city_slug}"
                        selected_rows.append(row)
            pd.DataFrame(selected_rows).to_csv(registry_csv, index=False)

            outputs = run_qualitative_render(config)
            self.assertTrue(outputs["summary_csv_path"].exists())
            self.assertTrue(outputs["report_path"].exists())
            self.assertTrue(outputs["almaty_overview_figure_path"].exists())
            self.assertTrue(outputs["astana_overview_figure_path"].exists())
            self.assertTrue(outputs["almaty_cases_figure_path"].exists())
            self.assertTrue(outputs["astana_cases_figure_path"].exists())

    def test_cli_scaffold_and_render_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            full_dir = root / "full"
            built_dir = root / "built"
            full_dir.mkdir()
            built_dir.mkdir()
            for city_slug, city_name in (("almaty", "Almaty"), ("astana", "Astana")):
                surface = _build_grid_surface(city_name)
                surface.to_file(full_dir / f"{city_slug}__random_forest.geojson", driver="GeoJSON")
                built = surface.copy()
                built["Population_Estimate_Final"] = built["Population_Estimate_Final"] * 0.85
                built.to_file(built_dir / f"{city_slug}__random_forest.geojson", driver="GeoJSON")
            completeness_csv = root / "completeness.csv"
            pd.DataFrame(
                [
                    {"city_name": "Almaty", "completeness_score": 75.8, "completeness_label": "good"},
                    {"city_name": "Astana", "completeness_score": 65.0, "completeness_label": "moderate"},
                ]
            ).to_csv(completeness_csv, index=False)

            registry_csv = root / "registry.csv"
            output_dir = root / "report"
            script = Path.cwd() / "scripts" / "run_qualitative_validation_v2.py"

            scaffold = subprocess.run(
                [
                    sys.executable,
                    str(script),
                    "--stage",
                    "scaffold",
                    "--full-inference-dir",
                    str(full_dir),
                    "--built-form-inference-dir",
                    str(built_dir),
                    "--completeness-csv",
                    str(completeness_csv),
                    "--registry-csv",
                    str(registry_csv),
                    "--output-dir",
                    str(output_dir),
                ],
                capture_output=True,
                text=True,
                check=False,
                cwd=Path.cwd(),
            )
            self.assertEqual(scaffold.returncode, 0, msg=scaffold.stderr)
            self.assertTrue(registry_csv.exists())

            registry = pd.read_csv(registry_csv)
            selected_rows: list[dict[str, object]] = []
            for city_slug in ("almaty", "astana"):
                city_rows = registry.loc[registry["city_slug"] == city_slug].copy()
                for frame, case_ids, label in (
                    (city_rows.loc[city_rows["zone_type"] == "hotspot"].head(2).reset_index(drop=True), ("H1", "H2"), "dense hotspot"),
                    (city_rows.loc[city_rows["zone_type"] == "coldspot"].head(2).reset_index(drop=True), ("L1", "L2"), "cold fringe"),
                ):
                    for idx, case_id in enumerate(case_ids):
                        row = frame.iloc[idx].to_dict()
                        row["case_id"] = case_id
                        row["include_in_report"] = True
                        row["case_title"] = f"{city_slug.title()} {case_id}"
                        row["interpretation_label"] = label
                        row["narrative_summary"] = f"{case_id} summary"
                        row["caution_note"] = f"{case_id} caution"
                        selected_rows.append(row)
            pd.DataFrame(selected_rows).to_csv(registry_csv, index=False)

            render = subprocess.run(
                [
                    sys.executable,
                    str(script),
                    "--stage",
                    "render",
                    "--full-inference-dir",
                    str(full_dir),
                    "--built-form-inference-dir",
                    str(built_dir),
                    "--completeness-csv",
                    str(completeness_csv),
                    "--registry-csv",
                    str(registry_csv),
                    "--output-dir",
                    str(output_dir),
                ],
                capture_output=True,
                text=True,
                check=False,
                cwd=Path.cwd(),
            )
            self.assertEqual(render.returncode, 0, msg=render.stderr)
            self.assertTrue((output_dir / "qualitative_validation_report.md").exists())


if __name__ == "__main__":
    unittest.main()
