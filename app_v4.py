"""City1 v4 offline, tool-grounded interpretation interface.

Run from the repository root with:
    python -m streamlit run app_v4.py

The module keeps helper functions import-safe for smoke tests. Streamlit is
imported only inside ``main`` and no frozen evidence artifact is modified.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from city1.llm_client import generate_llm_response, get_gemini_status  # noqa: E402
from city1.llm_cache import get_cache_status  # noqa: E402
from city1.llm_tools import (  # noqa: E402
    RUN_ID,
    compare_cities,
    get_available_cities,
    get_city_summary,
    get_claim_boundaries,
    get_hotspot_summary,
)


MODE_LABEL_TO_KEY = {
    "Ask City1 Assistant": "ask",
    "Generate City Brief": "city_brief",
    "Hotspot Review": "hotspot_review",
    "Uncertainty Summary": "uncertainty_summary",
    "Confidence Summary": "confidence_summary",
    "Compare Cities": "compare_cities",
    "Explain Selected Cell": "explain_cell",
    "Claim Checker": "claim_checker",
    "Reviewer-Safe Answer": "reviewer_safe",
}

LANGUAGE_LABEL_TO_CODE = {"English": "en", "Russian": "ru"}
STATE_DEFAULTS = {
    "last_response": None,
    "last_question": "",
    "selected_city": "Almaty",
    "selected_mode": "Generate City Brief",
    "selected_language": "English",
    "generated_report_md": "",
    "last_guardrail": None,
    "selected_provider": "Local fallback only",
    "show_cache_status": False,
}


def get_ordered_city_options() -> list[str]:
    """Return full-V3 cities first, then the remaining frozen registry cities."""
    available = get_available_cities()
    full = list(available.get("full_v3_cities", []))
    basic = list(available.get("v2_basic_cities", []))
    return list(dict.fromkeys(full + basic))


def resolve_selected_city(selected_city: str, custom_city: str = "", use_custom: bool = False) -> str:
    """Resolve sidebar city state without rejecting unknown-city tests."""
    if use_custom and str(custom_city).strip():
        return str(custom_city).strip()
    return str(selected_city or "").strip()


def get_city_overview(city: str) -> dict[str, Any]:
    """Combine read-only city and hotspot summaries for metric cards."""
    city_summary = get_city_summary(city)
    hotspot_summary = get_hotspot_summary(city, top_n=0)
    return {
        "city": city_summary.get("city") or city,
        "support_level": city_summary.get("support_level", "unknown"),
        "official_total": city_summary.get("official_total"),
        "cell_count": city_summary.get("cell_count"),
        "median_relative_uncertainty": city_summary.get("median_relative_uncertainty"),
        "mean_confidence_score": city_summary.get("mean_confidence_score"),
        "high_confidence_share": city_summary.get("high_confidence_share"),
        "medium_confidence_share": city_summary.get("medium_confidence_share"),
        "low_confidence_share": city_summary.get("low_confidence_share"),
        "priority_cells": hotspot_summary.get("total_priority_cells"),
        "osm_label": city_summary.get("osm_label"),
        "claim_boundary": city_summary.get("claim_boundary"),
        "evidence_sources": list(dict.fromkeys(
            city_summary.get("evidence_sources", []) + hotspot_summary.get("evidence_sources", [])
        )),
        "missing_artifacts": list(dict.fromkeys(
            city_summary.get("missing_artifacts", []) + hotspot_summary.get("missing_artifacts", [])
        )),
    }


def run_local_assistant(
    *,
    city: str,
    mode: str,
    language: str,
    question: str = "",
    cell_id: str | int | None = None,
    cities: list[str] | None = None,
    provider: str = "fallback",
    use_cache: bool = False,
    use_retrieval: bool = False,
    cache_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Call the guarded provider backend used by the Streamlit Generate button."""
    mode_key = MODE_LABEL_TO_KEY.get(mode, mode if mode in MODE_LABEL_TO_KEY.values() else "ask")
    language_code = LANGUAGE_LABEL_TO_CODE.get(language, language if language in {"en", "ru"} else "en")
    provider_key = "gemini" if str(provider).lower() in {"gemini", "gemini api with fallback"} else "fallback"
    return generate_llm_response(
        city=city,
        question=question,
        mode=mode_key,
        language=language_code,
        cell_id=cell_id,
        cities=cities,
        provider=provider_key,
        use_cache=use_cache,
        use_retrieval=use_retrieval,
        cache_dir=cache_dir,
    )


def build_markdown_report(
    response: dict[str, Any],
    *,
    city: str,
    mode: str,
    question: str,
    guardrail_result: dict[str, Any] | None = None,
) -> str:
    """Build a downloadable report in memory without writing to the project."""
    evidence = response.get("evidence_used", [])
    boundaries = response.get("claim_boundary_notes", [])
    checks = response.get("recommended_next_checks", [])
    missing = response.get("missing_artifacts", [])
    lines = [
        "# City1 v4 Interpretation Report",
        "",
        f"- **Selected city:** {city or 'Not applicable'}",
        f"- **Mode:** {mode}",
        f"- **Language:** {response.get('language', 'en')}",
        f"- **Provider requested:** {response.get('provider_requested', 'fallback')}",
        f"- **Provider used:** {response.get('provider_used', 'fallback')}",
        f"- **Frozen run:** `{RUN_ID}`",
        f"- **Confidence of answer:** {response.get('confidence_of_answer', 'unknown')}",
        "",
        "## Question",
        "",
        question.strip() or "No free-text question supplied; the selected structured mode was used.",
        "",
        "## Answer",
        "",
        response.get("answer", "No answer was generated."),
        "",
        "## Evidence used",
        "",
    ]
    lines.extend(f"- `{item}`" for item in evidence)
    if not evidence:
        lines.append("- No local evidence source was available.")
    lines.extend(["", "## Claim-boundary notes", ""])
    lines.extend(f"- {item}" for item in boundaries)
    lines.extend(["", "## Recommended next checks", ""])
    lines.extend(f"- {item}" for item in checks)
    if missing:
        lines.extend(["", "## Missing artifacts", ""])
        lines.extend(f"- `{item}`" for item in missing)
    if guardrail_result:
        guardrail = guardrail_result.get("guardrail", guardrail_result)
        lines.extend([
            "",
            "## Guardrail check",
            "",
            f"- **Passed:** {guardrail.get('passed', False)}",
            f"- **Severity:** {guardrail.get('severity', 'unknown')}",
            f"- **Risk score:** {guardrail.get('risk_score', 'unknown')}",
            f"- **Grounding score:** {guardrail.get('grounding_score', 'unknown')}",
            f"- **Safe rewrite used:** {guardrail_result.get('used_safe_rewrite', False)}",
        ])
        violations = guardrail.get("violations", [])
        if violations:
            lines.extend(["", "### Detected violations", ""])
            for item in violations:
                lines.append(
                    f"- `{item.get('category', 'UNKNOWN')}`: {item.get('matched_text', '')} — "
                    f"{item.get('explanation', '')}"
                )
    gemini = response.get("gemini")
    if isinstance(gemini, dict) and response.get("provider_requested") == "gemini":
        lines.extend([
            "",
            "## Gemini metadata",
            "",
            f"- **Success:** {gemini.get('success', False)}",
            f"- **Model:** {gemini.get('model', 'unknown')}",
            f"- **Latency seconds:** {gemini.get('latency_seconds', 0.0)}",
            f"- **Error/fallback reason:** {gemini.get('error') or 'None'}",
        ])
    cache = response.get("cache_metadata")
    if isinstance(cache, dict):
        lines.extend([
            "",
            "## Cache metadata",
            "",
            f"- **Cache hit:** {response.get('cache_hit', False)}",
            f"- **Match type:** {cache.get('match_type', 'none')}",
            f"- **Similarity:** {cache.get('similarity', 0.0)}",
            f"- **Cache ID:** {cache.get('cache_id') or 'None'}",
            f"- **Evidence hash:** {cache.get('evidence_hash') or 'None'}",
            f"- **Reason:** {cache.get('reason') or 'None'}",
        ])
    snippets = response.get("retrieved_snippets")
    if isinstance(snippets, list) and snippets:
        lines.extend(["", "## Retrieved City1 evidence snippets", ""])
        for item in snippets:
            lines.append(
                f"- **{item.get('title', 'Evidence')}** (`{item.get('source', 'local')}`, "
                f"score={item.get('score', 0.0)}): {item.get('snippet', '')}"
            )
    lines.extend([
        "",
        "## Scientific disclaimer",
        "",
        "City1 v4 explains frozen V2/V3 evidence through a guarded language layer with deterministic fallback. "
        "It does not create new population estimates, reconstruct true cell-level census counts, "
        "or convert proxy intervals into true census uncertainty.",
        "",
        f"Generated by the City1 v4 {response.get('provider_used', 'fallback')} provider path.",
    ])
    return "\n".join(lines)


def _fmt_integer(value: Any) -> str:
    if value is None:
        return "Not available"
    try:
        return f"{int(round(float(value))):,}"
    except (TypeError, ValueError):
        return "Not available"


def _fmt_float(value: Any, digits: int = 3) -> str:
    if value is None:
        return "Not available"
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return "Not available"


def _fmt_percent(value: Any) -> str:
    if value is None:
        return "Not available"
    try:
        return f"{float(value) * 100:.1f}%"
    except (TypeError, ValueError):
        return "Not available"


def _initialize_session_state(st: Any) -> None:
    for key, value in STATE_DEFAULTS.items():
        st.session_state.setdefault(key, value)


def _render_style(st: Any) -> None:
    st.markdown(
        """
        <style>
        :root {
            --city1-ink: #18323a;
            --city1-teal: #16756f;
            --city1-sand: #f3ead7;
            --city1-amber: #cf7b28;
            --city1-paper: #fbfaf6;
        }
        .stApp {
            background:
                radial-gradient(circle at 88% 6%, rgba(207,123,40,.12), transparent 27rem),
                linear-gradient(180deg, var(--city1-paper), #f4f7f4 65%);
            color: var(--city1-ink);
            font-family: Georgia, 'Times New Roman', serif;
        }
        h1, h2, h3 { color: var(--city1-ink); letter-spacing: -0.02em; }
        [data-testid="stMetric"] {
            background: rgba(255,255,255,.78);
            border: 1px solid rgba(24,50,58,.13);
            border-top: 3px solid var(--city1-teal);
            border-radius: 10px;
            padding: .75rem 1rem;
            box-shadow: 0 8px 28px rgba(24,50,58,.06);
        }
        [data-testid="stSidebar"] { background: #18323a; }
        [data-testid="stSidebar"] * { color: #f8f2e7; }
        [data-testid="stSidebar"] input,
        [data-testid="stSidebar"] [data-baseweb="select"] * { color: #18323a; }
        .city1-kicker {
            color: var(--city1-teal); font-weight: 700; letter-spacing: .12em;
            text-transform: uppercase; font-size: .75rem;
        }
        .city1-answer {
            background: rgba(255,255,255,.82); border-left: 5px solid var(--city1-amber);
            border-radius: 8px; padding: 1.25rem 1.4rem; line-height: 1.65;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_response(st: Any, response: dict[str, Any]) -> None:
    status_columns = st.columns(3)
    status_columns[0].metric("Answer confidence", str(response.get("confidence_of_answer", "unknown")).title())
    status_columns[1].metric("Fallback used", "Yes" if response.get("fallback_used") else "No")
    status_columns[2].metric("Evidence sources", len(response.get("evidence_used", [])))

    st.markdown("### Assistant response")
    st.markdown(response.get("answer", "No answer generated."))

    missing = response.get("missing_artifacts", [])
    if missing:
        st.warning("Some expected artifacts are unavailable. The answer has been downgraded accordingly.")
        for item in missing:
            st.code(item, language=None)

    with st.expander("Evidence used", expanded=False):
        sources = response.get("evidence_used", [])
        if sources:
            for item in sources:
                st.code(item, language=None)
        else:
            st.info("No local artifact path was available for this response.")

    with st.expander("Claim boundaries", expanded=True):
        for item in response.get("claim_boundary_notes", []):
            st.warning(item)

    with st.expander("Recommended next checks", expanded=False):
        for item in response.get("recommended_next_checks", []):
            st.markdown(f"- {item}")


def _render_guardrail(st: Any, guarded: dict[str, Any]) -> None:
    guardrail = guarded.get("guardrail", {})
    severity = str(guardrail.get("severity", "none"))
    passed = bool(guardrail.get("passed"))
    rewritten = bool(guarded.get("used_safe_rewrite"))
    grounding_score = guardrail.get("grounding_score", 0)

    st.markdown("### Guardrail check")
    status_columns = st.columns(4)
    status_columns[0].metric("Status", "Passed" if passed else "Review required")
    status_columns[1].metric("Severity", severity.title())
    status_columns[2].metric("Grounding score", f"{grounding_score}/100")
    status_columns[3].metric("Safe rewrite", "Used" if rewritten else "Not needed")

    message = (
        "Critical scientific overclaim detected. The displayed answer was replaced with conservative City1 wording."
        if severity == "critical"
        else "Scientific claim-boundary issues were detected. Review the violations below."
    )
    if severity == "critical":
        st.error(message)
    elif severity in {"medium", "high"}:
        st.warning(message)
    elif passed:
        st.success("The response passed deterministic claim-boundary and evidence-grounding checks.")
    else:
        st.info("No forbidden phrase was found, but evidence grounding requires review.")

    violations = guardrail.get("violations", [])
    if violations:
        with st.expander("Detected guardrail violations", expanded=True):
            for item in violations:
                st.markdown(f"**{item.get('category', 'UNKNOWN')}** — `{item.get('matched_text', '')}`")
                st.caption(item.get("explanation", ""))
                st.markdown(f"Safe alternative: `{item.get('safe_alternative', '')}`")
    issues = guardrail.get("grounding_issues", [])
    if issues:
        with st.expander("Evidence-grounding issues", expanded=True):
            for item in issues:
                st.markdown(f"- {item}")


def _render_provider_metadata(st: Any, response: dict[str, Any]) -> None:
    requested = response.get("provider_requested", "fallback")
    used = response.get("provider_used", "fallback")
    if requested == "gemini":
        gemini = response.get("gemini", {})
        st.markdown("### Gemini provider status")
        columns = st.columns(4)
        columns[0].metric("Provider used", str(used).title())
        columns[1].metric("Gemini call", "Succeeded" if gemini.get("success") else "Unavailable / rejected")
        columns[2].metric("Model", str(gemini.get("model", "unknown")))
        columns[3].metric("Latency", f"{float(gemini.get('latency_seconds') or 0.0):.2f}s")
        if used == "fallback":
            st.warning(f"Gemini unavailable; using deterministic fallback. Reason: {gemini.get('error') or 'unknown'}")
        else:
            st.success("Gemini generated the language response; deterministic guardrails approved it.")


def _render_cache_and_retrieval(st: Any, response: dict[str, Any]) -> None:
    cache = response.get("cache_metadata", {})
    st.markdown("### Cache and local retrieval")
    columns = st.columns(4)
    columns[0].metric("Cache", "Hit" if response.get("cache_hit") else "Miss / disabled")
    columns[1].metric("Match type", str(cache.get("match_type", "none")).title())
    columns[2].metric("Similarity", f"{float(cache.get('similarity') or 0.0):.3f}")
    evidence_hash = str(cache.get("evidence_hash") or "")
    columns[3].metric("Evidence hash", evidence_hash[:12] if evidence_hash else "Not available")
    if response.get("cache_hit"):
        st.success("A previously guardrail-approved answer was reused; no Gemini call was needed.")

    snippets = response.get("retrieved_snippets", [])
    with st.expander("Retrieved City1 evidence snippets", expanded=False):
        if snippets:
            for item in snippets:
                st.markdown(f"**{item.get('title', 'Evidence')}** — score `{item.get('score', 0.0)}`")
                st.caption(f"Source: {item.get('source', 'local City1 artifact')}")
                st.write(item.get("snippet", ""))
        else:
            st.info("Mini-RAG retrieval was disabled or returned no local snippets.")


def main() -> None:
    try:
        import pandas as pd
        import streamlit as st
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "City1 v4 requires Streamlit for the UI. Install project requirements and run "
            "`python -m streamlit run app_v4.py`."
        ) from exc

    st.set_page_config(page_title="City1 v4 Interpretation Assistant", layout="wide")
    _initialize_session_state(st)
    _render_style(st)

    city_options = get_ordered_city_options()
    if not city_options:
        city_options = ["Almaty"]
    if st.session_state.get("selected_city") not in city_options:
        st.session_state["selected_city"] = city_options[0]

    with st.sidebar:
        st.markdown("## Evidence controls")
        st.selectbox("City", options=city_options, key="selected_city")
        use_custom_city = st.checkbox("Use custom / unknown city", value=False)
        custom_city = st.text_input("Custom city", value="") if use_custom_city else ""

        st.selectbox("Mode", options=list(MODE_LABEL_TO_KEY), key="selected_mode")
        st.selectbox("Language", options=list(LANGUAGE_LABEL_TO_CODE), key="selected_language")
        st.selectbox(
            "Provider",
            options=["Local fallback only", "Gemini API with fallback"],
            key="selected_provider",
        )
        gemini_status = get_gemini_status()
        if st.session_state["selected_provider"] == "Gemini API with fallback":
            if gemini_status["available"]:
                st.success(f"Gemini ready: {gemini_status['model']}")
            else:
                st.warning(f"Gemini unavailable: {gemini_status['reason']}")
        st.caption(
            f"SDK: {'available' if gemini_status['sdk_available'] else 'missing'}; "
            f"API key: {'available' if gemini_status['api_key_available'] else 'missing'}."
        )
        use_cache = st.checkbox("Use local cache", value=True)
        use_retrieval = st.checkbox("Use City1 mini-RAG snippets", value=True)
        if st.button("Show cache status", use_container_width=True):
            st.session_state["show_cache_status"] = not st.session_state.get("show_cache_status", False)
        if st.session_state.get("show_cache_status"):
            cache_status = get_cache_status()
            st.info(
                f"Entries: {cache_status['entry_count']} | "
                f"Index: {'present' if cache_status['index_exists'] else 'not created'} | "
                f"Directory: {cache_status['cache_dir']}"
            )

        mode_key = MODE_LABEL_TO_KEY[st.session_state["selected_mode"]]
        cell_id = None
        compare_selection: list[str] | None = None
        if mode_key == "explain_cell":
            cell_id = st.text_input("Cell ID", placeholder="Example: Z1406")
        if mode_key == "compare_cities":
            defaults = [city for city in ("Almaty", "Astana") if city in city_options]
            compare_selection = st.multiselect("Cities to compare", options=city_options, default=defaults)

        st.divider()
        st.caption(f"Frozen evidence run: {RUN_ID}")
        st.caption("All providers are evidence-grounded; deterministic fallback remains available offline.")

    selected_city = resolve_selected_city(st.session_state["selected_city"], custom_city, use_custom_city)
    overview = get_city_overview(selected_city)
    language_code = LANGUAGE_LABEL_TO_CODE[st.session_state["selected_language"]]

    st.markdown("<div class='city1-kicker'>City1 / cCity research interface</div>", unsafe_allow_html=True)
    st.title("City1 v4 — Tool-Grounded LLM Interpretation Assistant")
    st.caption("Evidence-first fallback interface for calibrated and uncertainty-aware proxy population surfaces.")
    if language_code == "ru":
        st.warning("City1 v4 объясняет frozen V2/V3 evidence. Он не создаёт новые оценки населения и не восстанавливает true cell-level census counts.")
    else:
        st.warning("City1 v4 explains frozen V2/V3 evidence. It does not create new population estimates and does not reconstruct true cell-level census counts.")

    top_cards = st.columns(5)
    top_cards[0].metric("Selected city", overview["city"] or selected_city)
    top_cards[1].metric("Support level", str(overview["support_level"]).replace("_", " ").title())
    cached_response = st.session_state.get("last_response") or {}
    provider_display = cached_response.get("provider_used") or (
        "gemini + fallback" if st.session_state["selected_provider"] == "Gemini API with fallback" else "local fallback"
    )
    top_cards[2].metric("Provider", str(provider_display).title())
    top_cards[3].metric("Run ID", RUN_ID)
    top_cards[4].metric("Fallback status", "Ready offline")

    st.markdown("### City evidence overview")
    evidence_cards = st.columns(6)
    evidence_cards[0].metric("Official total", _fmt_integer(overview["official_total"]))
    evidence_cards[1].metric("Grid cells", _fmt_integer(overview["cell_count"]))
    evidence_cards[2].metric("Median rel. uncertainty", _fmt_float(overview["median_relative_uncertainty"]))
    evidence_cards[3].metric("Mean confidence", _fmt_float(overview["mean_confidence_score"]))
    evidence_cards[4].metric("Priority cells", _fmt_integer(overview["priority_cells"]))
    evidence_cards[5].metric("OSM context", str(overview["osm_label"] or "Not available").title())

    shares = {
        "High": overview["high_confidence_share"],
        "Medium": overview["medium_confidence_share"],
        "Low": overview["low_confidence_share"],
    }
    if any(value is not None for value in shares.values()):
        with st.expander("Confidence-band distribution", expanded=False):
            chart = pd.DataFrame(
                {"Confidence band": list(shares), "Share": [shares[key] or 0.0 for key in shares]}
            ).set_index("Confidence band")
            st.bar_chart(chart)
            st.caption("confidence_score is interpretation support, not a probability of correctness.")
    elif overview["support_level"] != "full_v3":
        st.info("Full V3 confidence-band evidence is unavailable for this city.")

    st.markdown("### Assistant panel")
    question_placeholder = {
        "claim_checker": "Paste a scientific claim to check...",
        "explain_cell": "Optional context for the selected cell...",
        "compare_cities": "What aspect of the selected cities should be compared?",
    }.get(mode_key, "Ask about the city, uncertainty, confidence, hotspots, or claim boundaries...")
    question = st.text_area(
        "Question or claim",
        value=st.session_state.get("last_question", ""),
        placeholder=question_placeholder,
        height=110,
    )

    action_columns = st.columns([1, 1, 4])
    generate_clicked = action_columns[0].button("Generate answer", type="primary", use_container_width=True)
    clear_clicked = action_columns[1].button("Clear answer", use_container_width=True)

    if clear_clicked:
        st.session_state["last_response"] = None
        st.session_state["last_question"] = ""
        st.session_state["generated_report_md"] = ""
        st.session_state["last_guardrail"] = None
        st.rerun()

    if generate_clicked:
        if mode_key == "claim_checker" and not question.strip():
            st.warning("Enter a claim before running Claim Checker.")
        elif mode_key == "compare_cities" and not compare_selection:
            st.warning("Select at least one city for comparison.")
        else:
            try:
                with st.spinner("Reading frozen evidence and building a bounded response..."):
                    response = run_local_assistant(
                        city=selected_city,
                        mode=mode_key,
                        language=language_code,
                        question=question,
                        cell_id=cell_id,
                        cities=compare_selection,
                        provider=st.session_state["selected_provider"],
                        use_cache=use_cache,
                        use_retrieval=use_retrieval,
                    )
                    guarded = {
                        "guardrail": response.get("guardrail", {}),
                        "final_response": response,
                        "used_safe_rewrite": response.get("used_safe_rewrite", False),
                    }
                st.session_state["last_response"] = response
                st.session_state["last_guardrail"] = guarded
                st.session_state["last_question"] = question
                st.session_state["generated_report_md"] = build_markdown_report(
                    response,
                    city=selected_city,
                    mode=st.session_state["selected_mode"],
                    question=question,
                    guardrail_result=guarded,
                )
            except Exception as exc:  # Keep the interface usable with partial local artifacts.
                st.error(f"The local evidence engine could not complete this request: {exc}")

    response = st.session_state.get("last_response")
    if response:
        _render_response(st, response)
        _render_provider_metadata(st, response)
        _render_cache_and_retrieval(st, response)
        guarded = st.session_state.get("last_guardrail")
        if guarded:
            _render_guardrail(st, guarded)
        st.download_button(
            "Download Markdown report",
            data=st.session_state.get("generated_report_md", ""),
            file_name="city1_v4_interpretation_report.md",
            mime="text/markdown",
        )

        if response.get("mode") == "compare_cities" and compare_selection:
            comparison = compare_cities(compare_selection)
            rows = comparison.get("cities", [])
            if rows:
                st.markdown("### Comparison evidence table")
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    with st.expander("Framework-wide scientific boundaries", expanded=False):
        boundaries = get_claim_boundaries()
        st.markdown("**Allowed framing**")
        for item in boundaries.get("allowed_claims", []):
            st.markdown(f"- {item}")
        st.markdown("**Forbidden framing**")
        for item in boundaries.get("forbidden_claims", []):
            st.markdown(f"- {item}")

    st.divider()
    st.caption(
        "City1 v4 guarded interpretation interface. Hotspot classes are screening/triage outputs; "
        "proxy intervals are not true census uncertainty; external products are structural comparators only."
    )


if __name__ == "__main__":
    main()
