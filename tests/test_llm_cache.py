from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from city1.llm_cache import (  # noqa: E402
    augment_evidence_pack_with_retrieval,
    build_city1_retrieval_corpus,
    compute_evidence_hash,
    compute_response_hash,
    get_cache_status,
    lookup_cached_response,
    make_cache_key,
    normalize_question,
    retrieve_city1_snippets,
    store_cached_response,
)
from city1.llm_client import generate_llm_response  # noqa: E402
from city1.llm_tools import generate_evidence_pack  # noqa: E402


class LlmCacheTests(unittest.TestCase):
    def setUp(self) -> None:
        self.pack = generate_evidence_pack("Almaty", question="Summarize confidence", mode="city_brief")
        self.response = generate_llm_response(
            city="Almaty",
            question="Summarize confidence",
            mode="city_brief",
            provider="fallback",
            use_cache=False,
            use_retrieval=False,
        )

    def test_normalize_question_is_stable(self) -> None:
        self.assertEqual(
            normalize_question("  Explain   CONFIDENCE_score / P10-P90?  "),
            "explain confidence_score / p10-p90",
        )

    def test_evidence_hash_is_stable_and_ignores_question(self) -> None:
        first = compute_evidence_hash(self.pack)
        changed_question = dict(self.pack)
        changed_question["question"] = "A similar rephrased question"
        self.assertEqual(first, compute_evidence_hash(changed_question))
        self.assertEqual(first, compute_evidence_hash(self.pack))

    def test_cache_key_is_deterministic(self) -> None:
        evidence_hash = compute_evidence_hash(self.pack)
        first = make_cache_key("Almaty", "city_brief", "en", "Question", evidence_hash)
        second = make_cache_key(" almaty ", "CITY_BRIEF", "EN", "  question  ", evidence_hash)
        self.assertEqual(first, second)

    def test_store_and_exact_lookup_safe_response(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            stored = store_cached_response(
                self.response, self.pack, "Summarize confidence", "Almaty", "city_brief", "en", temp
            )
            self.assertTrue(stored["stored"])
            lookup = lookup_cached_response(
                "Almaty", "city_brief", "en", "Summarize confidence", self.pack, temp
            )
            self.assertTrue(lookup["hit"])
            self.assertEqual(lookup["match_type"], "exact")
            self.assertIn("calibrated proxy", lookup["cached_response"]["answer"])

    def test_critical_response_is_not_cached(self) -> None:
        unsafe = dict(self.response)
        unsafe["guardrail"] = dict(unsafe["guardrail"])
        unsafe["guardrail"].update({"passed": False, "severity": "critical"})
        unsafe["answer"] = "This is true census reconstruction."
        with tempfile.TemporaryDirectory() as temp:
            result = store_cached_response(
                unsafe, self.pack, "Unsafe", "Almaty", "city_brief", "en", temp
            )
            self.assertFalse(result["stored"])
            self.assertEqual(get_cache_status(temp)["entry_count"], 0)

    def test_unknown_cache_directory_is_created_safely(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            nested = Path(temp) / "new" / "cache"
            result = store_cached_response(
                self.response, self.pack, "Question", "Almaty", "city_brief", "en", nested
            )
            self.assertTrue(result["stored"])
            self.assertTrue((nested / "cache_index.jsonl").exists())
            self.assertTrue((nested / "cached_answers").is_dir())

    def test_retrieval_corpus_builds_without_internet(self) -> None:
        corpus = build_city1_retrieval_corpus()
        self.assertGreater(corpus["entry_count"], 20)
        self.assertFalse(corpus["internet_used"])
        self.assertTrue(any(item["category"] == "claim_boundary" for item in corpus["entries"]))

    def test_retrieval_finds_confidence_probability_evidence(self) -> None:
        result = retrieve_city1_snippets("confidence_score probability", city="Almaty", top_k=5)
        self.assertTrue(result["results"])
        joined = " ".join(item["snippet"] for item in result["results"]).lower()
        self.assertIn("confidence_score", joined)
        self.assertIn(result["method"], {"exact", "difflib"})
        self.assertFalse(result["internet_used"])

    def test_augment_pack_adds_compact_snippets(self) -> None:
        augmented = augment_evidence_pack_with_retrieval(
            self.pack, "Explain confidence_score", city="Almaty", top_k=3
        )
        self.assertLessEqual(len(augmented["retrieved_snippets"]), 3)
        self.assertTrue(augmented["retrieval_sources"])
        self.assertIn("no internet", augmented["retrieval_note"].lower())

    def test_llm_response_returns_cache_on_second_call(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            first = generate_llm_response(
                city="Almaty", question="Summarize confidence", mode="city_brief",
                provider="fallback", cache_dir=temp, use_cache=True, use_retrieval=True,
            )
            second = generate_llm_response(
                city="Almaty", question="Summarize confidence", mode="city_brief",
                provider="fallback", cache_dir=temp, use_cache=True, use_retrieval=True,
            )
            self.assertFalse(first["cache_hit"])
            self.assertEqual(second["provider_used"], "cache")
            self.assertTrue(second["cache_hit"])
            self.assertEqual(second["cache_metadata"]["match_type"], "exact")

    def test_hashes_and_outputs_are_json_serializable(self) -> None:
        payloads = [
            {"evidence_hash": compute_evidence_hash(self.pack)},
            {"response_hash": compute_response_hash(self.response)},
            get_cache_status(Path(tempfile.gettempdir()) / "city1_nonexistent_cache_status"),
            retrieve_city1_snippets("proxy interval", top_k=2),
        ]
        for payload in payloads:
            json.dumps(payload, ensure_ascii=False)


if __name__ == "__main__":
    unittest.main()
