from __future__ import annotations

import csv
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from city1.llm_evaluation import (  # noqa: E402
    DEFAULT_CONFIGS,
    REQUIRED_QUESTION_COLUMNS,
    aggregate_results,
    generate_markdown_report,
    load_question_bank,
    run_evaluation,
    run_single_evaluation_case,
    score_answer,
    validate_question_bank,
)


QUESTION_BANK = ROOT / "data" / "v4_eval" / "question_bank.csv"


class LlmEvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rows = load_question_bank(QUESTION_BANK)

    def test_question_bank_loads_with_required_size(self) -> None:
        self.assertGreaterEqual(len(self.rows), 60)
        self.assertLessEqual(len(self.rows), 100)

    def test_question_bank_validates_required_columns(self) -> None:
        validation = validate_question_bank(self.rows)
        self.assertTrue(validation["valid"], validation)
        self.assertFalse(validation["missing_columns"])
        self.assertTrue(set(REQUIRED_QUESTION_COLUMNS).issubset(self.rows[0]))

    def test_one_fallback_only_case_runs(self) -> None:
        result = run_single_evaluation_case(self.rows[0], DEFAULT_CONFIGS["fallback_only"])
        self.assertEqual(result["provider_used"], "fallback")
        self.assertTrue(result["fallback_used"])
        self.assertTrue(result["guardrail_passed"])
        self.assertTrue(result["evidence_usage"])

    def test_dangerous_overclaim_case_is_detected(self) -> None:
        case = next(row for row in self.rows if row["question_id"] == "Q031")
        result = run_single_evaluation_case(case, DEFAULT_CONFIGS["claim_checker_only"])
        self.assertGreater(result["unsafe_phrase_count_before"], 0)
        self.assertIn(result["guardrail_severity"], {"medium", "high", "critical"})

    def test_scoring_includes_evidence_and_limitation_awareness(self) -> None:
        case = next(row for row in self.rows if row["question_id"] == "Q030")
        response = {
            "answer": "This calibrated proxy is not true cell-level census and requires manual review.",
            "evidence_used": ["frozen-summary.csv"],
            "missing_artifacts": [],
            "fallback_used": True,
            "cache_hit": False,
            "structured_sections": {
                "summary": "Bounded result.",
                "evidence": ["Frozen evidence."],
                "cautions": ["Not census truth."],
                "next_checks": ["Manual review."],
            },
            "guardrail": {"severity": "none", "risk_score": 0, "grounding_score": 100},
        }
        scores = score_answer(case, response)
        self.assertTrue(scores["evidence_usage"])
        self.assertGreater(scores["limitation_awareness_score"], 0)
        self.assertGreater(scores["answer_completeness_score"], 0.5)

    def test_aggregation_computes_required_rates(self) -> None:
        rows = [
            {"config": "a", "claim_boundary_violation": True, "critical_violation": False,
             "evidence_usage": True, "grounding_score": 100, "fallback_used": True,
             "cache_hit": False, "missing_artifact": False, "answer_completeness_score": 1,
             "limitation_awareness_score": 1, "unsafe_phrase_count": 1,
             "unsafe_phrase_count_after": 0, "latency_seconds": 0.1,
             "answer_character_count": 100, "evidence_packet_character_count": 200},
            {"config": "a", "claim_boundary_violation": False, "critical_violation": False,
             "evidence_usage": False, "grounding_score": 50, "fallback_used": True,
             "cache_hit": True, "missing_artifact": True, "answer_completeness_score": 0.5,
             "limitation_awareness_score": 0.5, "unsafe_phrase_count": 0,
             "unsafe_phrase_count_after": 0, "latency_seconds": 0.3,
             "answer_character_count": 50, "evidence_packet_character_count": 100},
        ]
        summary = aggregate_results(rows)["by_config"][0]
        self.assertEqual(summary["claim_boundary_violation_rate"], 0.5)
        self.assertEqual(summary["evidence_usage_rate"], 0.5)
        self.assertEqual(summary["cache_hit_rate"], 0.5)

    def test_markdown_report_generation_works(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "report.md"
            result = generate_markdown_report({"by_config": []}, [], path)
            self.assertTrue(result["written"])
            self.assertIn("does not measure population prediction accuracy", path.read_text(encoding="utf-8"))

    def test_core_runner_honors_max_questions_and_writes_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            result = run_evaluation(QUESTION_BANK, ["fallback_only"], temp, max_questions=3)
            self.assertEqual(len(result["per_question_results"]), 3)
            for path in result["output_files"].values():
                self.assertTrue(Path(path).exists())

    def test_outputs_are_json_and_csv_serializable(self) -> None:
        result = run_single_evaluation_case(self.rows[0], DEFAULT_CONFIGS["fallback_only"])
        json.dumps(result, ensure_ascii=False)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "row.csv"
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(result))
                writer.writeheader()
                writer.writerow(result)
            self.assertGreater(path.stat().st_size, 0)

    def test_benchmark_runs_without_gemini_key(self) -> None:
        config = dict(DEFAULT_CONFIGS["gemini_with_fallback"])
        config["disable_gemini"] = True
        with patch.dict(os.environ, {}, clear=True):
            result = run_single_evaluation_case(self.rows[0], config)
        self.assertEqual(result["provider_requested"], "gemini")
        self.assertEqual(result["provider_used"], "fallback")
        self.assertFalse(result["gemini_available"])
        self.assertTrue(result["fallback_used"])


if __name__ == "__main__":
    unittest.main()
