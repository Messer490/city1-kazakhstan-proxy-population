from __future__ import annotations

import json
import unittest

import app_v4


class _FakeStreamlit:
    def __init__(self) -> None:
        self.session_state: dict = {}


class _StyleCapture:
    def __init__(self) -> None:
        self.content = ""

    def markdown(self, content: str, **_: object) -> None:
        self.content = content


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
        self.assertIn("last_guardrail", fake.session_state)
        self.assertEqual(fake.session_state["selected_provider"], "Local fallback only")

    def test_all_nine_modes_have_readable_help_text(self) -> None:
        self.assertEqual(len(app_v4.MODE_LABEL_TO_KEY), 9)
        for mode in app_v4.MODE_LABEL_TO_KEY.values():
            with self.subTest(mode=mode):
                self.assertGreater(len(app_v4._mode_help_text(mode)), 20)
        self.assertEqual(
            app_v4._mode_help_text("ask"),
            "Answer a free-form question using City1 evidence.",
        )
        self.assertEqual(
            app_v4._mode_help_text("reviewer_safe"),
            "Generate conservative paper-safe wording.",
        )

    def test_how_to_use_card_contains_required_steps(self) -> None:
        rendered = app_v4._how_to_use_html()
        self.assertIn("How to use this interface", rendered)
        for step in (
            "Select a city.",
            "Select a mode.",
            "Choose provider: Local fallback or Gemini with fallback.",
            "Click Generate answer.",
            "Review Evidence used and Guardrail check.",
        ):
            self.assertIn(step, rendered)

    def test_provider_and_cache_help_text_are_explicit(self) -> None:
        self.assertEqual(
            app_v4.PROVIDER_HELP_TEXT["Local fallback only"],
            "Deterministic answer, no API needed.",
        )
        self.assertEqual(
            app_v4.PROVIDER_HELP_TEXT["Gemini API with fallback"],
            "Uses Gemini if available, otherwise deterministic fallback.",
        )
        self.assertIn("Cache stores only safe guardrail-approved answers", app_v4.CACHE_HELP_TEXT)
        self.assertIn("Entries: 0 means no answer has been cached yet", app_v4.CACHE_HELP_TEXT)
        self.assertIn("Repeat the same question to test cache hit", app_v4.CACHE_HELP_TEXT)

    def test_confidence_chart_is_lightweight_and_readable(self) -> None:
        chart = app_v4._confidence_band_chart_html({"High": 0.5, "Medium": 0.3, "Low": 0.2})
        self.assertIn("city1-band-chart", chart)
        self.assertIn("High", chart)
        self.assertIn("50.0%", chart)
        self.assertNotIn("<canvas", chart)

    def test_answer_card_escapes_provider_html(self) -> None:
        rendered = app_v4._answer_html("Safe <script>alert(1)</script>\nSecond line")
        self.assertIn("city1-answer", rendered)
        self.assertNotIn("<script>", rendered)
        self.assertIn("&lt;script&gt;", rendered)
        self.assertIn("<br>", rendered)

    def test_status_grid_contains_required_screenshot_fields(self) -> None:
        rendered = app_v4._status_grid_html(
            city="Almaty", support_level="full_v3", provider="Local fallback", cache_enabled=True
        )
        for label in ("Selected city", "Support level", "Provider", "Frozen run", "Fallback / cache"):
            self.assertIn(label, rendered)
        self.assertIn("city1-status-value--badge", rendered)

    def test_theme_uses_high_contrast_sidebar_and_teal_focus(self) -> None:
        capture = _StyleCapture()
        app_v4._render_style(capture)
        self.assertIn("--city1-sidebar: #14343c", capture.content)
        self.assertIn("background: #ffffff !important", capture.content)
        self.assertIn("border-color: var(--city1-teal) !important", capture.content)
        self.assertIn(".city1-help-card", capture.content)
        self.assertIn(".city1-sidebar-help", capture.content)
        self.assertIn(".city1-footer", capture.content)

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

    def test_backend_wrapper_reviewer_safe_policy_answer_is_direct(self) -> None:
        response = app_v4.run_local_assistant(
            city="Almaty",
            mode="Reviewer-Safe Answer",
            language="English",
            question="Can City1 v4 be used as official census evidence for policy decisions?",
        )
        answer = response["answer"]
        self.assertIn("No.", answer)
        self.assertIn("should not be used as official census evidence", answer)
        self.assertIn("calibrated proxy", answer)
        self.assertIn("not true cell-level census", answer)
        self.assertEqual(response["mode"], "reviewer_safe")

    def test_gemini_provider_label_falls_back_without_key(self) -> None:
        response = app_v4.run_local_assistant(
            city="Almaty",
            mode="Generate City Brief",
            language="English",
            provider="Gemini API with fallback",
        )
        self.assertEqual(response["provider_requested"], "gemini")
        self.assertIn(response["provider_used"], {"gemini", "fallback"})
        self.assertIn("guardrail", response)

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
        self.assertIn("guarded language layer with deterministic fallback", report)
        self.assertIn("fallback provider path", report)

    def test_markdown_report_can_include_guardrail_audit(self) -> None:
        from city1.llm_guardrails import guard_response

        response = app_v4.run_local_assistant(
            city="Almaty", mode="city_brief", language="en"
        )
        guarded = guard_response(response)
        report = app_v4.build_markdown_report(
            guarded["final_response"],
            city="Almaty",
            mode="Generate City Brief",
            question="",
            guardrail_result=guarded,
        )
        self.assertIn("## Guardrail check", report)
        self.assertIn("**Grounding score:** 100", report)
        self.assertIn("**Safe rewrite used:** False", report)

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
