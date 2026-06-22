"""Optional Gemini language layer for the City1 v4 evidence assistant.

Gemini is never required. All provider errors, invalid responses, and unsafe
answers return to the deterministic fallback and every final answer passes the
local claim-boundary guardrail.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Iterable

from city1.llm_cache import (
    augment_evidence_pack_with_retrieval,
    lookup_cached_response,
    store_cached_response,
)
from city1.llm_fallback import SUPPORTED_MODES, generate_fallback_response
from city1.llm_guardrails import guard_response
from city1.llm_tools import (
    compare_cities,
    generate_evidence_pack,
    get_cell_evidence,
    get_claim_boundaries,
)


DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
DEFAULT_TEMPERATURE = 0.2
DEFAULT_MAX_OUTPUT_TOKENS = 1600
DEFAULT_TIMEOUT_SECONDS = 45.0
EVIDENCE_WARNING_CHARACTERS = 24_000

_RESPONSE_SCHEMA = {
    "answer": "human-readable answer",
    "confidence_of_answer": "high|medium|low",
    "evidence_used": ["local evidence source label"],
    "claim_boundary_notes": ["explicit scientific boundary"],
    "recommended_next_checks": ["manual or evidence check"],
    "structured_sections": {
        "summary": "short summary",
        "evidence": ["evidence statement"],
        "cautions": ["limitation statement"],
        "next_checks": ["recommended check"],
    },
}


def _dedupe(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(str(value) for value in values if value not in (None, "")))


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _model_name() -> str:
    return os.getenv("CITY1_GEMINI_MODEL", DEFAULT_GEMINI_MODEL).strip() or DEFAULT_GEMINI_MODEL


def _api_key() -> str | None:
    return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or None


def _sdk_available() -> bool:
    try:
        return importlib.util.find_spec("google.genai") is not None
    except (ImportError, ModuleNotFoundError, ValueError):
        return False


def get_gemini_status() -> dict[str, Any]:
    """Report local Gemini readiness without exposing secret values."""
    sdk = _sdk_available()
    key = bool(_api_key())
    if not sdk:
        reason = "google-genai SDK is not installed."
    elif not key:
        reason = "No GEMINI_API_KEY or GOOGLE_API_KEY is configured."
    else:
        reason = "Gemini SDK and API key are available."
    return {
        "available": sdk and key,
        "reason": reason,
        "sdk_available": sdk,
        "api_key_available": key,
        "model": _model_name(),
        "provider": "gemini",
    }


def _source_label(value: str) -> str:
    text = str(value).replace("\\", "/").rstrip("/")
    name = Path(text).name
    parent = Path(text).parent.name
    return f"{parent}/{name}" if parent and parent != "." else (name or text)


def _compact_value(value: Any, *, depth: int = 0) -> Any:
    if depth > 6:
        return "[nested content omitted]"
    if isinstance(value, dict):
        compact: dict[str, Any] = {}
        for key, nested in value.items():
            if key in {"top_hotspots", "stable_examples", "caution_examples"} and isinstance(nested, list):
                compact[key] = [_compact_value(item, depth=depth + 1) for item in nested[:3]]
            elif key in {"evidence_sources", "evidence_used"} and isinstance(nested, list):
                compact[key] = _dedupe(_source_label(item) for item in nested)[:20]
            else:
                compact[key] = _compact_value(nested, depth=depth + 1)
        return compact
    if isinstance(value, (list, tuple)):
        return [_compact_value(item, depth=depth + 1) for item in value[:20]]
    if isinstance(value, str):
        return value if len(value) <= 900 else value[:897] + "..."
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return str(value)


def _compact_evidence_pack(evidence_pack: dict[str, Any]) -> dict[str, Any]:
    allowed_keys = (
        "mode",
        "city",
        "question",
        "city_summary",
        "hotspot_summary",
        "confidence_summary",
        "uncertainty_summary",
        "cell_evidence",
        "city_comparison",
        "claim_boundaries",
        "method_summary",
        "evidence_sources",
        "missing_artifacts",
        "retrieved_snippets",
        "retrieval_sources",
        "retrieval_note",
    )
    selected = {key: evidence_pack[key] for key in allowed_keys if key in evidence_pack}
    return _compact_value(selected)


def estimate_evidence_packet_size(evidence_pack: dict[str, Any]) -> dict[str, Any]:
    compact = _compact_evidence_pack(evidence_pack if isinstance(evidence_pack, dict) else {})
    serialized = json.dumps(compact, ensure_ascii=False, separators=(",", ":"))
    character_count = len(serialized)
    return {
        "character_count": character_count,
        "approximate_tokens": max(1, character_count // 4),
        "warning": character_count > EVIDENCE_WARNING_CHARACTERS,
        "warning_threshold_characters": EVIDENCE_WARNING_CHARACTERS,
    }


def build_gemini_prompt(
    evidence_pack: dict[str, Any],
    question: str,
    mode: str,
    language: str = "en",
) -> dict[str, Any]:
    """Build a compact closed-world prompt without raw project files."""
    language = language if language in {"en", "ru"} else "en"
    compact = _compact_evidence_pack(evidence_pack if isinstance(evidence_pack, dict) else {})
    boundaries = compact.get("claim_boundaries") or get_claim_boundaries()
    system_instruction = (
        "You are the City1 v4 evidence interpretation language layer. You are not a population model. "
        "You cannot create estimates, change P10/P50/P90, change confidence_score, or create hotspot classes. "
        "Use only the supplied compact evidence packet. If evidence is missing, state exactly: "
        "'Evidence unavailable in the current City1 artifacts.' Keep all claim boundaries explicit. "
        "City1 is a calibrated proxy population framework, not true cell-level census reconstruction. "
        "P10/P50/P90 describe proxy ensemble spread, not true census uncertainty. "
        "Return one JSON object only, with no markdown fences or surrounding commentary."
    )
    user_payload = {
        "question": str(question or ""),
        "mode": str(mode or "ask"),
        "language": language,
        "allowed_claims": boundaries.get("allowed_claims", []),
        "forbidden_claims": boundaries.get("forbidden_claims", []),
        "required_response_schema": _RESPONSE_SCHEMA,
        "compact_evidence_packet": compact,
    }
    size = estimate_evidence_packet_size(evidence_pack)
    return {
        "system_instruction": system_instruction,
        "user_prompt": json.dumps(user_payload, ensure_ascii=False, indent=2),
        "response_schema_description": copy_json(_RESPONSE_SCHEMA),
        "token_safety_notes": [
            "Only compact summaries and at most three examples per hotspot list are included.",
            "Local source paths are reduced to short artifact labels.",
            "Raw CSV, GeoJSON, model files, manuscripts, and secrets are excluded.",
            f"Approximate prompt evidence size: {size['character_count']} characters.",
        ],
    }


def copy_json(value: Any) -> Any:
    """Return a detached JSON-safe copy for prompt and response metadata."""
    return json.loads(json.dumps(value, ensure_ascii=False))


def parse_gemini_json_response(text: str) -> dict[str, Any]:
    """Parse pure, fenced, or surrounded JSON without raising exceptions."""
    value = str(text or "").strip()
    candidates = [value]
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", value, flags=re.IGNORECASE | re.DOTALL)
    if fenced:
        candidates.insert(0, fenced.group(1))
    first_brace = value.find("{")
    if first_brace >= 0:
        candidates.append(value[first_brace:])

    errors: list[str] = []
    decoder = json.JSONDecoder()
    for candidate in _dedupe(candidates):
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError as exc:
            try:
                parsed, _ = decoder.raw_decode(candidate)
            except json.JSONDecodeError:
                errors.append(str(exc))
                continue
        if isinstance(parsed, dict):
            return {"success": True, "data": parsed, "error": None}
        errors.append("Parsed JSON is not an object.")
    return {
        "success": False,
        "data": None,
        "error": "Gemini response did not contain a valid JSON object. " + (errors[0] if errors else "Empty response."),
    }


def _safe_error(exc: Exception, key: str | None) -> str:
    message = f"{type(exc).__name__}: {exc}"
    if key:
        message = message.replace(key, "[REDACTED]")
    return message[:600]


def call_gemini_structured(
    evidence_pack: dict[str, Any],
    question: str,
    mode: str = "ask",
    language: str = "en",
) -> dict[str, Any]:
    """Call google-genai safely and return metadata instead of raising."""
    started = time.perf_counter()
    model = _model_name()
    status = get_gemini_status()
    if not status["available"]:
        return {
            "success": False,
            "provider": "gemini",
            "model": model,
            "raw_text": "",
            "parsed_response": None,
            "error": status["reason"],
            "latency_seconds": round(time.perf_counter() - started, 4),
            "used_fallback": False,
        }

    key = _api_key()
    try:
        from google import genai
        from google.genai import types

        prompt = build_gemini_prompt(evidence_pack, question, mode, language)
        timeout_ms = max(1, int(_env_float("CITY1_GEMINI_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS) * 1000))
        try:
            client = genai.Client(api_key=key, http_options=types.HttpOptions(timeout=timeout_ms))
        except (TypeError, AttributeError):
            client = genai.Client(api_key=key)

        config_kwargs = {
            "system_instruction": prompt["system_instruction"],
            "temperature": max(0.0, min(_env_float("CITY1_GEMINI_TEMPERATURE", DEFAULT_TEMPERATURE), 1.0)),
            "max_output_tokens": max(256, _env_int("CITY1_GEMINI_MAX_OUTPUT_TOKENS", DEFAULT_MAX_OUTPUT_TOKENS)),
            "response_mime_type": "application/json",
        }
        config = types.GenerateContentConfig(**config_kwargs)
        response = client.models.generate_content(
            model=model,
            contents=prompt["user_prompt"],
            config=config,
        )
        raw_text = str(getattr(response, "text", "") or "")
        parsed = parse_gemini_json_response(raw_text)
        if not parsed["success"]:
            return {
                "success": False,
                "provider": "gemini",
                "model": model,
                "raw_text": raw_text[:4000],
                "parsed_response": None,
                "error": parsed["error"],
                "latency_seconds": round(time.perf_counter() - started, 4),
                "used_fallback": False,
            }
        return {
            "success": True,
            "provider": "gemini",
            "model": model,
            "raw_text": raw_text[:4000],
            "parsed_response": parsed["data"],
            "error": None,
            "latency_seconds": round(time.perf_counter() - started, 4),
            "used_fallback": False,
        }
    except Exception as exc:
        return {
            "success": False,
            "provider": "gemini",
            "model": model,
            "raw_text": "",
            "parsed_response": None,
            "error": _safe_error(exc, key),
            "latency_seconds": round(time.perf_counter() - started, 4),
            "used_fallback": False,
        }


def _prepare_evidence_pack(
    city: str | None,
    question: str,
    mode: str,
    evidence_pack: dict[str, Any] | None,
    cell_id: str | int | None,
    cities: list[str] | None,
) -> dict[str, Any]:
    if isinstance(evidence_pack, dict):
        return copy_json(evidence_pack)
    tool_mode = mode if mode in {"ask", "city_brief", "hotspot_review", "explain_cell", "compare_cities", "claim_checker", "reviewer_safe"} else "city_brief"
    cell_question = question
    if mode == "explain_cell" and cell_id is not None and str(cell_id) not in cell_question:
        cell_question = f"{cell_question} cell {cell_id}".strip()
    pack = generate_evidence_pack(city or "", question=cell_question, mode=tool_mode)
    if mode == "explain_cell" and cell_id is not None:
        pack["cell_evidence"] = get_cell_evidence(city or pack.get("city", ""), cell_id)
    if mode == "compare_cities":
        comparison = compare_cities(cities)
        pack["city_comparison"] = comparison
        pack["evidence_sources"] = _dedupe(pack.get("evidence_sources", []) + comparison.get("evidence_sources", []))
        pack["missing_artifacts"] = _dedupe(pack.get("missing_artifacts", []) + comparison.get("missing_artifacts", []))
    return pack


def _normalize_gemini_response(
    parsed: dict[str, Any],
    evidence_pack: dict[str, Any],
    *,
    city: str | None,
    mode: str,
    language: str,
) -> dict[str, Any] | None:
    answer = parsed.get("answer")
    if not isinstance(answer, str) or not answer.strip():
        return None
    confidence = parsed.get("confidence_of_answer")
    if confidence not in {"high", "medium", "low"}:
        confidence = "medium"
    sections = parsed.get("structured_sections")
    if not isinstance(sections, dict):
        sections = {
            "summary": answer.strip(),
            "evidence": [],
            "cautions": [],
            "next_checks": [],
        }
    for key, default in (("summary", answer.strip()), ("evidence", []), ("cautions", []), ("next_checks", [])):
        if key not in sections or not isinstance(sections[key], (str, list)):
            sections[key] = default
    actual_sources = list(evidence_pack.get("evidence_sources", []))
    missing = list(evidence_pack.get("missing_artifacts", []))
    notes = parsed.get("claim_boundary_notes") if isinstance(parsed.get("claim_boundary_notes"), list) else []
    checks = parsed.get("recommended_next_checks") if isinstance(parsed.get("recommended_next_checks"), list) else []
    return {
        "answer": answer.strip(),
        "mode": mode,
        "city": city or evidence_pack.get("city"),
        "language": language if language in {"en", "ru"} else "en",
        "fallback_used": False,
        "confidence_of_answer": confidence,
        "evidence_used": actual_sources,
        "claim_boundary_notes": _dedupe(notes),
        "recommended_next_checks": _dedupe(checks),
        "missing_artifacts": missing,
        "structured_sections": sections,
    }


def _finalize_result(
    final_response: dict[str, Any],
    guarded: dict[str, Any],
    *,
    provider_requested: str,
    provider_used: str,
    gemini_meta: dict[str, Any],
) -> dict[str, Any]:
    result = copy_json(final_response)
    result.update({
        "provider_requested": provider_requested,
        "provider_used": provider_used,
        "fallback_used": provider_used == "fallback",
        "gemini": gemini_meta,
        "guardrail": guarded["guardrail"],
        "used_safe_rewrite": guarded["used_safe_rewrite"],
    })
    json.dumps(result, ensure_ascii=False)
    return result


def generate_llm_response(
    city: str | None = None,
    question: str = "",
    mode: str = "ask",
    language: str = "en",
    provider: str = "fallback",
    evidence_pack: dict[str, Any] | None = None,
    cell_id: str | int | None = None,
    cities: list[str] | None = None,
    use_cache: bool = True,
    use_retrieval: bool = True,
    cache_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Generate one guarded Gemini or deterministic fallback response."""
    normalized_mode = mode if mode in SUPPORTED_MODES else "ask"
    normalized_language = language if language in {"en", "ru"} else "en"
    provider_requested = "gemini" if str(provider).lower() in {"gemini", "gemini api with fallback"} else "fallback"
    pack = _prepare_evidence_pack(city, question, normalized_mode, evidence_pack, cell_id, cities)
    if use_retrieval:
        pack = augment_evidence_pack_with_retrieval(pack, question, city=city or pack.get("city"), top_k=5)

    lookup = {
        "hit": False,
        "match_type": "none",
        "similarity": 0.0,
        "reason": "Local cache is disabled.",
    }
    if use_cache:
        lookup = lookup_cached_response(
            city=city or str(pack.get("city") or ""),
            mode=normalized_mode,
            language=normalized_language,
            question=question,
            evidence_pack=pack,
            cache_dir=cache_dir,
            allow_similarity=True,
        )
        if lookup["hit"]:
            cached_response = dict(lookup["cached_response"])
            cached_guarded = guard_response(cached_response, language=normalized_language, auto_rewrite=False)
            if cached_guarded["guardrail"]["passed"]:
                result = dict(cached_guarded["final_response"])
                cached_source = str(lookup.get("source") or "fallback")
                result.update({
                    "provider_requested": provider_requested,
                    "provider_used": "cache",
                    "fallback_used": cached_source == "fallback",
                    "gemini": {
                        "success": False,
                        "model": _model_name(),
                        "error": "Cache hit; Gemini call was not needed." if provider_requested == "gemini" else None,
                        "latency_seconds": 0.0,
                    },
                    "guardrail": cached_guarded["guardrail"],
                    "used_safe_rewrite": False,
                    "cache_hit": True,
                    "cache_metadata": {
                        "match_type": lookup["match_type"],
                        "similarity": lookup["similarity"],
                        "cache_id": lookup.get("cache_id"),
                        "evidence_hash": lookup.get("evidence_hash"),
                        "source": cached_source,
                        "reason": lookup["reason"],
                    },
                    "retrieved_snippets": list(pack.get("retrieved_snippets", [])),
                    "retrieval_sources": list(pack.get("retrieval_sources", [])),
                    "retrieval_note": pack.get("retrieval_note"),
                })
                json.dumps(result, ensure_ascii=False)
                return result

    gemini_meta: dict[str, Any] = {
        "success": False,
        "model": _model_name(),
        "error": None,
        "latency_seconds": 0.0,
    }
    if provider_requested == "gemini":
        call = call_gemini_structured(pack, question, normalized_mode, normalized_language)
        gemini_meta = {
            "success": bool(call.get("success")),
            "model": call.get("model", _model_name()),
            "error": call.get("error"),
            "latency_seconds": call.get("latency_seconds", 0.0),
        }
        if call.get("success"):
            gemini_response = _normalize_gemini_response(
                call.get("parsed_response") or {}, pack,
                city=city, mode=normalized_mode, language=normalized_language,
            )
            if gemini_response is not None:
                if normalized_mode == "claim_checker":
                    gemini_response["claim_text_under_review"] = question
                gemini_guarded = guard_response(gemini_response, language=normalized_language, auto_rewrite=True)
                if gemini_guarded["guardrail"]["passed"]:
                    final_response = dict(gemini_guarded["final_response"])
                    final_response.pop("claim_text_under_review", None)
                    result = _finalize_result(
                        final_response, gemini_guarded,
                        provider_requested="gemini", provider_used="gemini", gemini_meta=gemini_meta,
                    )
                    return _attach_cache_and_retrieval(
                        result, pack, lookup, use_cache=use_cache, cache_dir=cache_dir,
                        city=city or str(pack.get("city") or ""), mode=normalized_mode,
                        language=normalized_language, question=question,
                    )
                gemini_meta["error"] = "Gemini response was rejected by deterministic claim-boundary guardrails."
                gemini_meta["guardrail_rejected"] = True
                gemini_meta["rejection_severity"] = gemini_guarded["guardrail"]["severity"]
            else:
                gemini_meta["error"] = "Gemini JSON was missing a non-empty answer field."

    fallback_response = generate_fallback_response(
        evidence_pack=pack,
        city=city,
        question=question,
        mode=normalized_mode,
        language=normalized_language,
        cell_id=cell_id,
        cities=cities,
    )
    if normalized_mode == "claim_checker":
        fallback_response["claim_text_under_review"] = question
    fallback_guarded = guard_response(fallback_response, language=normalized_language, auto_rewrite=True)
    final_response = dict(fallback_guarded["final_response"])
    final_response.pop("claim_text_under_review", None)
    if provider_requested == "gemini" and not gemini_meta.get("error"):
        gemini_meta["error"] = "Gemini was unavailable; deterministic fallback was used."
    result = _finalize_result(
        final_response, fallback_guarded,
        provider_requested=provider_requested, provider_used="fallback", gemini_meta=gemini_meta,
    )
    return _attach_cache_and_retrieval(
        result, pack, lookup, use_cache=use_cache, cache_dir=cache_dir,
        city=city or str(pack.get("city") or ""), mode=normalized_mode,
        language=normalized_language, question=question,
    )


def _attach_cache_and_retrieval(
    result: dict[str, Any],
    evidence_pack: dict[str, Any],
    lookup: dict[str, Any],
    *,
    use_cache: bool,
    cache_dir: str | Path | None,
    city: str,
    mode: str,
    language: str,
    question: str,
) -> dict[str, Any]:
    result["cache_hit"] = False
    result["retrieved_snippets"] = list(evidence_pack.get("retrieved_snippets", []))
    result["retrieval_sources"] = list(evidence_pack.get("retrieval_sources", []))
    result["retrieval_note"] = evidence_pack.get("retrieval_note")
    cache_metadata: dict[str, Any] = {
        "enabled": use_cache,
        "match_type": lookup.get("match_type", "none"),
        "similarity": lookup.get("similarity", 0.0),
        "cache_id": lookup.get("cache_id"),
        "evidence_hash": lookup.get("evidence_hash"),
        "reason": lookup.get("reason", "Local cache is disabled."),
    }
    if use_cache:
        store = store_cached_response(
            result,
            evidence_pack,
            question=question,
            city=city,
            mode=mode,
            language=language,
            cache_dir=cache_dir,
        )
        cache_metadata["store"] = store
        if store.get("evidence_hash"):
            cache_metadata["evidence_hash"] = store["evidence_hash"]
        if store.get("cache_id"):
            cache_metadata["cache_id"] = store["cache_id"]
    result["cache_metadata"] = cache_metadata
    json.dumps(result, ensure_ascii=False)
    return result


def get_llm_client_capabilities() -> dict[str, Any]:
    return {
        "supported_providers": ["fallback", "gemini"],
        "supported_modes": list(SUPPORTED_MODES),
        "supported_languages": ["en", "ru"],
        "default_model": DEFAULT_GEMINI_MODEL,
        "fallback_behavior": "Any missing key, SDK error, timeout, quota error, invalid JSON, or unsafe Gemini response uses deterministic fallback.",
        "internet_rag": False,
        "changes_model_outputs": False,
        "local_cache": True,
        "city1_only_retrieval": True,
    }


__all__ = [
    "DEFAULT_GEMINI_MODEL",
    "build_gemini_prompt",
    "call_gemini_structured",
    "estimate_evidence_packet_size",
    "generate_llm_response",
    "get_gemini_status",
    "get_llm_client_capabilities",
    "parse_gemini_json_response",
]
