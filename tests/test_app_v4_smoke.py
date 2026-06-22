from __future__ import annotations

import json
import unittest

import app_v4


class _FakeStreamlit:
    def __init__(self) -> None:
        self.session_state: dict = {}


class AppV4SmokeTests(unittest.TestCase):
    def test_module_import_is_streamlit_safe(self) -> None:
        self.assertNotIn("streamlit", app_v4.__dict__)
        self.assertTrue(callable(app_v4.main))

    def test_full_v3_cities_are_first(self) -> None:
        options = app_v4.get_ordered_city_options()
        self.assertEqual(options[:4], ["Almaty", "Astana", "Semey", "Shymkent"])
        self.assertIn("Kurchatov", options)

    def test_custom_city_resolution(self) -> None:
        self.assertEqual(app_v4.resolve_selected_city("Almaty", "Example City", True), "Example City")
        self.assertEqual(app_v4.resolve_selected_city("Almaty", "", True), "Almaty")

    def test_session_state_defaults_are_initialized(self) -> None:
        fake = _FakeStreamlit()
        app_v4._initialize_session_state(fake)
        self.assertIn("last_response", fake.session_state)
        self.assertIn("last_question", fake.session_state)
        self.assertIn("selected_city", fake.session_state)
        self.assertIn("selected_mode", fake.session_state)
        self.assertIn("selected_language", fake.session_state)
        self.assertIn("generated_report_md", fake.session_state)

    def test_almaty_overview_uses_frozen_evidence(self) -> None:
        overview = app_v4.get_city_overview("Almaty")
        self.assertEqual(overview["support_level"], "full_v3")
        self.assertEqual(overview["official_total"], 2351424)
        self.assertEqual(overview["priority_cells"], 842)

    def test_backend_wrapper_generates_russian_brief(self) -> None:
        response = app_v4.run_local_assistant(
            city="Almaty",
            mode="Generate City Brief",
            language="Russian",
        )
        self.assertTrue(response["fallback_used"])
        self.assertEqual(response["language"], "ru")
        self.assertTrue(response["evidence_used"])

    def test_backend_wrapper_handles_claim_checker(self) -> None:
        response = app_v4.run_local_assistant(
            city="Almaty",
            mode="Claim Checker",
            language="English",
            question="This is true census ground truth.",
        )
        self.assertTrue(response["fallback_used"])
        self.assertTrue(response["has_risk"])

    def test_markdown_report_contains_required_sections(self) -> None:
        response = app_v4.run_local_assistant(
            city="Almaty",
            mode="city_brief",
            language="en",
            question="Summarize the evidence.",
        )
        report = app_v4.build_markdown_report(
            response,
            city="Almaty",
            mode="Generate City Brief",
            question="Summarize the evidence.",
        )
        self.assertIn("# City1 v4 Interpretation Report", report)
        self.assertIn("## Evidence used", report)
        self.assertIn("## Claim-boundary notes", report)
        self.assertIn("Scientific disclaimer", report)
        self.assertIn("local fallback engine", report)

    def test_helper_outputs_are_json_serializable(self) -> None:
        payloads = [
            app_v4.get_city_overview("Kurchatov"),
            app_v4.get_city_overview("Unknown Example City"),
            app_v4.run_local_assistant(city="Almaty", mode="hotspot_review", language="en"),
            app_v4.run_local_assistant(
                city="Almaty",
                mode="compare_cities",
                language="en",
                cities=["Almaty", "Astana"],
            ),
            app_v4.run_local_assistant(
                city="Almaty",
                mode="explain_cell",
                language="en",
                cell_id=None,
            ),
        ]
        for payload in payloads:
            json.dumps(payload, ensure_ascii=False)


if __name__ == "__main__":
    unittest.main()
