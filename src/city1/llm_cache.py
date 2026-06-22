"""Local safe-answer cache and City1-only mini-RAG retrieval.

The module never accesses the internet. It stores only guardrail-approved
final responses and retrieves compact snippets from existing City1 artifacts.
"""

from __future__ import annotations

import difflib
import hashlib
import json
import math
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from city1.llm_guardrails import check_response_dict
from city1.llm_tools import (
    RUN_ID,
    get_available_cities,
    get_city_summary,
    get_claim_boundaries,
    get_confidence_summary,
    get_hotspot_summary,
    get_method_summary,
    get_uncertainty_summary,
)


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CACHE_DIR = ROOT / "data" / "v4_qa_cache"
SCHEMA_VERSION = "v4_cache_1"
SIMILARITY_THRESHOLD = 0.86

_HASH_EXCLUDED_KEYS = {
    "question",
    "token_saving_note",
    "retrieved_snippets",
    "retrieval_sources",
    "retrieval_note",
    "cache_hit",
    "cache_metadata",
}

_CACHED_RESPONSE_FIELDS = {
    "answer",
    "mode",
    "city",
    "language",
    "provider_requested",
    "provider_used",
    "fallback_used",
    "gemini",
    "guardrail",
    "used_safe_rewrite",
    "confidence_of_answer",
    "evidence_used",
    "claim_boundary_notes",
    "recommended_next_checks",
    "missing_artifacts",
    "structured_sections",
    "retrieved_snippets",
    "retrieval_sources",
    "retrieval_note",
}


def _dedupe(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(str(value) for value in values if value not in (None, "")))


def normalize_question(text: str) -> str:
    """Normalize matching text while preserving technical underscores/tokens."""
    value = unicodedata.normalize("NFKC", str(text or "")).lower().strip()
    value = re.sub(r"[^\w\-/]+", " ", value, flags=re.UNICODE)
    return re.sub(r"\s+", " ", value).strip()


def _json_safe(value: Any, *, exclude_hash_fields: bool = False) -> Any:
    if isinstance(value, dict):
        return {
            str(key): _json_safe(nested, exclude_hash_fields=exclude_hash_fields)
            for key, nested in sorted(value.items(), key=lambda item: str(item[0]))
            if not (exclude_hash_fields and str(key) in _HASH_EXCLUDED_KEYS)
        }
    if isinstance(value, (list, tuple)):
        return [_json_safe(item, exclude_hash_fields=exclude_hash_fields) for item in value]
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, Path):
        return str(value)
    return str(value)


def _stable_hash(value: Any, *, exclude_hash_fields: bool = False) -> str:
    payload = _json_safe(value, exclude_hash_fields=exclude_hash_fields)
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def compute_evidence_hash(evidence_pack: dict) -> str:
    return _stable_hash(evidence_pack if isinstance(evidence_pack, dict) else {}, exclude_hash_fields=True)


def compute_response_hash(response: dict) -> str:
    selected = {
        key: response.get(key)
        for key in sorted(_CACHED_RESPONSE_FIELDS)
        if isinstance(response, dict) and key in response
    }
    return _stable_hash(selected, exclude_hash_fields=True)


def make_cache_key(city: str, mode: str, language: str, question: str, evidence_hash: str) -> str:
    identity = {
        "city": normalize_question(city),
        "mode": str(mode or "ask").strip().lower(),
        "language": str(language or "en").strip().lower(),
        "question": normalize_question(question),
        "evidence_hash": str(evidence_hash),
        "schema_version": SCHEMA_VERSION,
    }
    return _stable_hash(identity)[:32]


def _cache_paths(cache_dir: str | Path | None) -> tuple[Path, Path, Path]:
    root = Path(cache_dir) if cache_dir is not None else DEFAULT_CACHE_DIR
    return root, root / "cache_index.jsonl", root / "cached_answers"


def _read_index(index_path: Path) -> list[dict[str, Any]]:
    if not index_path.exists():
        return []
    entries: dict[str, dict[str, Any]] = {}
    try:
        with index_path.open("r", encoding="utf-8-sig") as handle:
            for line in handle:
                if not line.strip():
                    continue
                try:
                    item = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(item, dict) and item.get("cache_id"):
                    entries[str(item["cache_id"])] = item
    except OSError:
        return []
    return list(entries.values())


def get_cache_status(cache_dir: str | Path | None = None) -> dict[str, Any]:
    root, index_path, answers_dir = _cache_paths(cache_dir)
    entries = _read_index(index_path)
    return {
        "enabled": True,
        "cache_dir": str(root),
        "entry_count": len(entries),
        "index_exists": index_path.exists(),
        "answers_dir_exists": answers_dir.exists(),
        "schema_version": SCHEMA_VERSION,
    }


def _load_cached_answer(answers_dir: Path, cache_id: str) -> dict[str, Any] | None:
    path = answers_dir / f"{cache_id}.json"
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeError):
        return None
    return value if isinstance(value, dict) else None


def lookup_cached_response(
    city: str,
    mode: str,
    language: str,
    question: str,
    evidence_pack: dict,
    cache_dir: str | Path | None = None,
    allow_similarity: bool = True,
) -> dict[str, Any]:
    root, index_path, answers_dir = _cache_paths(cache_dir)
    evidence_hash = compute_evidence_hash(evidence_pack)
    normalized = normalize_question(question)
    cache_id = make_cache_key(city, mode, language, question, evidence_hash)
    entries = _read_index(index_path)

    candidates: list[tuple[float, str, dict[str, Any]]] = []
    for entry in entries:
        if entry.get("schema_version") != SCHEMA_VERSION:
            continue
        if str(entry.get("evidence_hash")) != evidence_hash:
            continue
        if normalize_question(entry.get("city", "")) != normalize_question(city):
            continue
        if str(entry.get("mode", "")).lower() != str(mode or "ask").lower():
            continue
        if str(entry.get("language", "")).lower() != str(language or "en").lower():
            continue
        entry_question = str(entry.get("question_normalized", ""))
        if entry.get("cache_id") == cache_id or entry_question == normalized:
            candidates.append((1.0, "exact", entry))
        elif allow_similarity and normalized and entry_question:
            similarity = difflib.SequenceMatcher(None, normalized, entry_question).ratio()
            if similarity >= SIMILARITY_THRESHOLD:
                candidates.append((similarity, "similarity", entry))

    if not candidates:
        return {
            "hit": False,
            "match_type": "none",
            "similarity": 0.0,
            "cached_response": None,
            "reason": "No safe cache entry matched the current evidence hash and request context.",
            "cache_id": cache_id,
            "evidence_hash": evidence_hash,
            "cache_dir": str(root),
        }

    similarity, match_type, entry = max(candidates, key=lambda item: item[0])
    cached = _load_cached_answer(answers_dir, str(entry["cache_id"]))
    if cached is None:
        return {
            "hit": False,
            "match_type": "none",
            "similarity": 0.0,
            "cached_response": None,
            "reason": "Cache index entry exists but its safe-answer file is unavailable.",
            "cache_id": cache_id,
            "evidence_hash": evidence_hash,
            "cache_dir": str(root),
        }
    validation = check_response_dict(cached, language=language)
    if not validation["passed"] or validation["severity"] not in {"none", "low"}:
        return {
            "hit": False,
            "match_type": "none",
            "similarity": 0.0,
            "cached_response": None,
            "reason": "Cached response no longer passes current guardrail and grounding rules.",
            "cache_id": cache_id,
            "evidence_hash": evidence_hash,
            "cache_dir": str(root),
        }
    return {
        "hit": True,
        "match_type": match_type,
        "similarity": round(float(similarity), 4),
        "cached_response": cached,
        "reason": "A guardrail-approved response matched the current evidence context.",
        "cache_id": str(entry["cache_id"]),
        "evidence_hash": evidence_hash,
        "source": entry.get("source"),
        "created_at_utc": entry.get("created_at_utc"),
        "cache_dir": str(root),
    }


def _contains_secret_fields(value: Any) -> bool:
    if isinstance(value, dict):
        for key, nested in value.items():
            lowered = str(key).lower()
            if any(term in lowered for term in ("api_key", "secret", "environment", "raw_text", "authorization")):
                return True
            if _contains_secret_fields(nested):
                return True
    elif isinstance(value, (list, tuple)):
        return any(_contains_secret_fields(item) for item in value)
    return False


def _safe_cached_response(response: dict[str, Any]) -> dict[str, Any]:
    return {
        key: _json_safe(response[key])
        for key in sorted(_CACHED_RESPONSE_FIELDS)
        if key in response and key != "gemini"
    }


def store_cached_response(
    response: dict,
    evidence_pack: dict,
    question: str,
    city: str,
    mode: str,
    language: str,
    cache_dir: str | Path | None = None,
) -> dict[str, Any]:
    if not isinstance(response, dict):
        return {"stored": False, "cache_id": None, "reason": "Response is not a dictionary."}
    validation = check_response_dict(response, language=language)
    severity = str(response.get("guardrail", {}).get("severity", validation["severity"]))
    guardrail_passed = bool(response.get("guardrail", {}).get("passed", validation["passed"]))
    if not guardrail_passed or severity not in {"none", "low"} or not validation["passed"]:
        return {"stored": False, "cache_id": None, "reason": "Response did not pass safe guardrail and grounding requirements."}
    if not response.get("answer") or not response.get("evidence_used"):
        return {"stored": False, "cache_id": None, "reason": "Response lacks an answer or evidence_used."}
    if _contains_secret_fields(response):
        return {"stored": False, "cache_id": None, "reason": "Response contains a forbidden secret/raw field."}

    root, index_path, answers_dir = _cache_paths(cache_dir)
    evidence_hash = compute_evidence_hash(evidence_pack)
    cache_id = make_cache_key(city, mode, language, question, evidence_hash)
    safe_response = _safe_cached_response(response)
    response_hash = compute_response_hash(safe_response)
    provider_used = str(response.get("provider_used", "fallback"))
    source = "guarded_gemini" if provider_used == "gemini" else "fallback"
    entry = {
        "cache_id": cache_id,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "question_normalized": normalize_question(question),
        "question_original": str(question or ""),
        "city": str(city or ""),
        "mode": str(mode or "ask"),
        "language": str(language or "en"),
        "provider_requested": str(response.get("provider_requested", "fallback")),
        "provider_used": provider_used,
        "evidence_hash": evidence_hash,
        "response_hash": response_hash,
        "guardrail_passed": True,
        "guardrail_severity": severity,
        "answer": str(response["answer"]),
        "evidence_used": list(response.get("evidence_used", [])),
        "claim_boundary_notes": list(response.get("claim_boundary_notes", [])),
        "missing_artifacts": list(response.get("missing_artifacts", [])),
        "source": source,
        "schema_version": SCHEMA_VERSION,
    }
    try:
        answers_dir.mkdir(parents=True, exist_ok=True)
        answer_path = answers_dir / f"{cache_id}.json"
        temporary = answers_dir / f".{cache_id}.tmp"
        temporary.write_text(json.dumps(safe_response, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(answer_path)
        existing = {item["cache_id"]: item for item in _read_index(index_path)}
        existing[cache_id] = entry
        index_temp = root / ".cache_index.tmp"
        index_temp.write_text(
            "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in existing.values()),
            encoding="utf-8",
        )
        index_temp.replace(index_path)
    except OSError as exc:
        return {"stored": False, "cache_id": cache_id, "reason": f"Cache write failed: {exc}"}
    return {
        "stored": True,
        "cache_id": cache_id,
        "reason": "Guardrail-approved response stored in the local City1 cache.",
        "evidence_hash": evidence_hash,
        "response_hash": response_hash,
        "cache_dir": str(root),
    }


def _entry(entry_id: str, title: str, text: str, source: str, category: str, city: str | None = None) -> dict[str, Any]:
    return {
        "id": entry_id,
        "title": title,
        "text": re.sub(r"\s+", " ", str(text)).strip()[:4000],
        "source": source,
        "city": city,
        "category": category,
    }


def build_city1_retrieval_corpus() -> dict[str, Any]:
    """Build a compact corpus from local City1 summaries and documentation."""
    entries: list[dict[str, Any]] = []
    claims = get_claim_boundaries()
    method = get_method_summary()
    entries.append(_entry(
        "claim-boundaries", "City1 claim boundaries",
        "Allowed: " + "; ".join(claims.get("allowed_claims", [])) + ". Forbidden: " + "; ".join(claims.get("forbidden_claims", [])),
        "reports/paper_v3_uncertainty/limitations", "claim_boundary",
    ))
    entries.append(_entry(
        "method-summary", "City1 method and stage roles",
        json.dumps(method, ensure_ascii=False), "manuscript_package_city1_unified/sections", "method",
    ))

    available = get_available_cities()
    cities = list(dict.fromkeys(available.get("full_v3_cities", []) + available.get("v2_basic_cities", [])))
    full_v3 = set(available.get("full_v3_cities", []))
    for city in cities:
        summary = get_city_summary(city)
        entries.append(_entry(
            f"city-{normalize_question(city)}", f"{city} city evidence summary",
            json.dumps(summary, ensure_ascii=False), "data/external/city_status_registry_v2.csv", "city_summary", city,
        ))
        if city in full_v3:
            for category, title, payload, source in (
                ("hotspot", f"{city} hotspot screening summary", get_hotspot_summary(city, top_n=3), "reports/hotspot_prioritization_v3"),
                ("confidence", f"{city} confidence-band summary", get_confidence_summary(city), "reports/uncertainty_validation_v3"),
                ("uncertainty", f"{city} proxy-uncertainty summary", get_uncertainty_summary(city), "reports/uncertainty_validation_v3"),
            ):
                entries.append(_entry(
                    f"{category}-{normalize_question(city)}", title,
                    json.dumps(payload, ensure_ascii=False), source, category, city,
                ))

    docs_dir = ROOT / "docs"
    for path in sorted(docs_dir.glob("V4_*.md")):
        try:
            text = path.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError):
            continue
        category = "claim_boundary" if "CLAIM" in path.name else "limitation"
        entries.append(_entry(
            f"doc-{path.stem.lower()}", path.stem.replace("_", " ").title(), text,
            path.relative_to(ROOT).as_posix(), category,
        ))

    limitations_dir = ROOT / "reports" / "paper_v3_uncertainty" / RUN_ID / "limitations"
    for path in sorted(limitations_dir.glob("*.md")):
        try:
            text = path.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError):
            continue
        entries.append(_entry(
            f"limitation-{path.stem}", path.stem.replace("_", " ").title(), text,
            path.relative_to(ROOT).as_posix(), "limitation",
        ))
    return {"entries": entries, "entry_count": len(entries), "internet_used": False}


def _snippet(text: str, normalized_query: str, limit: int = 420) -> str:
    clean = re.sub(r"\s+", " ", text).strip()
    if len(clean) <= limit:
        return clean
    query_terms = [term for term in normalized_query.split() if len(term) > 2]
    lowered = clean.lower()
    positions = [lowered.find(term) for term in query_terms if lowered.find(term) >= 0]
    start = max(0, (min(positions) if positions else 0) - 80)
    end = min(len(clean), start + limit)
    return ("..." if start else "") + clean[start:end] + ("..." if end < len(clean) else "")


def retrieve_city1_snippets(
    query: str,
    city: str | None = None,
    top_k: int = 5,
    corpus: dict | None = None,
) -> dict[str, Any]:
    query_normalized = normalize_question(query)
    corpus_value = corpus if isinstance(corpus, dict) else build_city1_retrieval_corpus()
    entries = corpus_value.get("entries", []) if isinstance(corpus_value.get("entries", []), list) else []
    city_normalized = normalize_question(city or "")
    try:
        limit = max(1, min(int(top_k), 10))
    except (TypeError, ValueError):
        limit = 5

    scored: list[tuple[float, bool, dict[str, Any]]] = []
    query_tokens = set(query_normalized.split())
    for item in entries:
        item_city = normalize_question(item.get("city") or "")
        if city_normalized and item_city and item_city != city_normalized:
            continue
        searchable = normalize_question(f"{item.get('title', '')} {item.get('text', '')}")
        if not searchable:
            continue
        exact = bool(query_normalized and query_normalized in searchable)
        searchable_tokens = set(searchable.split())
        overlap = len(query_tokens & searchable_tokens) / max(1, len(query_tokens))
        sequence = difflib.SequenceMatcher(None, query_normalized, searchable[: max(200, len(query_normalized) * 4)]).ratio() if query_normalized else 0.0
        score = 1.0 if exact else min(0.99, 0.75 * overlap + 0.25 * sequence)
        if score > 0:
            scored.append((score, exact, item))
    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    selected = scored[:limit]
    method = "exact" if any(exact for _, exact, _ in selected) else ("difflib" if selected else "fallback")
    return {
        "query": str(query or ""),
        "city": city,
        "results": [
            {
                "id": item.get("id"),
                "title": item.get("title"),
                "snippet": _snippet(str(item.get("text", "")), query_normalized),
                "source": item.get("source"),
                "score": round(float(score), 4),
                "category": item.get("category"),
            }
            for score, _, item in selected
        ],
        "method": method,
        "internet_used": False,
    }


def augment_evidence_pack_with_retrieval(
    evidence_pack: dict,
    question: str,
    city: str | None = None,
    top_k: int = 5,
) -> dict[str, Any]:
    augmented = json.loads(json.dumps(evidence_pack if isinstance(evidence_pack, dict) else {}, ensure_ascii=False))
    retrieval = retrieve_city1_snippets(question, city=city, top_k=top_k)
    augmented["retrieved_snippets"] = retrieval["results"]
    augmented["retrieval_sources"] = _dedupe(item.get("source") for item in retrieval["results"])
    augmented["retrieval_note"] = (
        "Local City1-only deterministic retrieval; no internet or external evidence was used."
    )
    return augmented


def get_cache_capabilities() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "features": [
            "exact normalized-question cache matching",
            "difflib similarity matching within identical evidence context",
            "stable evidence and response hashes",
            "guardrail-approved answer storage only",
            "City1-only local snippet retrieval",
        ],
        "limitations": [
            "No internet retrieval or external vector database.",
            "Similarity matching is lexical rather than semantic.",
            "Cache invalidation relies on stable evidence hashes.",
            "Generated cache entries are runtime artifacts and must remain outside version control.",
        ],
        "default_cache_dir": str(DEFAULT_CACHE_DIR),
        "internet_rag": False,
    }


__all__ = [
    "DEFAULT_CACHE_DIR",
    "SCHEMA_VERSION",
    "augment_evidence_pack_with_retrieval",
    "build_city1_retrieval_corpus",
    "compute_evidence_hash",
    "compute_response_hash",
    "get_cache_capabilities",
    "get_cache_status",
    "lookup_cached_response",
    "make_cache_key",
    "normalize_question",
    "retrieve_city1_snippets",
    "store_cached_response",
]
