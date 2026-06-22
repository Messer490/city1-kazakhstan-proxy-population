from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from city1.llm_fallback import generate_fallback_response  # noqa: E402
from city1.llm_guardrails import (  # noqa: E402
    check_answer_for_forbidden_claims,
    check_response_dict,
    get_guardrail_capabilities,
    get_guardrail_rules,
    guard_response,
    rewrite_unsafe_answer,
    validate_evidence_grounding,
)


class LlmGuardrailTests(unittest.TestCase):
    def test_safe_text_passes(self) -> None:
        result = check_answer_for_forbidden_claims(
            "City1 provides a calibrated proxy population surface for screening. "
            "It is not true census reconstruction and requires manual review."
        )
        self.assertTrue(result["passed"])
        self.assertEqual(result["severity"], "none")

    def test_true_census_reconstruction_is_detected(self) -> None:
        result = check_answer_for_forbidden_claims("This is true census reconstruction.")
        self.assertFalse(result["passed"])
        self.assertEqual(result["violations"][0]["category"], "TRUE_CENSUS_RECONSTRUCTION")
        self.assertEqual(result["severity"], "critical")

    def test_confidence_probability_is_detected(self) -> None:
        result = check_answer_for_forbidden_claims("confidence_score is probability of correctness.")
        categories = {item["category"] for item in result["violations"]}
        self.assertIn("CONFIDENCE_AS_PROBABILITY", categories)

    def test_worldpop_ground_truth_is_detected(self) -> None:
        result = check_answer_for_forbidden_claims("WorldPop is ground truth.")
        categories = {item["category"] for item in result["violations"]}
        self.assertIn("EXTERNAL_PRODUCTS_AS_GROUND_TRUTH", categories)

    def test_verified_hotspot_is_detected(self) -> None:
        result = check_answer_for_forbidden_claims("This cell is a verified hotspot.")
        self.assertEqual(result["violations"][0]["category"], "VERIFIED_HOTSPOT_TRUTH")

    def test_llm_accuracy_claim_is_detected(self) -> None:
        result = check_answer_for_forbidden_claims("LLM improves population prediction accuracy.")
        self.assertEqual(result["violations"][0]["category"], "LLM_IMPROVES_PREDICTION_ACCURACY")
        self.assertEqual(result["severity"], "critical")

    def test_automated_policy_claim_is_detected(self) -> None:
        result = check_answer_for_forbidden_claims("This supports a fully automated policy decision.")
        self.assertEqual(result["violations"][0]["category"], "AUTOMATED_POLICY_DECISION")

    def test_russian_dangerous_phrases_are_detected(self) -> None:
        cases = {
            "Это точное население ячейки.": "TRUE_CENSUS_RECONSTRUCTION",
            "Это истинная неопределённость.": "TRUE_UNCERTAINTY",
            "Это вероятность правильности.": "CONFIDENCE_AS_PROBABILITY",
            "Это подтверждённый hotspot.": "VERIFIED_HOTSPOT_TRUTH",
            "Можно использовать без ручной проверки.": "AUTOMATED_POLICY_DECISION",
            "LLM улучшает точность населения.": "LLM_IMPROVES_PREDICTION_ACCURACY",
        }
        for text, category in cases.items():
            with self.subTest(text=text):
                result = check_answer_for_forbidden_claims(text, language="ru")
                self.assertIn(category, {item["category"] for item in result["violations"]})

    def test_rewrite_uses_safe_terms(self) -> None:
        check = check_answer_for_forbidden_claims(
            "WorldPop is ground truth and this is a verified hotspot."
        )
        rewrite = rewrite_unsafe_answer("unsafe", check["violations"])
        self.assertTrue(rewrite["rewritten"])
        self.assertIn("structural comparators", rewrite["safe_answer"])
        self.assertIn("screening/triage class", rewrite["safe_answer"])
        self.assertTrue(check_answer_for_forbidden_claims(rewrite["safe_answer"])["passed"])

    def test_guard_response_returns_safe_final_response(self) -> None:
        response = generate_fallback_response(city="Almaty", mode="city_brief")
        response["answer"] = "This is true census reconstruction and a verified hotspot."
        guarded = guard_response(response)
        self.assertTrue(guarded["used_safe_rewrite"])
        self.assertFalse(guarded["guardrail"]["passed"])
        self.assertIn("calibrated proxy", guarded["final_response"]["answer"])
        self.assertTrue(check_answer_for_forbidden_claims(guarded["final_response"]["answer"])["passed"])

    def test_grounding_catches_missing_evidence(self) -> None:
        result = validate_evidence_grounding({
            "answer": "A sufficiently long but generic answer that does not cite any frozen local artifact or source.",
            "claim_boundary_notes": ["Use cautiously."],
            "missing_artifacts": [],
        })
        self.assertFalse(result["grounded"])
        self.assertTrue(any("evidence_used" in item for item in result["issues"]))

    def test_real_fallback_response_passes(self) -> None:
        response = generate_fallback_response(city="Almaty", mode="city_brief")
        result = check_response_dict(response)
        self.assertTrue(result["passed"])
        self.assertEqual(result["grounding_score"], 100)
        self.assertFalse(result["violations"])

    def test_guardrail_outputs_are_json_serializable(self) -> None:
        response = generate_fallback_response(city="Almaty", mode="city_brief")
        unsafe = dict(response)
        unsafe["answer"] = "confidence_score is probability and WorldPop is ground truth."
        payloads = [
            get_guardrail_rules(),
            get_guardrail_capabilities(),
            check_answer_for_forbidden_claims("verified hotspot"),
            check_response_dict(response),
            validate_evidence_grounding(response),
            guard_response(unsafe),
        ]
        for payload in payloads:
            json.dumps(payload, ensure_ascii=False)


if __name__ == "__main__":
    unittest.main()
