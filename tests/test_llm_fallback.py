from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from city1.llm_fallback import (  # noqa: E402
    check_text_for_overclaims,
    generate_fallback_response,
    get_fallback_capabilities,
)
from city1.llm_guardrails import guard_response  # noqa: E402


class LlmFallbackTests(unittest.TestCase):
    def test_almaty_city_brief_uses_fallback(self) -> None:
        result = generate_fallback_response(city="Almaty", mode="city_brief")
        self.assertTrue(result["fallback_used"])
        self.assertEqual(result["mode"], "city_brief")
        self.assertEqual(result["city"], "Almaty")
        self.assertTrue(result["evidence_used"])

    def test_almaty_answer_is_proxy_and_screening_bounded(self) -> None:
        result = generate_fallback_response(city="Almaty", mode="city_brief")
        answer = result["answer"].lower()
        self.assertIn("proxy", answer)
        self.assertIn("screening", answer)
        self.assertNotIn("reconstructs true cell-level census", answer)
        self.assertNotIn("verified hotspot truth.", answer.replace("not verified hotspot truth.", ""))

    def test_russian_city_brief(self) -> None:
        result = generate_fallback_response(city="Almaty", mode="city_brief", language="ru")
        self.assertEqual(result["language"], "ru")
        self.assertIn("Краткий вывод", result["answer"])
        self.assertIn("не probability of correctness", result["answer"])

    def test_hotspot_review_marks_classes_as_not_verified_truth(self) -> None:
        result = generate_fallback_response(city="Almaty", mode="hotspot_review")
        self.assertIn("not verified hotspot truth", result["answer"])
        self.assertIn("high_value_high_confidence", result["answer"])

    def test_confidence_summary_is_not_probability(self) -> None:
        result = generate_fallback_response(city="Almaty", mode="confidence_summary")
        self.assertIn("confidence_score is not a probability", result["answer"])

    def test_uncertainty_summary_is_not_true_census_uncertainty(self) -> None:
        result = generate_fallback_response(city="Almaty", mode="uncertainty_summary")
        self.assertIn("not true census uncertainty", result["answer"])
        self.assertIn("P10/P50/P90", result["answer"])

    def test_partial_city_is_explicitly_limited(self) -> None:
        result = generate_fallback_response(city="Kurchatov", mode="city_brief")
        self.assertEqual(result["confidence_of_answer"], "low")
        self.assertIn("partial", result["answer"].lower())
        self.assertIn("frozen full-v3 evidence", result["answer"].lower())

    def test_unknown_city_does_not_crash(self) -> None:
        result = generate_fallback_response(city="Unknown Example City", mode="city_brief")
        self.assertEqual(result["confidence_of_answer"], "low")
        self.assertIn("not present", result["answer"])

    def test_comparison_avoids_truth_accuracy_ranking(self) -> None:
        result = generate_fallback_response(mode="compare_cities", cities=["Almaty", "Astana"])
        self.assertEqual(result["mode"], "compare_cities")
        self.assertIn("interpretation support", result["answer"])
        self.assertIn("does not mean", result["answer"])
        self.assertNotIn("more accurately predicted against true population.", result["structured_sections"]["summary"])

    def test_missing_cell_id_is_graceful(self) -> None:
        result = generate_fallback_response(city="Almaty", mode="explain_cell")
        self.assertIn("not found", result["answer"])
        self.assertTrue(result["recommended_next_checks"])

    def test_reviewer_safe_policy_question_uses_direct_conservative_answer(self) -> None:
        question = "Can City1 v4 be used as official census evidence for policy decisions?"
        result = generate_fallback_response(
            city="Almaty",
            mode="reviewer_safe",
            question=question,
        )
        answer = result["answer"]
        self.assertIn("No.", answer)
        self.assertIn("should not be used as official census evidence", answer)
        self.assertIn("calibrated proxy", answer)
        self.assertIn("not true cell-level census", answer)
        self.assertTrue(
            "not automated policy decisions" in answer
            or "not justify automated policy decisions" in answer
        )
        guarded = guard_response(result)
        self.assertTrue(guarded["guardrail"]["passed"])

    def test_overclaim_checker_detects_dangerous_phrases(self) -> None:
        result = check_text_for_overclaims(
            "The system reconstructs true census population and WorldPop is ground truth."
        )
        self.assertTrue(result["has_risk"])
        self.assertIn("true_census", result["risk_phrases"])
        self.assertIn("ground_truth", result["risk_phrases"])
        self.assertIn("calibrated proxy", result["safe_rewrite"])

    def test_public_responses_are_json_serializable(self) -> None:
        calls = [
            lambda: generate_fallback_response(city="Almaty", mode="ask"),
            lambda: generate_fallback_response(city="Almaty", mode="city_brief", language="ru"),
            lambda: generate_fallback_response(city="Almaty", mode="hotspot_review"),
            lambda: generate_fallback_response(city="Almaty", mode="uncertainty_summary"),
            lambda: generate_fallback_response(city="Almaty", mode="confidence_summary"),
            lambda: generate_fallback_response(city="Almaty", mode="explain_cell", cell_id="Z1406"),
            lambda: generate_fallback_response(mode="compare_cities", cities=["Almaty", "Semey"]),
            lambda: generate_fallback_response(question="This is ground truth", mode="claim_checker"),
            lambda: generate_fallback_response(city="Almaty", mode="reviewer_safe"),
            lambda: check_text_for_overclaims("A bounded proxy statement."),
            lambda: get_fallback_capabilities(),
        ]
        for call in calls:
            with self.subTest(call=call):
                json.dumps(call(), ensure_ascii=False)


if __name__ == "__main__":
    unittest.main()
