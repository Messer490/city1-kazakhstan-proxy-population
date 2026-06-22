from __future__ import annotations

import json
import unittest

from city1.llm_tools import (
    compare_cities,
    generate_evidence_pack,
    get_available_cities,
    get_cell_evidence,
    get_city_summary,
    get_claim_boundaries,
    get_confidence_summary,
    get_hotspot_summary,
    get_method_summary,
    get_uncertainty_summary,
)


class LlmToolsTests(unittest.TestCase):
    def test_available_cities_contains_full_v3_set(self) -> None:
        result = get_available_cities()
        self.assertEqual(set(result["full_v3_cities"]), {"Almaty", "Astana", "Semey", "Shymkent"})
        self.assertTrue(result["run_id"])
        self.assertTrue(result["evidence_sources"])

    def test_almaty_city_summary_has_full_v3_support(self) -> None:
        result = get_city_summary("Almaty")
        self.assertEqual(result["support_level"], "full_v3")
        self.assertEqual(result["official_total"], 2351424)
        self.assertIsNotNone(result["median_relative_uncertainty"])

    def test_basic_and_partial_cities_are_graceful(self) -> None:
        basic = get_city_summary("Taraz")
        partial = get_city_summary("Kurchatov")
        self.assertEqual(basic["support_level"], "v2_basic")
        self.assertIsNotNone(basic["official_total"])
        self.assertIsNone(basic["median_relative_uncertainty"])
        self.assertEqual(partial["support_level"], "partial")

    def test_hotspot_summary_uses_screening_wording(self) -> None:
        result = get_hotspot_summary("Almaty", top_n=3)
        self.assertEqual(result["total_priority_cells"], 842)
        self.assertEqual(len(result["top_hotspots"]), 3)
        self.assertIn("screening", result["claim_boundary"].lower())
        self.assertTrue(result["evidence_sources"])

    def test_confidence_is_not_probability(self) -> None:
        result = get_confidence_summary("Almaty")
        self.assertIn("not a probability", result["claim_boundary"])
        self.assertTrue({"high", "medium", "low"}.issubset(result["bands"]))

    def test_intervals_are_not_true_census_uncertainty(self) -> None:
        result = get_uncertainty_summary("Almaty")
        self.assertIn("not true census uncertainty", result["claim_boundary"])
        self.assertIsNotNone(result["weak_target_interval_coverage"])

    def test_claim_boundaries_return_forbidden_claims(self) -> None:
        result = get_claim_boundaries()
        self.assertTrue(result["forbidden_claims"])
        self.assertTrue(any("probability" in claim for claim in result["forbidden_claims"]))

    def test_city_brief_pack_contains_evidence_and_boundaries(self) -> None:
        result = generate_evidence_pack("Almaty", mode="city_brief")
        self.assertEqual(result["city_summary"]["support_level"], "full_v3")
        self.assertTrue(result["claim_boundaries"]["forbidden_claims"])
        self.assertEqual(result["hotspot_summary"]["total_priority_cells"], 842)
        self.assertEqual(result["token_saving_note"], "compact evidence packet only")

    def test_unknown_city_does_not_raise(self) -> None:
        result = get_city_summary("Unknown Example City")
        self.assertEqual(result["support_level"], "unknown")
        self.assertIsNone(result["official_total"])
        self.assertTrue(result["interpretation"]["caution"])

    def test_missing_cell_is_graceful(self) -> None:
        result = get_cell_evidence("Almaty", "DOES_NOT_EXIST")
        self.assertFalse(result["found"])
        self.assertTrue(result["available_alternative"])

    def test_public_functions_are_json_serializable(self) -> None:
        calls = [
            lambda: get_available_cities(),
            lambda: get_city_summary("Almaty"),
            lambda: get_hotspot_summary("Almaty", top_n=2),
            lambda: get_confidence_summary("Almaty"),
            lambda: get_uncertainty_summary("Almaty"),
            lambda: get_cell_evidence("Almaty", "Z1406"),
            lambda: compare_cities(["Almaty", "Astana"]),
            lambda: get_claim_boundaries(),
            lambda: get_method_summary(),
            lambda: generate_evidence_pack("Almaty", mode="city_brief"),
        ]
        for call in calls:
            with self.subTest(call=call):
                json.dumps(call(), ensure_ascii=False)


if __name__ == "__main__":
    unittest.main()
