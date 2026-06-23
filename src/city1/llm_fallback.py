"""Deterministic evidence-to-explanation fallback for City1 v4.

The fallback consumes dictionaries produced by :mod:`city1.llm_tools`. It is
read-only, performs no prediction, and keeps all scientific claim boundaries
explicit when an external language model is unavailable.
"""

from __future__ import annotations

import json
import re
from typing import Any, Iterable

from city1.llm_tools import (
    compare_cities,
    generate_evidence_pack,
    get_cell_evidence,
    get_claim_boundaries,
    get_method_summary,
)


SUPPORTED_LANGUAGES = ("en", "ru")
SUPPORTED_MODES = (
    "ask",
    "city_brief",
    "hotspot_review",
    "uncertainty_summary",
    "confidence_summary",
    "compare_cities",
    "explain_cell",
    "claim_checker",
    "reviewer_safe",
)

_LABELS = {
    "en": {
        "summary": "Summary",
        "evidence": "Evidence used",
        "cautions": "Claim boundaries",
        "next": "Recommended next checks",
        "unavailable": "not available",
    },
    "ru": {
        "summary": "Краткий вывод",
        "evidence": "Использованные данные",
        "cautions": "Границы утверждений",
        "next": "Рекомендуемые проверки",
        "unavailable": "нет данных",
    },
}

_OVERCLAIM_PATTERNS = {
    "true_census": (
        r"\btrue\s+(?:cell[- ]level\s+)?census\b",
        r"\breconstructs?\s+(?:the\s+)?true\s+population\b",
        r"истинн\w*\s+(?:данн\w*\s+)?перепис",
    ),
    "exact_population": (
        r"\bexact\s+(?:cell[- ]level\s+)?population\b",
        r"\baccurately\s+reconstructs?\b",
        r"точн\w*\s+численност",
    ),
    "ground_truth": (r"\bground\s*truth\b", r"наземн\w*\s+истин", r"эталонн\w*\s+истин"),
    "correctness_probability": (
        r"\bprobability\s+of\s+correctness\b",
        r"confidence_score\s+(?:is|means)\s+(?:a\s+)?probability",
        r"вероятност\w*\s+правильност",
    ),
    "verified_hotspot": (r"\bverified\s+(?:population\s+)?hotspot\b", r"подтвержденн\w*\s+hotspot"),
    "official_cell_census": (r"\bofficial\s+cell[- ]level\s+census\b", r"официальн\w*\s+перепис\w*\s+по\s+ячей"),
    "automated_policy": (r"\bfully\s+automated\s+policy\b", r"полност\w*\s+автоматиз\w*\s+решен"),
    "llm_accuracy": (
        r"\bllm\s+improv(?:es|ed)\s+(?:population\s+)?prediction\s+accuracy\b",
        r"llm\s+улучш\w*\s+точност\w*\s+прогноз",
    ),
}


def _language(language: str) -> tuple[str, bool]:
    normalized = str(language or "en").strip().lower()
    return (normalized, False) if normalized in SUPPORTED_LANGUAGES else ("en", True)


def _dedupe(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(str(value) for value in values if value not in (None, "")))


def _percent(value: Any, language: str) -> str:
    if value is None:
        return _LABELS[language]["unavailable"]
    try:
        return f"{float(value) * 100:.1f}%"
    except (TypeError, ValueError):
        return _LABELS[language]["unavailable"]


def _number(value: Any, decimals: int = 3) -> str:
    if value is None:
        return "n/a"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "n/a"
    if number.is_integer():
        return f"{int(number):,}"
    return f"{number:.{decimals}f}"


def _sources(pack: dict[str, Any]) -> list[str]:
    sources = list(pack.get("evidence_sources", []))
    for value in pack.values():
        if isinstance(value, dict):
            sources.extend(value.get("evidence_sources", []))
    return _dedupe(sources)


def _missing(pack: dict[str, Any]) -> list[str]:
    missing = list(pack.get("missing_artifacts", []))
    for value in pack.values():
        if isinstance(value, dict):
            missing.extend(value.get("missing_artifacts", []))
    return _dedupe(missing)


def _confidence(support_level: str, missing: list[str], mode: str) -> str:
    if support_level in {"unknown", "partial"}:
        return "low"
    if missing or support_level == "v2_basic" or mode in {"uncertainty_summary", "compare_cities", "reviewer_safe"}:
        return "medium"
    return "high"


def _compose_answer(
    language: str,
    summary: str,
    evidence: list[str],
    cautions: list[str],
    next_checks: list[str],
    extra_sections: list[tuple[str, list[str]]] | None = None,
) -> str:
    labels = _LABELS[language]
    blocks = [f"{labels['summary']}:\n{summary}"]
    for heading, items in extra_sections or []:
        if items:
            blocks.append(f"{heading}:\n" + "\n".join(f"- {item}" for item in items))
    if evidence:
        blocks.append(f"{labels['evidence']}:\n" + "\n".join(f"- {item}" for item in evidence))
    if cautions:
        blocks.append(f"{labels['cautions']}:\n" + "\n".join(f"- {item}" for item in cautions))
    if next_checks:
        blocks.append(f"{labels['next']}:\n" + "\n".join(f"- {item}" for item in next_checks))
    return "\n\n".join(blocks)


def _response(
    *,
    mode: str,
    city: str | None,
    language: str,
    summary: str,
    evidence: list[str],
    cautions: list[str],
    next_checks: list[str],
    evidence_used: list[str],
    missing_artifacts: list[str],
    support_level: str = "unknown",
    extra_sections: list[tuple[str, list[str]]] | None = None,
    language_fallback: bool = False,
) -> dict[str, Any]:
    caution_items = list(cautions)
    if language_fallback:
        caution_items.append("Requested language is unsupported; English fallback was used.")
    payload = {
        "answer": _compose_answer(language, summary, evidence, caution_items, next_checks, extra_sections),
        "mode": mode,
        "city": city,
        "language": language,
        "fallback_used": True,
        "confidence_of_answer": _confidence(support_level, missing_artifacts, mode),
        "evidence_used": _dedupe(evidence_used),
        "claim_boundary_notes": _dedupe(caution_items),
        "recommended_next_checks": _dedupe(next_checks),
        "missing_artifacts": _dedupe(missing_artifacts),
        "structured_sections": {
            "summary": summary,
            "evidence": evidence,
            "cautions": _dedupe(caution_items),
            "next_checks": _dedupe(next_checks),
        },
    }
    json.dumps(payload, ensure_ascii=False)
    return payload


def _base_pack(city: str | None, question: str, mode: str) -> dict[str, Any]:
    tool_mode = mode if mode in {"ask", "city_brief", "hotspot_review", "explain_cell", "compare_cities", "claim_checker", "reviewer_safe"} else "city_brief"
    return generate_evidence_pack(city or "", question=question, mode=tool_mode)


def generate_city_brief(evidence_pack: dict[str, Any], language: str = "en") -> dict[str, Any]:
    language, fallback = _language(language)
    city_summary = evidence_pack.get("city_summary", {})
    hotspot = evidence_pack.get("hotspot_summary", {})
    uncertainty = evidence_pack.get("uncertainty_summary", {})
    confidence = evidence_pack.get("confidence_summary", {})
    claims = evidence_pack.get("claim_boundaries", get_claim_boundaries())
    city = city_summary.get("city") or evidence_pack.get("city")
    support = city_summary.get("support_level", "unknown")
    missing = _missing(evidence_pack)

    if language == "ru":
        if support == "full_v3":
            summary = f"{city}: доступен полный frozen V3 reliability layer поверх calibrated proxy population surface."
        elif support == "v2_basic":
            summary = f"{city}: доступен базовый V2-контекст и официальный city-total anchor, но полного V3 reliability layer нет."
        elif support == "partial":
            summary = f"{city}: поддержка частичная; registry существует, но полного frozen feature/V3 evidence нет."
        else:
            summary = f"{city or 'Указанный город'} отсутствует в frozen City1 registry."
        evidence = [
            f"Уровень поддержки: {support}.",
            f"Официальный city-total anchor: {_number(city_summary.get('official_total'))}.",
            f"Количество grid cells: {_number(city_summary.get('cell_count'))}.",
        ]
        if support == "full_v3":
            evidence.extend([
                f"Median relative_uncertainty: {_number(city_summary.get('median_relative_uncertainty'))}.",
                f"High/medium/low confidence shares: {_percent(confidence.get('high_share'), language)} / {_percent(confidence.get('medium_share'), language)} / {_percent(confidence.get('low_share'), language)}.",
                f"Priority screening cells: {_number(hotspot.get('total_priority_cells'))}; high_value_high_confidence: {_number(hotspot.get('high_value_high_confidence'))}.",
            ])
        cautions = [
            "Поверхность является calibrated proxy, а не true cell-level census reconstruction.",
            "confidence_score — interpretation-confidence score, не probability of correctness.",
            "hotspot_priority_class — screening/triage class, не verified census truth.",
        ]
        next_checks = ["Проверить локальную OSM completeness и исходные карты перед практическим использованием."]
        if support != "full_v3":
            next_checks.append("Не использовать V3 uncertainty/hotspot интерпретацию без frozen V3 artifacts для этого города.")
        headings = ("Hotspot-интерпретация", "Uncertainty и confidence", "Что допустимо утверждать", "Что нельзя утверждать")
    else:
        if support == "full_v3":
            summary = f"{city} has the full frozen V3 reliability layer over the calibrated proxy population surface."
        elif support == "v2_basic":
            summary = f"{city} has V2 registry and official-total evidence, but no full frozen V3 reliability layer."
        elif support == "partial":
            summary = f"{city} has partial registry support; complete frozen feature and V3 evidence is unavailable."
        else:
            summary = f"{city or 'The requested city'} is not present in the frozen City1 registry."
        evidence = [
            f"Support level: {support}.",
            f"Official city-total calibration anchor: {_number(city_summary.get('official_total'))}.",
            f"Grid cells: {_number(city_summary.get('cell_count'))}.",
        ]
        if support == "full_v3":
            evidence.extend([
                f"Median relative uncertainty: {_number(city_summary.get('median_relative_uncertainty'))}.",
                f"High/medium/low confidence shares: {_percent(confidence.get('high_share'), language)} / {_percent(confidence.get('medium_share'), language)} / {_percent(confidence.get('low_share'), language)}.",
                f"Priority screening cells: {_number(hotspot.get('total_priority_cells'))}; high-value/high-confidence: {_number(hotspot.get('high_value_high_confidence'))}.",
            ])
        cautions = [
            "The surface is a calibrated proxy, not true cell-level census reconstruction.",
            "confidence_score is interpretation support, not a probability of correctness.",
            "hotspot_priority_class is a screening/triage class, not verified hotspot truth.",
        ]
        next_checks = ["Inspect local OSM completeness and source maps before operational use."]
        if support != "full_v3":
            next_checks.append("Do not infer V3 uncertainty or hotspot behavior without frozen V3 artifacts for this city.")
        headings = ("Hotspot interpretation", "Uncertainty and confidence", "What can be claimed", "What cannot be claimed")

    allowed = list(city_summary.get("interpretation", {}).get("allowed", [])) or list(claims.get("allowed_claims", []))[:2]
    forbidden = list(city_summary.get("interpretation", {}).get("caution", [])) or list(claims.get("forbidden_claims", []))[:2]
    extra = [
        (headings[0], [hotspot.get("interpretation")] if hotspot.get("interpretation") else []),
        (headings[1], [uncertainty.get("interpretation")] if uncertainty.get("interpretation") else []),
        (headings[2], allowed),
        (headings[3], forbidden),
    ]
    return _response(
        mode="city_brief", city=city, language=language, summary=summary, evidence=evidence,
        cautions=cautions, next_checks=next_checks, evidence_used=_sources(evidence_pack),
        missing_artifacts=missing, support_level=support, extra_sections=extra, language_fallback=fallback,
    )


def generate_hotspot_review(evidence_pack: dict[str, Any], language: str = "en") -> dict[str, Any]:
    language, fallback = _language(language)
    city_summary = evidence_pack.get("city_summary", {})
    hotspot = evidence_pack.get("hotspot_summary", {})
    city = city_summary.get("city") or evidence_pack.get("city")
    support = city_summary.get("support_level", hotspot.get("support_level", "unknown"))
    if language == "ru":
        summary = (
            f"Для {city} найдено {_number(hotspot.get('total_priority_cells'))} priority screening cells."
            if support == "full_v3" else f"Для {city} полный frozen hotspot review недоступен."
        )
        evidence = [
            f"high_value_high_confidence: {_number(hotspot.get('high_value_high_confidence'))}.",
            f"high_value_low_confidence: {_number(hotspot.get('high_value_low_confidence'))}.",
            f"medium_value_high_confidence: {_number(hotspot.get('medium_value_high_confidence'))}.",
            f"low_value_high_uncertainty: {_number(hotspot.get('low_value_high_uncertainty'))}.",
            f"Stable/caution examples available: {_number(hotspot.get('stable_hotspot_cells'))} / {_number(hotspot.get('caution_hotspot_cells'))}.",
        ]
        cautions = ["Это screening/triage classes, не verified hotspot truth и не official cell-level census."]
        next_checks = ["Для caution-heavy cells проверить локальные данные и OSM support до prioritization."]
        extra = [
            ("Stable screening candidates", ["high_value_high_confidence и medium_value_high_confidence имеют более сильную interpretation support."]),
            ("Caution-heavy classes", ["high_value_low_confidence и low_value_high_uncertainty требуют ручной проверки."]),
        ]
    else:
        summary = (
            f"{city} has {_number(hotspot.get('total_priority_cells'))} priority screening cells in the frozen V3 output."
            if support == "full_v3" else f"A full frozen hotspot review is unavailable for {city}."
        )
        evidence = [
            f"high_value_high_confidence: {_number(hotspot.get('high_value_high_confidence'))}.",
            f"high_value_low_confidence: {_number(hotspot.get('high_value_low_confidence'))}.",
            f"medium_value_high_confidence: {_number(hotspot.get('medium_value_high_confidence'))}.",
            f"low_value_high_uncertainty: {_number(hotspot.get('low_value_high_uncertainty'))}.",
            f"Stable/caution examples available: {_number(hotspot.get('stable_hotspot_cells'))} / {_number(hotspot.get('caution_hotspot_cells'))}.",
        ]
        cautions = ["These are screening/triage classes, not verified hotspot truth or official cell-level census evidence."]
        next_checks = ["Review local data and OSM support for caution-heavy cells before prioritization."]
        extra = [
            ("Stable screening candidates", ["high_value_high_confidence and medium_value_high_confidence have stronger interpretation support."]),
            ("Caution-heavy classes", ["high_value_low_confidence and low_value_high_uncertainty require manual review."]),
        ]
    return _response(
        mode="hotspot_review", city=city, language=language, summary=summary, evidence=evidence,
        cautions=cautions, next_checks=next_checks, evidence_used=_sources(evidence_pack),
        missing_artifacts=_missing(evidence_pack), support_level=support, extra_sections=extra,
        language_fallback=fallback,
    )


def generate_uncertainty_summary(evidence_pack: dict[str, Any], language: str = "en") -> dict[str, Any]:
    language, fallback = _language(language)
    city_summary = evidence_pack.get("city_summary", {})
    uncertainty = evidence_pack.get("uncertainty_summary", {})
    city = city_summary.get("city") or evidence_pack.get("city")
    support = city_summary.get("support_level", uncertainty.get("support_level", "unknown"))
    alignment = uncertainty.get("error_width_alignment", {})
    district = uncertainty.get("district_interval_coverage", {})
    if language == "ru":
        summary = f"P50 — median calibrated proxy estimate для {city}; P10/P90 задают ensemble-spread proxy interval."
        evidence = [
            f"Median relative_uncertainty: {_number(uncertainty.get('median_relative_uncertainty'))}.",
            f"Median interval width: {_number(uncertainty.get('median_interval_width'))}.",
            f"Weak-target P10–P90 coverage: {_percent(uncertainty.get('weak_target_interval_coverage'), language)}.",
            f"Error-width alignment Pearson/Spearman: {_number(alignment.get('pearson'))} / {_number(alignment.get('spearman'))}.",
            f"District interval coverage: {_percent(district.get('coverage_rate'), language)}.",
        ]
        cautions = [
            "P10/P50/P90 — proxy intervals, не true census uncertainty.",
            "Interval coverage и error-width alignment являются mixed/limited evidence и не гарантируют cell-level correctness.",
        ]
        next_checks = ["Сопоставить interval width с локальным OSM context и вручную проверить зоны высокой uncertainty."]
    else:
        summary = f"P50 is the median calibrated proxy estimate for {city}; P10/P90 bound the ensemble-spread proxy interval."
        evidence = [
            f"Median relative uncertainty: {_number(uncertainty.get('median_relative_uncertainty'))}.",
            f"Median interval width: {_number(uncertainty.get('median_interval_width'))}.",
            f"Weak-target P10-P90 coverage: {_percent(uncertainty.get('weak_target_interval_coverage'), language)}.",
            f"Error-width alignment Pearson/Spearman: {_number(alignment.get('pearson'))} / {_number(alignment.get('spearman'))}.",
            f"District interval coverage: {_percent(district.get('coverage_rate'), language)}.",
        ]
        cautions = [
            "P10/P50/P90 are proxy intervals, not true census uncertainty.",
            "Interval coverage and error-width alignment are mixed/limited evidence and do not guarantee cell-level correctness.",
        ]
        next_checks = ["Read interval width with local OSM context and manually review high-uncertainty zones."]
    return _response(
        mode="uncertainty_summary", city=city, language=language, summary=summary, evidence=evidence,
        cautions=cautions, next_checks=next_checks, evidence_used=_sources(evidence_pack),
        missing_artifacts=_missing(evidence_pack), support_level=support, language_fallback=fallback,
    )


def generate_confidence_summary(evidence_pack: dict[str, Any], language: str = "en") -> dict[str, Any]:
    language, fallback = _language(language)
    city_summary = evidence_pack.get("city_summary", {})
    confidence = evidence_pack.get("confidence_summary", {})
    city = city_summary.get("city") or evidence_pack.get("city")
    support = city_summary.get("support_level", confidence.get("support_level", "unknown"))
    bands = confidence.get("bands", {})
    band_items = []
    for band in ("high", "medium", "low"):
        item = bands.get(band, {})
        band_items.append(
            f"{band}: share {_percent(item.get('share'), language)}, median relative_uncertainty {_number(item.get('median_relative_uncertainty'))}, priority share {_percent(item.get('priority_share'), language)}."
        )
    if language == "ru":
        summary = f"confidence_score и confidence_band для {city} описывают interpretation support внутри proxy framework."
        cautions = ["confidence_score — не probability of correctness и не мера истинности населения в ячейке."]
        next_checks = ["Низкий confidence_band использовать как сигнал для ручной проверки, а не как автоматический отказ."]
    else:
        summary = f"confidence_score and confidence_band describe interpretation support for {city} inside the proxy framework."
        cautions = ["confidence_score is not a probability of correctness and does not measure cell-level population truth."]
        next_checks = ["Use a low confidence_band as a manual-review signal, not an automatic rejection rule."]
    return _response(
        mode="confidence_summary", city=city, language=language, summary=summary, evidence=band_items,
        cautions=cautions, next_checks=next_checks, evidence_used=_sources(evidence_pack),
        missing_artifacts=_missing(evidence_pack), support_level=support, language_fallback=fallback,
    )


def generate_cell_explanation(
    evidence_pack: dict[str, Any], cell_id: str | int | None = None, language: str = "en"
) -> dict[str, Any]:
    language, fallback = _language(language)
    city_summary = evidence_pack.get("city_summary", {})
    city = city_summary.get("city") or evidence_pack.get("city")
    support = city_summary.get("support_level", "unknown")
    cell = evidence_pack.get("cell_evidence")
    if (not cell or not cell.get("found")) and cell_id is not None and city:
        cell = get_cell_evidence(city, cell_id)
    cell = cell or {"found": False, "reason": "No cell identifier was supplied.", "evidence_sources": [], "missing_artifacts": []}
    combined_pack = dict(evidence_pack)
    combined_pack["cell_evidence"] = cell
    if not cell.get("found"):
        if language == "ru":
            summary = f"Cell-level evidence для {city} не найдено: {cell.get('reason', 'нет данных')}"
            cautions = ["Без frozen cell record нельзя интерпретировать P10/P50/P90 или hotspot_priority_class."]
            next_checks = [cell.get("available_alternative", "Используйте city-level или hotspot-level summary.")]
        else:
            summary = f"Cell-level evidence for {city} was not found: {cell.get('reason', 'unavailable')}"
            cautions = ["Without a frozen cell record, P10/P50/P90 and hotspot_priority_class cannot be interpreted."]
            next_checks = [cell.get("available_alternative", "Use a city-level or hotspot-level summary.")]
        return _response(
            mode="explain_cell", city=city, language=language, summary=summary, evidence=[], cautions=cautions,
            next_checks=next_checks, evidence_used=_sources(combined_pack), missing_artifacts=_missing(combined_pack),
            support_level=support, language_fallback=fallback,
        )

    hotspot_class = cell.get("hotspot_priority_class")
    stable = hotspot_class in {"high_value_high_confidence", "medium_value_high_confidence"}
    if language == "ru":
        summary = f"Ячейка {cell.get('cell_id')} в {city}: P50={_number(cell.get('p50'))}, confidence_band={cell.get('confidence_band')}, hotspot_priority_class={hotspot_class}."
        evidence = [
            f"P10/P50/P90: {_number(cell.get('p10'))} / {_number(cell.get('p50'))} / {_number(cell.get('p90'))}.",
            f"relative_uncertainty: {_number(cell.get('relative_uncertainty'))}.",
            f"confidence_score: {_number(cell.get('confidence_score'))}; confidence_band: {cell.get('confidence_band')}.",
            f"Интерпретация класса: {'более стабильный screening candidate' if stable else 'caution-heavy или background class'}.",
        ]
        cautions = ["Это frozen proxy cell evidence, не verified census truth и не official cell-level census count."]
        next_checks = ["Проверить карту, OSM context и локальные источники перед практическим решением."]
    else:
        summary = f"Cell {cell.get('cell_id')} in {city}: P50={_number(cell.get('p50'))}, confidence_band={cell.get('confidence_band')}, hotspot_priority_class={hotspot_class}."
        evidence = [
            f"P10/P50/P90: {_number(cell.get('p10'))} / {_number(cell.get('p50'))} / {_number(cell.get('p90'))}.",
            f"Relative uncertainty: {_number(cell.get('relative_uncertainty'))}.",
            f"confidence_score: {_number(cell.get('confidence_score'))}; confidence_band: {cell.get('confidence_band')}.",
            f"Class interpretation: {'more stable screening candidate' if stable else 'caution-heavy or background class'}.",
        ]
        cautions = ["This is frozen proxy cell evidence, not verified census truth or an official cell-level census count."]
        next_checks = ["Inspect the map, OSM context, and local sources before an operational decision."]
    return _response(
        mode="explain_cell", city=city, language=language, summary=summary, evidence=evidence,
        cautions=cautions, next_checks=next_checks, evidence_used=_sources(combined_pack),
        missing_artifacts=_missing(combined_pack), support_level=support, language_fallback=fallback,
    )


def generate_city_comparison(cities: list[str] | None = None, language: str = "en") -> dict[str, Any]:
    language, fallback = _language(language)
    comparison = compare_cities(cities)
    rows = comparison.get("cities", [])
    evidence = []
    for row in rows:
        evidence.append(
            f"{row.get('city')}: support={row.get('support_level')}, official total={_number(row.get('official_total'))}, "
            f"cells={_number(row.get('cell_count'))}, median relative_uncertainty={_number(row.get('median_relative_uncertainty'))}, "
            f"high-confidence share={_percent(row.get('high_confidence_share'), language)}, priority cells={_number(row.get('priority_cells'))}."
        )
    if language == "ru":
        summary = "Сравнение показывает различия в interpretation support и frozen proxy indicators между городами."
        cautions = ["Нельзя утверждать, что город с более сильной support метрикой точнее предсказан относительно true population."]
        next_checks = ["Сравнивать только города с одинаковым support level и учитывать OSM completeness."]
    else:
        summary = "The comparison describes differences in interpretation support and frozen proxy indicators across cities."
        cautions = ["A stronger support indicator does not mean a city is more accurately predicted against true population."]
        next_checks = ["Compare like-for-like support levels and retain OSM completeness context."]
    support = "full_v3" if rows and all(row.get("support_level") == "full_v3" for row in rows) else "partial"
    return _response(
        mode="compare_cities", city=None, language=language, summary=summary, evidence=evidence,
        cautions=cautions, next_checks=next_checks, evidence_used=comparison.get("evidence_sources", []),
        missing_artifacts=comparison.get("missing_artifacts", []), support_level=support,
        extra_sections=[("Ranking notes" if language == "en" else "Сравнительные заметки", comparison.get("ranking_notes", []))],
        language_fallback=fallback,
    )


def generate_reviewer_safe_answer(
    evidence_pack: dict[str, Any], question: str = "", language: str = "en"
) -> dict[str, Any]:
    """Generate a conservative reviewer-facing answer instead of reusing city-brief prose."""
    language, fallback = _language(language)
    city_summary = evidence_pack.get("city_summary", {})
    city = city_summary.get("city") or evidence_pack.get("city")
    support = city_summary.get("support_level", "unknown")
    missing = _missing(evidence_pack)
    lowered = str(question or "").strip().lower()
    is_policy_census_question = any(
        term in lowered
        for term in (
            "official census",
            "census evidence",
            "policy decision",
            "policy decisions",
            "official policy",
            "policy",
            "перепис",
            "официаль",
        )
    )

    if language == "ru":
        summary = (
            "Нет. City1 v4 не должен использоваться как official census evidence for policy decisions."
            if is_policy_census_question
            else "City1 v4 должен использоваться как reviewer-safe interpretation layer, а не как источник official census evidence."
        )
        evidence = [
            "City1 v4 — это tool-grounded interpretation assistant.",
            "Он объясняет calibrated proxy population surfaces и frozen V2/V3 reliability evidence.",
            "Он может поддерживать screening, explanation, reviewer-facing interpretation и manual review.",
            f"Current support level for {city or 'the requested city'}: {support}.",
        ]
        cautions = [
            "City1 v4 не должен использоваться как official census evidence.",
            "Он не восстанавливает true cell-level census counts.",
            "Он не оценивает true census uncertainty.",
            "Он не должен оправдывать automated policy decisions без external administrative review.",
            "confidence_score — это interpretation support, а не probability of correctness.",
            "hotspot_priority_class — это screening/triage class, а не verified hotspot truth.",
            "WorldPop и GHS-POP — structural comparators, а не ground truth.",
            "Reviewer-safe mode: mixed и unavailable evidence не интерпретируются как положительный результат.",
        ]
        next_checks = [
            "Использовать City1 v4 только для bounded explanation, cautious screening и reviewer-facing interpretation.",
            "Для policy use сохранять external administrative review и независимые локальные источники.",
        ]
    else:
        summary = (
            "No. City1 v4 should not be used as official census evidence for policy decisions."
            if is_policy_census_question
            else "City1 v4 should be used as a reviewer-safe interpretation layer, not as official census evidence."
        )
        evidence = [
            "City1 v4 is a tool-grounded interpretation assistant.",
            "It explains calibrated proxy population surfaces and frozen V2/V3 reliability evidence.",
            "It can support screening, explanation, reviewer-facing interpretation, and manual review.",
            f"Current support level for {city or 'the requested city'}: {support}.",
        ]
        cautions = [
            "City1 v4 should not be used as official census evidence.",
            "It is not true cell-level census evidence.",
            "It does not reconstruct true cell-level census counts.",
            "It does not estimate true census uncertainty.",
            "It should not justify automated policy decisions without external administrative review.",
            "confidence_score is interpretation support, not a probability of correctness.",
            "hotspot_priority_class is a screening/triage class, not verified hotspot truth.",
            "WorldPop and GHS-POP are structural comparators, not ground truth.",
            "Reviewer-safe mode: mixed and unavailable evidence is not interpreted as positive evidence.",
        ]
        next_checks = [
            "Use City1 v4 for bounded explanation, cautious screening, and reviewer-facing interpretation only.",
            "For policy use, retain external administrative review and independent local evidence.",
        ]

    return _response(
        mode="reviewer_safe", city=city, language=language, summary=summary, evidence=evidence,
        cautions=cautions, next_checks=next_checks, evidence_used=_sources(evidence_pack),
        missing_artifacts=missing, support_level=support, language_fallback=fallback,
    )


def check_text_for_overclaims(text: str, language: str = "en") -> dict[str, Any]:
    """Run a lightweight phrase-based pre-check; V4.6 will add full guardrails."""
    language, fallback = _language(language)
    value = str(text or "")
    risks = []
    for label, patterns in _OVERCLAIM_PATTERNS.items():
        if any(re.search(pattern, value, flags=re.IGNORECASE) for pattern in patterns):
            risks.append(label)
    if language == "ru":
        safe = (
            "City1 создаёт calibrated proxy population surface и uncertainty-aware screening layer; результаты не являются true cell-level census truth или true census uncertainty."
            if risks else "Явных overclaim-фраз не найдено, но утверждение всё равно должно опираться на frozen City1 evidence."
        )
        notes = ["Это лёгкий phrase-based pre-check, а не полный semantic guardrail V4.6."]
    else:
        safe = (
            "City1 provides a calibrated proxy population surface and an uncertainty-aware screening layer; outputs are not true cell-level census truth or true census uncertainty."
            if risks else "No obvious overclaim phrase was detected, but the statement must still be tied to frozen City1 evidence."
        )
        notes = ["This is a lightweight phrase-based pre-check, not the full semantic V4.6 guardrail."]
    if fallback:
        notes.append("Requested language is unsupported; English fallback was used.")
    result = {
        "has_risk": bool(risks),
        "risk_phrases": risks,
        "safe_rewrite": safe,
        "notes": notes,
        "answer": safe,
        "mode": "claim_checker",
        "city": None,
        "language": language,
        "fallback_used": True,
        "confidence_of_answer": "high" if risks else "medium",
        "evidence_used": get_claim_boundaries().get("evidence_sources", []),
        "claim_boundary_notes": notes,
        "recommended_next_checks": ["Run the future V4.6 guardrail before publication or policy-facing use."],
        "missing_artifacts": [],
        "structured_sections": {
            "summary": safe,
            "evidence": risks,
            "cautions": notes,
            "next_checks": ["Run the future V4.6 guardrail before publication or policy-facing use."],
        },
    }
    json.dumps(result, ensure_ascii=False)
    return result


def _generate_general_answer(pack: dict[str, Any], question: str, language: str, reviewer_safe: bool = False) -> dict[str, Any]:
    if reviewer_safe:
        return generate_reviewer_safe_answer(pack, question=question, language=language)
    lowered = question.lower()
    if any(term in lowered for term in ("uncertainty", "p10", "p50", "p90", "интервал", "неопредел")):
        result = generate_uncertainty_summary(pack, language)
    elif any(term in lowered for term in ("confidence", "уверен", "довер")):
        result = generate_confidence_summary(pack, language)
    elif any(term in lowered for term in ("hotspot", "priority", "приоритет", "горяч")):
        result = generate_hotspot_review(pack, language)
    else:
        result = generate_city_brief(pack, language)
    result["mode"] = "reviewer_safe" if reviewer_safe else "ask"
    if reviewer_safe:
        if result["language"] == "ru":
            note = "Reviewer-safe mode: mixed и unavailable evidence не интерпретируются как положительный результат."
        else:
            note = "Reviewer-safe mode: mixed and unavailable evidence is not interpreted as positive evidence."
        result["claim_boundary_notes"] = _dedupe(result["claim_boundary_notes"] + [note])
        result["structured_sections"]["cautions"] = result["claim_boundary_notes"]
        result["answer"] += f"\n\n{_LABELS[result['language']]['cautions']}:\n- {note}"
        result["confidence_of_answer"] = "medium" if result["confidence_of_answer"] == "high" else result["confidence_of_answer"]
    return result


def generate_fallback_response(
    evidence_pack: dict[str, Any] | None = None,
    city: str | None = None,
    question: str = "",
    mode: str = "ask",
    language: str = "en",
    cell_id: str | int | None = None,
    cities: list[str] | None = None,
) -> dict[str, Any]:
    """Generate one deterministic response from frozen City1 evidence."""
    normalized_mode = str(mode or "ask").strip().lower()
    if normalized_mode not in SUPPORTED_MODES:
        normalized_mode = "ask"
    if normalized_mode == "compare_cities":
        return generate_city_comparison(cities, language)
    if normalized_mode == "claim_checker":
        return check_text_for_overclaims(question, language)

    pack = evidence_pack if isinstance(evidence_pack, dict) else _base_pack(city, question, normalized_mode)
    if normalized_mode == "explain_cell":
        if "cell_evidence" not in pack and cell_id is not None:
            pack = dict(pack)
            pack["cell_evidence"] = get_cell_evidence(city or pack.get("city", ""), cell_id)
        return generate_cell_explanation(pack, cell_id=cell_id, language=language)
    if normalized_mode == "city_brief":
        return generate_city_brief(pack, language)
    if normalized_mode == "hotspot_review":
        return generate_hotspot_review(pack, language)
    if normalized_mode == "uncertainty_summary":
        return generate_uncertainty_summary(pack, language)
    if normalized_mode == "confidence_summary":
        return generate_confidence_summary(pack, language)
    return _generate_general_answer(pack, question, language, reviewer_safe=normalized_mode == "reviewer_safe")


def get_fallback_capabilities() -> dict[str, Any]:
    boundaries = get_claim_boundaries()
    method = get_method_summary()
    return {
        "supported_modes": list(SUPPORTED_MODES),
        "supported_languages": list(SUPPORTED_LANGUAGES),
        "default_language": "en",
        "evidence_dependency": "Frozen local dictionaries from city1.llm_tools only.",
        "limitations": [
            "No population prediction or model modification.",
            "No internet retrieval or external LLM call.",
            "Phrase-based claim checking is preliminary until V4.6.",
            "Full V3 interpretation is limited to Almaty, Astana, Semey, and Shymkent.",
        ],
        "fallback_used": True,
        "evidence_used": _dedupe(boundaries.get("evidence_sources", []) + method.get("evidence_sources", [])),
        "claim_boundary_notes": [boundaries.get("core_warning")],
        "missing_artifacts": _dedupe(boundaries.get("missing_artifacts", []) + method.get("missing_artifacts", [])),
    }


__all__ = [
    "SUPPORTED_LANGUAGES",
    "SUPPORTED_MODES",
    "check_text_for_overclaims",
    "generate_cell_explanation",
    "generate_city_brief",
    "generate_city_comparison",
    "generate_confidence_summary",
    "generate_fallback_response",
    "generate_hotspot_review",
    "generate_uncertainty_summary",
    "get_fallback_capabilities",
]
