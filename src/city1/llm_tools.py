"""Read-only evidence tools for the City1 v4 interpretation assistant.

The module exposes compact, JSON-serializable dictionaries built only from
frozen V2/V3 artifacts. It never trains models, changes estimates, or writes
to the evidence folders.
"""

from __future__ import annotations

import csv
import json
import math
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
RUN_ID = "city1_v3_rf500m_e20_20260618T040646Z"
FULL_V3_CITIES = ("Almaty", "Astana", "Semey", "Shymkent")

OUTPUT_DIR = ROOT / "outputs" / "v3_uncertainty" / RUN_ID
HOTSPOT_DIR = ROOT / "reports" / "hotspot_prioritization_v3" / RUN_ID
VALIDATION_DIR = ROOT / "reports" / "uncertainty_validation_v3" / RUN_ID
DISTRICT_DIR = ROOT / "reports" / "district_interval_coverage_v3" / RUN_ID
EXTERNAL_DIR = ROOT / "reports" / "external_disagreement_alignment_v3" / RUN_ID
PAPER_DIR = ROOT / "reports" / "paper_v3_uncertainty" / RUN_ID
REGISTRY_PATH = ROOT / "data" / "external" / "city_status_registry_v2.csv"
POPULATION_PATH = ROOT / "data" / "external" / "city_population_reference_v2.csv"

CITY_SUMMARY_PATH = OUTPUT_DIR / "city_uncertainty_summary.csv"
HOTSPOT_SUMMARY_PATH = HOTSPOT_DIR / "hotspot_city_summary.csv"
TOP_HOTSPOTS_PATH = HOTSPOT_DIR / "top_hotspots_by_city.csv"
STABLE_HOTSPOTS_PATH = HOTSPOT_DIR / "stable_hotspots.csv"
CAUTION_HOTSPOTS_PATH = HOTSPOT_DIR / "caution_hotspots.csv"
CONFIDENCE_PATH = VALIDATION_DIR / "confidence_band_validation_summary.csv"
STABILITY_PATH = VALIDATION_DIR / "hotspot_stability_summary.csv"
INTERVAL_PATH = VALIDATION_DIR / "interval_coverage_weak_target.csv"
ALIGNMENT_PATH = VALIDATION_DIR / "error_uncertainty_alignment.csv"
DISTRICT_PATH = DISTRICT_DIR / "district_interval_city_summary.csv"
EXTERNAL_PATH = EXTERNAL_DIR / "external_disagreement_alignment.csv"
CLAIMS_ALLOWED_PATH = PAPER_DIR / "limitations" / "claims_allowed.md"
CLAIMS_FORBIDDEN_PATH = PAPER_DIR / "limitations" / "claims_not_allowed.md"
LIMITATIONS_PATH = PAPER_DIR / "limitations" / "limitation_summary.md"

_ALIASES = {
    "ust kamenogorsk": "ust kamenogorsk",
    "oskemen": "ust kamenogorsk",
    "nur sultan": "astana",
}

_ALLOWED_DEFAULTS = [
    "City1 produces an officially calibrated proxy population surface.",
    "V3 adds uncertainty-aware interpretation to the frozen proxy surface.",
    "P10/P50/P90 summarize ensemble spread inside the proxy framework.",
    "Confidence bands and hotspot classes support screening and review triage.",
    "Hotspot stability is the strongest V3 uncertainty evidence layer.",
]

_FORBIDDEN_DEFAULTS = [
    "City1 reconstructs true cell-level census counts.",
    "P10/P50/P90 are true census uncertainty intervals.",
    "confidence_score is a probability of correctness.",
    "WorldPop or GHS-POP are ground truth.",
    "hotspot_priority_class is verified population-hotspot truth.",
    "V4 improves population prediction accuracy or changes model outputs.",
    "City1 supports definitive administrative accounting or automated policy decisions.",
]


def _source(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


@lru_cache(maxsize=None)
def _load_csv(path_text: str) -> tuple[dict[str, str], ...]:
    path = Path(path_text)
    if not path.exists():
        return ()
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return tuple(dict(row) for row in csv.DictReader(handle))
    except (OSError, UnicodeError, csv.Error):
        return ()


def _rows(path: Path) -> list[dict[str, str]]:
    return [dict(row) for row in _load_csv(str(path))]


def _missing(paths: Iterable[Path]) -> list[str]:
    return [_source(path) for path in paths if not path.exists()]


def _dedupe(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def _bool(value: Any) -> bool | None:
    if value is None or str(value).strip() == "":
        return None
    normalized = str(value).strip().lower()
    if normalized in {"true", "1", "yes", "y"}:
        return True
    if normalized in {"false", "0", "no", "n"}:
        return False
    return None


def _number(value: Any, *, integer: bool = False) -> int | float | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(parsed):
        return None
    return int(parsed) if integer else float(parsed)


def _value(row: dict[str, Any] | None, *names: str) -> Any:
    if not row:
        return None
    by_lower = {key.lower(): value for key, value in row.items()}
    for name in names:
        if name in row:
            return row[name]
        if name.lower() in by_lower:
            return by_lower[name.lower()]
    return None


def _normalize_key(city: str | None) -> str:
    text = str(city or "").strip().lower()
    text = re.sub(r"[_\-]+", " ", text)
    text = re.sub(r"[^a-zа-яё0-9 ]+", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip()
    return _ALIASES.get(text, text)


def _registry_index() -> dict[str, dict[str, str]]:
    return {
        _normalize_key(_value(row, "normalized_city_name", "city_name")): row
        for row in _rows(REGISTRY_PATH)
    }


def _population_index() -> dict[str, dict[str, str]]:
    return {
        _normalize_key(_value(row, "normalized_city_name", "city_name")): row
        for row in _rows(POPULATION_PATH)
    }


def _city_context(city: str) -> dict[str, Any]:
    key = _normalize_key(city)
    registry = _registry_index().get(key)
    population = _population_index().get(key)
    v3_row = next(
        (row for row in _rows(CITY_SUMMARY_PATH) if _normalize_key(_value(row, "city", "city_slug")) == key),
        None,
    )
    canonical = _value(registry, "city_name") or _value(population, "city_name") or _value(v3_row, "city")
    if not canonical:
        return {"key": key, "city": str(city).strip(), "support_level": "unknown", "registry": None, "population": None, "v3": None}
    if canonical in FULL_V3_CITIES and v3_row:
        support = "full_v3"
    elif registry and _bool(_value(registry, "feature_generated")) is False:
        support = "partial"
    else:
        support = "v2_basic"
    return {"key": key, "city": canonical, "support_level": support, "registry": registry, "population": population, "v3": v3_row}


def _city_rows(path: Path, key: str) -> list[dict[str, str]]:
    return [row for row in _rows(path) if _normalize_key(_value(row, "city", "city_slug", "city_name")) == key]


def _compact_hotspot_row(row: dict[str, str]) -> dict[str, Any]:
    return {
        "cell_id": _value(row, "cell_id"),
        "hotspot_rank": _number(_value(row, "hotspot_rank"), integer=True),
        "p50": _number(_value(row, "p50", "population_estimate_final")),
        "relative_uncertainty": _number(_value(row, "relative_uncertainty")),
        "confidence_score": _number(_value(row, "confidence_score")),
        "confidence_band": _value(row, "confidence_band"),
        "hotspot_priority_class": _value(row, "hotspot_priority_class"),
        "latitude": _number(_value(row, "centroid_latitude", "latitude")),
        "longitude": _number(_value(row, "centroid_longitude", "longitude")),
    }


def _read_markdown_bullets(path: Path) -> list[str]:
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except (OSError, UnicodeError):
        return []
    return [line.lstrip("- ").strip() for line in lines if line.strip().startswith("-")]


def get_available_cities() -> dict[str, Any]:
    """Return city support groups from the frozen registry and V3 run."""
    registry_rows = _rows(REGISTRY_PATH)
    registry_cities = [_value(row, "city_name") for row in registry_rows if _value(row, "city_name")]
    full = [city for city in FULL_V3_CITIES if city in registry_cities or _city_context(city)["v3"]]
    basic = [city for city in registry_cities if city not in full]
    partial = [
        _value(row, "city_name")
        for row in registry_rows
        if _bool(_value(row, "feature_generated")) is False
    ]
    sources = [_source(path) for path in (REGISTRY_PATH, POPULATION_PATH, CITY_SUMMARY_PATH) if path.exists()]
    return {
        "full_v3_cities": full,
        "v2_basic_cities": basic,
        "partial_cities": partial,
        "run_id": RUN_ID,
        "evidence_sources": sources,
        "missing_artifacts": _missing((REGISTRY_PATH, POPULATION_PATH, CITY_SUMMARY_PATH)),
    }


def get_city_summary(city: str) -> dict[str, Any]:
    """Return compact city-level evidence without generating new estimates."""
    context = _city_context(city)
    v3 = context["v3"]
    registry = context["registry"]
    population = context["population"]
    sources = []
    if registry:
        sources.append(_source(REGISTRY_PATH))
    if population:
        sources.append(_source(POPULATION_PATH))
    if v3:
        sources.append(_source(CITY_SUMMARY_PATH))

    missing = _missing((REGISTRY_PATH, POPULATION_PATH))
    if context["support_level"] == "full_v3" and not v3:
        missing.append(_source(CITY_SUMMARY_PATH))

    official_total = _number(
        _value(v3, "official_total") or _value(population, "population") or _value(registry, "population"),
        integer=True,
    )
    if context["support_level"] == "full_v3":
        allowed = [
            "Interpret the calibrated proxy surface at city and screening levels.",
            "Describe frozen V3 uncertainty, confidence bands, and hotspot classes.",
        ]
        caution = [
            "Do not interpret the surface as true cell-level census counts.",
            "Do not interpret confidence_score as a probability of correctness.",
        ]
    elif context["support_level"] in {"v2_basic", "partial"}:
        allowed = ["Report registry support and the official city-total calibration anchor."]
        caution = ["Frozen V3 reliability evidence is unavailable for this city."]
        if context["support_level"] == "partial":
            caution.append("The registry does not mark generated frozen features as available.")
    else:
        allowed = []
        caution = ["The city is not present in the frozen City1 registry."]

    return {
        "city": context["city"],
        "normalized_city": context["key"],
        "support_level": context["support_level"],
        "official_total": official_total,
        "cell_count": _number(_value(v3, "n_cells") or _value(registry, "feature_row_count"), integer=True),
        "median_relative_uncertainty": _number(_value(v3, "median_relative_uncertainty")),
        "mean_uncertainty_width": _number(_value(v3, "mean_uncertainty_width")),
        "mean_confidence_score": _number(_value(v3, "mean_confidence_score")),
        "high_confidence_share": _number(_value(v3, "share_high_confidence")),
        "medium_confidence_share": _number(_value(v3, "share_medium_confidence")),
        "low_confidence_share": _number(_value(v3, "share_low_confidence")),
        "osm_label": _value(v3, "osm_completeness_label"),
        "district_support": _value(v3, "district_support_flag") or _value(registry, "district_benchmark_quality"),
        "interpretation": {"allowed": allowed, "caution": caution},
        "claim_boundary": "This is frozen proxy evidence, not cell-level census truth.",
        "evidence_sources": _dedupe(sources),
        "missing_artifacts": _dedupe(missing),
    }


def get_hotspot_summary(city: str, top_n: int = 10) -> dict[str, Any]:
    """Return screening-class summaries and compact hotspot examples."""
    context = _city_context(city)
    try:
        limit = max(0, min(int(top_n), 50))
    except (TypeError, ValueError):
        limit = 10
    summary_rows = _city_rows(HOTSPOT_SUMMARY_PATH, context["key"])
    summary = summary_rows[0] if summary_rows else None
    top = sorted(
        _city_rows(TOP_HOTSPOTS_PATH, context["key"]),
        key=lambda row: _number(_value(row, "hotspot_rank"), integer=True) or 10**9,
    )[:limit]
    stable = _city_rows(STABLE_HOTSPOTS_PATH, context["key"])
    caution = _city_rows(CAUTION_HOTSPOTS_PATH, context["key"])
    expected = (HOTSPOT_SUMMARY_PATH, TOP_HOTSPOTS_PATH, STABLE_HOTSPOTS_PATH, CAUTION_HOTSPOTS_PATH)
    sources = [_source(path) for path in expected if path.exists() and (summary or top or stable or caution)]
    if context["support_level"] != "full_v3":
        note = "Hotspot screening classes are unavailable because this city has no frozen full-V3 evidence."
    else:
        note = _value(summary, "interpretation_note") or "Hotspot classes support screening and triage only."
    return {
        "city": context["city"],
        "support_level": context["support_level"],
        "total_priority_cells": _number(_value(summary, "n_priority_cells"), integer=True),
        "high_value_high_confidence": _number(_value(summary, "n_high_value_high_confidence"), integer=True),
        "high_value_low_confidence": _number(_value(summary, "n_high_value_low_confidence"), integer=True),
        "medium_value_high_confidence": _number(_value(summary, "n_medium_value_high_confidence"), integer=True),
        "low_value_high_uncertainty": _number(_value(summary, "n_low_value_high_uncertainty"), integer=True),
        "stable_hotspot_cells": len(stable) if stable else 0,
        "caution_hotspot_cells": len(caution) if caution else 0,
        "top_hotspots": [_compact_hotspot_row(row) for row in top],
        "stable_examples": [_compact_hotspot_row(row) for row in stable[: min(limit, 3)]],
        "caution_examples": [_compact_hotspot_row(row) for row in caution[: min(limit, 3)]],
        "interpretation": note,
        "claim_boundary": "These are screening classes, not verified population hotspots.",
        "evidence_sources": _dedupe(sources),
        "missing_artifacts": _missing(expected),
    }


def get_confidence_summary(city: str) -> dict[str, Any]:
    """Return confidence-band evidence and its interpretation boundary."""
    context = _city_context(city)
    rows = _city_rows(CONFIDENCE_PATH, context["key"])
    bands: dict[str, dict[str, Any]] = {}
    for row in rows:
        band = str(_value(row, "confidence_band") or "unknown").lower()
        bands[band] = {
            "cell_count": _number(_value(row, "n_cells"), integer=True),
            "share": _number(_value(row, "share_cells")),
            "median_relative_uncertainty": _number(_value(row, "median_relative_uncertainty")),
            "priority_share": _number(_value(row, "share_hotspot_priority_cells")),
        }
    city_summary = get_city_summary(city)
    return {
        "city": context["city"],
        "support_level": context["support_level"],
        "high_share": bands.get("high", {}).get("share") or city_summary["high_confidence_share"],
        "medium_share": bands.get("medium", {}).get("share") or city_summary["medium_confidence_share"],
        "low_share": bands.get("low", {}).get("share") or city_summary["low_confidence_share"],
        "bands": bands,
        "interpretation": "Confidence bands summarize interpretation support and uncertainty burden within the proxy framework.",
        "claim_boundary": "confidence_score is not a probability of correctness.",
        "evidence_sources": [_source(CONFIDENCE_PATH)] if rows else city_summary["evidence_sources"],
        "missing_artifacts": _missing((CONFIDENCE_PATH,)) if context["support_level"] == "full_v3" else [],
    }


def get_uncertainty_summary(city: str) -> dict[str, Any]:
    """Return proxy-interval and validation evidence for one city."""
    context = _city_context(city)
    city_summary = get_city_summary(city)
    interval = next(iter(_city_rows(INTERVAL_PATH, context["key"])), None)
    alignment = next(iter(_city_rows(ALIGNMENT_PATH, context["key"])), None)
    district = next(iter(_city_rows(DISTRICT_PATH, context["key"])), None)
    external_rows = _city_rows(EXTERNAL_PATH, context["key"])
    sources = list(city_summary["evidence_sources"])
    for path, value in ((INTERVAL_PATH, interval), (ALIGNMENT_PATH, alignment), (DISTRICT_PATH, district), (EXTERNAL_PATH, external_rows)):
        if value:
            sources.append(_source(path))
    return {
        "city": context["city"],
        "support_level": context["support_level"],
        "median_relative_uncertainty": city_summary["median_relative_uncertainty"],
        "mean_uncertainty_width": city_summary["mean_uncertainty_width"],
        "weak_target_interval_coverage": _number(_value(interval, "coverage_p10_p90")),
        "median_interval_width": _number(_value(interval, "median_interval_width")),
        "error_width_alignment": {
            "pearson": _number(_value(alignment, "pearson_error_vs_uncertainty_width")),
            "spearman": _number(_value(alignment, "spearman_error_vs_uncertainty_width")),
            "note": _value(alignment, "interpretation_note"),
        },
        "district_interval_coverage": {
            "districts_compared": _number(_value(district, "n_districts_compared"), integer=True),
            "coverage_rate": _number(_value(district, "district_interval_coverage_rate")),
            "note": _value(district, "interpretation_note"),
        },
        "external_alignment": [
            {
                "product": _value(row, "benchmark_product"),
                "pearson": _number(_value(row, "pearson_disagreement_vs_uncertainty")),
                "spearman": _number(_value(row, "spearman_disagreement_vs_uncertainty")),
                "note": _value(row, "interpretation_note"),
            }
            for row in external_rows
        ],
        "interpretation": "Uncertainty describes ensemble spread and evidence reliability inside the calibrated proxy framework.",
        "claim_boundary": "P10/P50/P90 are proxy interval outputs, not true census uncertainty intervals.",
        "evidence_sources": _dedupe(sources),
        "missing_artifacts": _missing((CITY_SUMMARY_PATH, INTERVAL_PATH, ALIGNMENT_PATH, DISTRICT_PATH, EXTERNAL_PATH)) if context["support_level"] == "full_v3" else [],
    }


def get_cell_evidence(city: str, cell_id: str | int) -> dict[str, Any]:
    """Locate one frozen V3 cell and return its evidence fields."""
    context = _city_context(city)
    cell_path = OUTPUT_DIR / f"{context['key'].replace(' ', '_')}_uncertainty_cells.csv"
    base = {
        "city": context["city"],
        "cell_id": str(cell_id),
        "support_level": context["support_level"],
        "evidence_sources": [_source(cell_path)] if cell_path.exists() else [],
        "missing_artifacts": _missing((cell_path,)),
    }
    if context["support_level"] != "full_v3":
        return {**base, "found": False, "reason": "Cell-level V3 evidence is unavailable for this city.", "available_alternative": "Use city-level summary."}
    target = str(cell_id).strip().lower()
    row = next((item for item in _rows(cell_path) if str(_value(item, "cell_id")).strip().lower() == target), None)
    if not row:
        reason = "Cell output file is unavailable." if not cell_path.exists() else "The requested cell_id was not found in the frozen city output."
        return {**base, "found": False, "reason": reason, "available_alternative": "Use city-level or hotspot-level summary."}
    return {
        **base,
        "found": True,
        "p10": _number(_value(row, "p10", "Population_Estimate_P10")),
        "p50": _number(_value(row, "p50", "Population_Estimate_P50", "population_estimate_final")),
        "p90": _number(_value(row, "p90", "Population_Estimate_P90")),
        "relative_uncertainty": _number(_value(row, "relative_uncertainty", "Population_Uncertainty_Relative")),
        "confidence_score": _number(_value(row, "confidence_score")),
        "confidence_band": _value(row, "confidence_band", "Population_Confidence_Band"),
        "hotspot_priority_class": _value(row, "hotspot_priority_class"),
        "centroid": {
            "latitude": _number(_value(row, "centroid_latitude")),
            "longitude": _number(_value(row, "centroid_longitude")),
        },
        "interpretation": [
            "P50 is the calibrated median proxy estimate for this frozen run.",
            "Use the confidence band and hotspot class for screening, not census verification.",
        ],
        "claim_boundary": "This cell record is proxy evidence, not observed cell-level census truth.",
    }


def compare_cities(cities: list[str] | None = None) -> dict[str, Any]:
    """Compare frozen city summaries without ranking truth accuracy."""
    requested = list(FULL_V3_CITIES) if cities is None else list(cities)
    comparisons = []
    sources: list[str] = []
    missing: list[str] = []
    for city in requested:
        summary = get_city_summary(city)
        hotspots = get_hotspot_summary(city, top_n=0)
        comparisons.append({
            "city": summary["city"],
            "support_level": summary["support_level"],
            "official_total": summary["official_total"],
            "cell_count": summary["cell_count"],
            "median_relative_uncertainty": summary["median_relative_uncertainty"],
            "high_confidence_share": summary["high_confidence_share"],
            "priority_cells": hotspots["total_priority_cells"],
            "stable_hotspot_cells": hotspots["stable_hotspot_cells"],
            "caution": summary["interpretation"]["caution"],
        })
        sources.extend(summary["evidence_sources"] + hotspots["evidence_sources"])
        missing.extend(summary["missing_artifacts"] + hotspots["missing_artifacts"])
    full_rows = [row for row in comparisons if row["support_level"] == "full_v3"]
    ranking_notes = []
    if full_rows:
        highest_confidence = max(full_rows, key=lambda row: row["high_confidence_share"] or -1)
        highest_uncertainty = max(full_rows, key=lambda row: row["median_relative_uncertainty"] or -1)
        ranking_notes = [
            f"{highest_confidence['city']} has the largest high-confidence share in this frozen comparison.",
            f"{highest_uncertainty['city']} has the largest median relative uncertainty in this frozen comparison.",
        ]
    return {
        "cities": comparisons,
        "ranking_notes": ranking_notes,
        "claim_boundary": "These rankings compare proxy evidence and reliability indicators, not truth-level prediction accuracy.",
        "run_id": RUN_ID,
        "evidence_sources": _dedupe(sources),
        "missing_artifacts": _dedupe(missing),
    }


def get_claim_boundaries() -> dict[str, Any]:
    """Return project claim rules with safe defaults if documents are missing."""
    documented_allowed = _read_markdown_bullets(CLAIMS_ALLOWED_PATH)
    documented_limits = _read_markdown_bullets(CLAIMS_FORBIDDEN_PATH) + _read_markdown_bullets(LIMITATIONS_PATH)
    sources = [_source(path) for path in (CLAIMS_ALLOWED_PATH, CLAIMS_FORBIDDEN_PATH, LIMITATIONS_PATH) if path.exists()]
    return {
        "allowed_claims": _dedupe(documented_allowed or _ALLOWED_DEFAULTS),
        "forbidden_claims": _FORBIDDEN_DEFAULTS,
        "documented_limitations": _dedupe(documented_limits),
        "core_warning": "City1 outputs are calibrated proxy evidence. They are not true cell-level census counts or true census uncertainty.",
        "evidence_sources": sources,
        "missing_artifacts": _missing((CLAIMS_ALLOWED_PATH, CLAIMS_FORBIDDEN_PATH, LIMITATIONS_PATH)),
    }


def get_method_summary() -> dict[str, Any]:
    """Return the compact V2/V3/V4 role separation."""
    manuscript_sections = ROOT / "manuscript_package_city1_unified" / "sections"
    sources = [_source(path) for path in (PAPER_DIR / "paper_summary.md", manuscript_sections) if path.exists()]
    return {
        "v2_stage_1": {
            "role": "Deterministic calibrated proxy population surface.",
            "method": "OpenStreetMap-derived features, weak target construction, Random Forest on a 500 m grid, and official-total calibration.",
        },
        "v3_stage_2": {
            "role": "Uncertainty-aware reliability and screening layer.",
            "method": "Calibrated ensemble members produce P10/P50/P90, relative uncertainty, confidence bands, and hotspot classes.",
        },
        "v4_role": "Read and explain frozen V2/V3 evidence; never predict population or alter model outputs.",
        "claim_boundary": "The framework produces calibrated proxy surfaces, not true cell-level census reconstruction.",
        "evidence_sources": sources,
        "missing_artifacts": [],
    }


def generate_evidence_pack(city: str, question: str = "", mode: str = "ask") -> dict[str, Any]:
    """Assemble a compact closed-world evidence packet for later answer engines."""
    normalized_mode = str(mode or "ask").strip().lower()
    valid_modes = {"ask", "city_brief", "explain_cell", "hotspot_review", "compare_cities", "claim_checker", "reviewer_safe"}
    if normalized_mode not in valid_modes:
        normalized_mode = "ask"

    city_summary = get_city_summary(city)
    claims = get_claim_boundaries()
    method = get_method_summary()
    pack: dict[str, Any] = {
        "mode": normalized_mode,
        "city": city_summary["city"],
        "question": str(question or "").strip(),
        "city_summary": city_summary,
        "claim_boundaries": claims,
        "method_summary": method,
    }

    if normalized_mode in {"ask", "city_brief", "hotspot_review", "reviewer_safe"}:
        pack["hotspot_summary"] = get_hotspot_summary(city)
        pack["confidence_summary"] = get_confidence_summary(city)
        pack["uncertainty_summary"] = get_uncertainty_summary(city)
    elif normalized_mode == "explain_cell":
        match = re.search(r"\b(?:cell(?:_id)?\s*[:=#-]?\s*)?([A-Za-z]+\d+)\b", str(question or ""), flags=re.IGNORECASE)
        pack["cell_evidence"] = get_cell_evidence(city, match.group(1)) if match else {
            "found": False,
            "reason": "No cell identifier was found in the question.",
            "available_alternative": "Provide a cell ID such as Z1406.",
            "evidence_sources": [],
            "missing_artifacts": [],
        }
    elif normalized_mode == "compare_cities":
        pack["city_comparison"] = compare_cities()

    nested = [value for value in pack.values() if isinstance(value, dict)]
    pack["evidence_sources"] = _dedupe(
        source for value in nested for source in value.get("evidence_sources", [])
    )
    pack["missing_artifacts"] = _dedupe(
        item for value in nested for item in value.get("missing_artifacts", [])
    )
    pack["token_saving_note"] = "compact evidence packet only"
    return pack


def _assert_json_serializable(payload: dict[str, Any]) -> None:
    """Internal development helper retained for focused tests and demos."""
    json.dumps(payload, ensure_ascii=False)


__all__ = [
    "RUN_ID",
    "compare_cities",
    "generate_evidence_pack",
    "get_available_cities",
    "get_cell_evidence",
    "get_city_summary",
    "get_claim_boundaries",
    "get_confidence_summary",
    "get_hotspot_summary",
    "get_method_summary",
    "get_uncertainty_summary",
]
