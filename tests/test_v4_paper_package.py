from __future__ import annotations

import csv
import hashlib
import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "build_v4_paper_package.py"
SPEC = importlib.util.spec_from_file_location("build_v4_paper_package", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Could not load build_v4_paper_package.py")
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class V4PaperPackageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "data" / "v4_eval").mkdir(parents=True)
        (self.root / "reports" / "v4_llm_evaluation").mkdir(parents=True)
        (self.root / "docs").mkdir(parents=True)
        self.frozen = self.root / "manuscript_package_city1_unified" / "frozen.txt"
        self.frozen.parent.mkdir(parents=True)
        self.frozen.write_text("frozen-v2-v3-context", encoding="utf-8")
        self.frozen_hash = hashlib.sha256(self.frozen.read_bytes()).hexdigest()

        (self.root / "data" / "v4_eval" / "question_bank.csv").write_text(
            "question_id,category,city,mode,language,question,expected_risk_level,expected_evidence_type,must_mention,forbidden_claim_trigger,notes\n"
            "Q001,city_overview,Almaty,city_brief,en,Summary,none,city_summary,proxy,,test\n"
            "Q002,russian_language,Almaty,claim_checker,ru,Claim,high,claim_boundary,proxy,TRUE_CENSUS_RECONSTRUCTION,test\n",
            encoding="utf-8",
        )
        (self.root / "reports" / "v4_llm_evaluation" / "evaluation_summary.csv").write_text(
            "config,question_count,claim_boundary_violation_rate,critical_violation_rate,evidence_usage_rate,grounding_score_mean,fallback_rate,cache_hit_rate,missing_artifact_rate,answer_completeness_score_mean,limitation_awareness_score_mean,unsafe_phrase_count_after_total\n"
            "fallback_only,2,0.5,0.0,1.0,100.0,1.0,0.0,0.0,0.9,0.8,0\n",
            encoding="utf-8",
        )
        (self.root / "reports" / "v4_llm_evaluation" / "per_question_results.csv").write_text(
            "question_id,config,cache_hit,unsafe_phrase_count_after\n"
            "Q001,fallback_only,False,0\nQ002,fallback_only,False,0\n",
            encoding="utf-8",
        )
        self.result = MODULE.build_v4_paper_package(self.root)
        self.package = self.root / "manuscript_package_v4"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_build_script_imports_and_runs_safely(self) -> None:
        self.assertTrue(callable(MODULE.build_v4_paper_package))
        self.assertFalse(self.result["gemini_required"])
        self.assertFalse(self.result["internet_required"])

    def test_package_exists_after_build(self) -> None:
        self.assertTrue(self.package.is_dir())

    def test_readme_exists(self) -> None:
        self.assertTrue((self.package / "README.md").is_file())

    def test_paper_summary_exists(self) -> None:
        self.assertTrue((self.package / "V4_PAPER_SUMMARY.md").is_file())

    def test_contribution_map_exists(self) -> None:
        self.assertTrue((self.package / "tables" / "table_v4_contribution_map.csv").is_file())

    def test_evaluation_summary_table_exists_when_source_exists(self) -> None:
        path = self.package / "tables" / "table_v4_evaluation_summary.csv"
        self.assertTrue(path.is_file())
        with path.open(encoding="utf-8", newline="") as handle:
            self.assertEqual(len(list(csv.DictReader(handle))), 1)

    def test_claim_boundary_summary_includes_forbidden_claims(self) -> None:
        text = (self.package / "V4_CLAIM_BOUNDARY_SUMMARY.md").read_text(encoding="utf-8")
        self.assertIn("Forbidden Claims", text)
        self.assertIn("population prediction accuracy", text)

    def test_reproducibility_checklist_includes_commands(self) -> None:
        text = (self.package / "V4_REPRODUCIBILITY_CHECKLIST.md").read_text(encoding="utf-8")
        self.assertIn("python scripts/run_v4_llm_evaluation.py --no-gemini", text)
        self.assertIn("python scripts/build_v4_paper_package.py", text)

    def test_package_files_are_not_empty(self) -> None:
        files = [path for path in self.package.rglob("*") if path.is_file()]
        self.assertGreaterEqual(len(files), 30)
        self.assertTrue(all(path.stat().st_size > 0 for path in files))

    def test_generated_csvs_have_expected_columns(self) -> None:
        expected = {
            "table_v4_contribution_map.csv": {"contribution_id", "contribution", "evidence_file", "paper_section", "claim_boundary"},
            "table_v4_modes.csv": {"mode", "purpose", "input", "evidence_tools", "output", "limitations"},
            "table_v4_evaluation_summary.csv": {"configuration", "cases", "evidence_usage_rate", "unsafe_phrases_after"},
        }
        for name, columns in expected.items():
            with self.subTest(name=name):
                with (self.package / "tables" / name).open(encoding="utf-8", newline="") as handle:
                    header = set(next(csv.reader(handle)))
                self.assertTrue(columns.issubset(header))

    def test_build_does_not_require_gemini_key(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            result = MODULE.build_v4_paper_package(self.root)
        self.assertFalse(result["gemini_required"])

    def test_builder_does_not_touch_frozen_directories(self) -> None:
        before = hashlib.sha256(self.frozen.read_bytes()).hexdigest()
        MODULE.build_v4_paper_package(self.root)
        after = hashlib.sha256(self.frozen.read_bytes()).hexdigest()
        self.assertEqual(before, self.frozen_hash)
        self.assertEqual(after, self.frozen_hash)

    def test_missing_evaluation_artifacts_are_handled_gracefully(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            empty_root = Path(temp)
            result = MODULE.build_v4_paper_package(empty_root)
            table = empty_root / "manuscript_package_v4" / "tables" / "table_v4_evaluation_summary.csv"
            self.assertFalse(result["evaluation_available"])
            self.assertTrue(table.is_file())
            with table.open(encoding="utf-8", newline="") as handle:
                self.assertIsNotNone(next(csv.reader(handle), None))


if __name__ == "__main__":
    unittest.main()
