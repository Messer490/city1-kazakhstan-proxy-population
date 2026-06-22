from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from city1.llm_client import (  # noqa: E402
    build_gemini_prompt,
    estimate_evidence_packet_size,
    generate_llm_response,
    get_gemini_status,
    get_llm_client_capabilities,
    parse_gemini_json_response,
)
from city1.llm_tools import generate_evidence_pack  # noqa: E402


class LlmClientTests(unittest.TestCase):
    def test_status_does_not_crash_without_key(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            result = get_gemini_status()
        self.assertFalse(result["api_key_available"])
        self.assertFalse(result["available"])
        self.assertEqual(result["provider"], "gemini")

    def test_parse_pure_json(self) -> None:
        result = parse_gemini_json_response('{"answer":"bounded proxy answer"}')
        self.assertTrue(result["success"])
        self.assertEqual(result["data"]["answer"], "bounded proxy answer")

    def test_parse_fenced_json(self) -> None:
        result = parse_gemini_json_response(
            "Model response:\n```json\n{\"answer\": \"safe\", \"confidence_of_answer\": \"medium\"}\n```"
        )
        self.assertTrue(result["success"])
        self.assertEqual(result["data"]["answer"], "safe")

    def test_parse_invalid_json_is_graceful(self) -> None:
        result = parse_gemini_json_response("This is not JSON.")
        self.assertFalse(result["success"])
        self.assertIsNone(result["data"])
        self.assertTrue(result["error"])

    def test_fallback_provider_works_without_gemini(self) -> None:
        result = generate_llm_response(city="Almaty", mode="city_brief", provider="fallback", use_cache=False, use_retrieval=False)
        self.assertEqual(result["provider_requested"], "fallback")
        self.assertEqual(result["provider_used"], "fallback")
        self.assertTrue(result["fallback_used"])
        self.assertTrue(result["guardrail"]["passed"])

    def test_gemini_provider_falls_back_without_key(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            result = generate_llm_response(city="Almaty", mode="city_brief", provider="gemini", use_cache=False, use_retrieval=False)
        self.assertEqual(result["provider_requested"], "gemini")
        self.assertEqual(result["provider_used"], "fallback")
        self.assertTrue(result["fallback_used"])
        self.assertFalse(result["gemini"]["success"])
        self.assertTrue(result["gemini"]["error"])

    def test_output_includes_guardrail_metadata(self) -> None:
        result = generate_llm_response(city="Almaty", mode="city_brief", provider="fallback", use_cache=False, use_retrieval=False)
        self.assertIn("guardrail", result)
        self.assertIn("grounding_score", result["guardrail"])
        self.assertIn("used_safe_rewrite", result)

    def test_safe_mocked_gemini_response_is_used(self) -> None:
        mocked = {
            "success": True,
            "provider": "gemini",
            "model": "test-flash",
            "raw_text": "{}",
            "parsed_response": {
                "answer": "Almaty has a calibrated proxy population surface for screening and manual review.",
                "confidence_of_answer": "medium",
                "evidence_used": ["invented-source.csv"],
                "claim_boundary_notes": ["This is not true cell-level census reconstruction."],
                "recommended_next_checks": ["Review local evidence."],
                "structured_sections": {
                    "summary": "Bounded proxy interpretation for Almaty.",
                    "evidence": ["Frozen evidence was used."],
                    "cautions": ["Not census truth."],
                    "next_checks": ["Manual review."],
                },
            },
            "error": None,
            "latency_seconds": 0.12,
            "used_fallback": False,
        }
        with patch("city1.llm_client.call_gemini_structured", return_value=mocked):
            result = generate_llm_response(city="Almaty", mode="city_brief", provider="gemini", use_cache=False, use_retrieval=False)
        self.assertEqual(result["provider_used"], "gemini")
        self.assertFalse(result["fallback_used"])
        self.assertTrue(result["guardrail"]["passed"])
        self.assertNotIn("invented-source.csv", result["evidence_used"])

    def test_unsafe_mocked_gemini_answer_is_rejected_to_fallback(self) -> None:
        mocked = {
            "success": True,
            "provider": "gemini",
            "model": "test-flash",
            "raw_text": "{}",
            "parsed_response": {
                "answer": "City1 provides true census reconstruction and verified hotspots.",
                "confidence_of_answer": "high",
                "claim_boundary_notes": ["Use the result."],
                "recommended_next_checks": [],
                "structured_sections": {
                    "summary": "True census reconstruction.",
                    "evidence": ["Ground truth."],
                    "cautions": [],
                    "next_checks": [],
                },
            },
            "error": None,
            "latency_seconds": 0.1,
            "used_fallback": False,
        }
        with patch("city1.llm_client.call_gemini_structured", return_value=mocked):
            result = generate_llm_response(city="Almaty", mode="city_brief", provider="gemini", use_cache=False, use_retrieval=False)
        self.assertEqual(result["provider_used"], "fallback")
        self.assertTrue(result["fallback_used"])
        self.assertTrue(result["gemini"]["guardrail_rejected"])
        self.assertIn(result["gemini"]["rejection_severity"], {"high", "critical"})
        self.assertTrue(result["guardrail"]["passed"])

    def test_prompt_is_compact_and_excludes_raw_paths(self) -> None:
        pack = generate_evidence_pack("Almaty", mode="city_brief")
        prompt = build_gemini_prompt(pack, "Summarize Almaty", "city_brief")
        size = estimate_evidence_packet_size(pack)
        self.assertIn("not a population model", prompt["system_instruction"])
        self.assertNotIn(str(ROOT), prompt["user_prompt"])
        self.assertLess(size["character_count"], size["warning_threshold_characters"])

    def test_outputs_are_json_serializable(self) -> None:
        pack = generate_evidence_pack("Almaty", mode="city_brief")
        payloads = [
            get_gemini_status(),
            get_llm_client_capabilities(),
            build_gemini_prompt(pack, "Question", "ask"),
            estimate_evidence_packet_size(pack),
            parse_gemini_json_response('{"answer":"safe"}'),
            generate_llm_response(city="Almaty", mode="city_brief", provider="fallback", use_cache=False, use_retrieval=False),
        ]
        for payload in payloads:
            json.dumps(payload, ensure_ascii=False)


if __name__ == "__main__":
    unittest.main()
