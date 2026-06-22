# City1 v4 Phase 2 - Local Evidence Tools Report

## Status

Phase V4.2 is complete. The new layer reads frozen V2/V3 artifacts and returns compact, JSON-serializable evidence dictionaries. It does not train models, generate population estimates, call an external service, or modify evidence files.

## Implemented files

- `src/city1/llm_tools.py` - read-only local evidence API.
- `tests/test_llm_tools.py` - focused unit and serialization tests.
- `scripts/demo_v4_llm_tools.py` - read-only examples for Almaty and Kurchatov.
- `docs/V4_PHASE2_LOCAL_TOOLS_REPORT.md` - this implementation record.

## Implemented public functions

- `get_available_cities()`
- `get_city_summary(city)`
- `get_hotspot_summary(city, top_n=10)`
- `get_confidence_summary(city)`
- `get_uncertainty_summary(city)`
- `get_cell_evidence(city, cell_id)`
- `compare_cities(cities=None)`
- `get_claim_boundaries()`
- `get_method_summary()`
- `generate_evidence_pack(city, question="", mode="ask")`

Every major response includes `evidence_sources`. Functions that depend on optional files also include `missing_artifacts`. Unknown cities, unsupported cell requests, missing rows, empty numeric values, and missing files return bounded dictionaries rather than raising user-facing exceptions.

## Artifact sources read

The tools use frozen run `city1_v3_rf500m_e20_20260618T040646Z` and read from:

- `outputs/v3_uncertainty/<run_id>/`
- `reports/hotspot_prioritization_v3/<run_id>/`
- `reports/uncertainty_validation_v3/<run_id>/`
- `reports/district_interval_coverage_v3/<run_id>/`
- `reports/external_disagreement_alignment_v3/<run_id>/`
- `reports/paper_v3_uncertainty/<run_id>/limitations/`
- `data/external/city_population_reference_v2.csv`
- `data/external/city_status_registry_v2.csv`
- the unified manuscript and V3 paper summary for method provenance

The implementation uses the Python standard library for artifact loading. It returns no pandas, NumPy, GeoPandas, or `Path` objects.

## Supported cities

Full V3 reliability evidence:

- Almaty
- Astana
- Semey
- Shymkent

V2/basic registry and official-total evidence:

- Petropavlovsk
- Taraz
- Uralsk
- Ust Kamenogorsk

Partial registry support:

- Kurchatov
- Ridder

Kurchatov and Ridder remain listed in the broad V2/basic city inventory, but individual summaries use `support_level="partial"` because the frozen registry marks `feature_generated=False`.

## Preserved scientific limitations

- P10/P50/P90 remain proxy ensemble intervals, not true census uncertainty.
- `confidence_score` remains interpretation confidence, not probability of correctness.
- Hotspot classes remain screening and review categories, not verified hotspots.
- Weak-target interval coverage is exposed with its cautious interpretation.
- Error-versus-uncertainty alignment remains mixed and is not overstated.
- District interval coverage remains unavailable where frozen district assignments are missing.
- WorldPop and GHS-POP remain structural comparators, not ground truth.

## Verification

Compilation:

```powershell
python -m py_compile src\city1\llm_tools.py scripts\demo_v4_llm_tools.py tests\test_llm_tools.py
```

Unit tests in the current environment:

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -p test_llm_tools.py -v
```

Result: 11 tests passed.

The repository environments do not currently include `pytest`, so the requested `pytest tests/test_llm_tools.py` command could not run. The test suite uses standard `unittest`, remains discoverable by pytest when installed, and passed with the standard-library runner.

Read-only demo:

```powershell
python scripts\demo_v4_llm_tools.py
```

## Example verified evidence

For Almaty, the tools return:

- `support_level`: `full_v3`
- official total: `2351424`
- cell count: `3078`
- median relative uncertainty: `0.1696593416621771`
- priority cells: `842`
- high-value/high-confidence cells: `212`

Cell `Z1406` is found in the frozen Almaty output and is returned with P10/P50/P90, relative uncertainty, confidence band, hotspot class, and centroid. Its response explicitly states that this is proxy evidence rather than observed census truth.

## Known missing or limited evidence

- Full V3 cell, hotspot, confidence, and uncertainty evidence is unavailable outside the four frozen V3 cities.
- Kurchatov and Ridder do not have generated frozen feature tables in the registry.
- District interval coverage is still blocked where offline district assignment artifacts are absent.
- External disagreement and error-alignment evidence is mixed; local tools expose the recorded notes rather than converting them into stronger claims.

## Exact next phase

V4.3 - implement `src/city1/llm_fallback.py`, a deterministic fallback answer engine that consumes these evidence dictionaries and produces bounded city briefs, hotspot explanations, cell explanations, and reviewer-safe answers without an API key.
