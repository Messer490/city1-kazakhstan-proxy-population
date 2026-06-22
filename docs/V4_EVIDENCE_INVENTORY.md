# City1 v4 Evidence Inventory

## Summary

Phase 1 inventory identifies which frozen artifacts can support a tool-grounded LLM assistant.

## Supported city modes

- Full V3 reliability mode:
  - Almaty
  - Astana
  - Semey
  - Shymkent

- V2/basic mode:
  - Petropavlovsk
  - Taraz
  - Uralsk
  - Ust Kamenogorsk
  - Kurchatov
  - Ridder

Notes:

- `city_status_registry_v2.csv` shows all 10 cities with official totals and calibrated inference support.
- Only the four V3 inference cities have the frozen uncertainty outputs required for full reliability-mode explanations.
- Kurchatov and Ridder are registry-supported but do not have generated features in the registry file, so they should be treated carefully in V4 summaries.

## Artifact groups

| Artifact group | Path | Expected files | What it contains | Later local tool | Mode support | Claim boundary |
|---|---|---|---|---|---|---|
| V3 uncertainty outputs | `outputs/v3_uncertainty/<run_id>/` | `city_uncertainty_summary.csv`, city CSV/GeoJSON files, `run_manifest.json` | City-level uncertainty outputs and per-cell outputs for the frozen v3 run | `get_city_summary`, `get_confidence_summary`, `get_uncertainty_summary`, `get_cell_evidence` | Full V3 for Almaty, Astana, Semey, Shymkent | Proxy uncertainty summaries only; not truth |
| Paper-facing V3 uncertainty evidence | `reports/paper_v3_uncertainty/<run_id>/` | `README.md`, `paper_summary.md`, `freeze_manifest.json`, figures, tables, limitation notes, source indexes | Frozen evidence package for the V3 paper | `get_method_summary`, `get_claim_boundaries`, report generator | Full V3 plus explainability | Paper evidence package, not a model |
| Hotspot prioritization reports | `reports/hotspot_prioritization_v3/<run_id>/` | `hotspot_city_summary.csv`, `top_hotspots_by_city.csv`, `stable_hotspots.csv`, `caution_hotspots.csv`, `PHASE_5_HOTSPOT_PRIORITIZATION_REPORT.md` | Hotspot classes and prioritization summaries | `get_hotspot_summary`, `generate_evidence_pack` | Full V3 | Screening and triage only |
| Uncertainty validation reports | `reports/uncertainty_validation_v3/<run_id>/` | `confidence_band_validation_summary.csv`, `hotspot_stability_summary.csv`, `interval_coverage_weak_target.csv`, `uncertainty_monotonicity.csv`, `error_uncertainty_alignment.csv`, `PHASE_6_UNCERTAINTY_VALIDATION_REPORT.md` | Reliability evidence, interval behavior, stability, and claim-limit context | `get_confidence_summary`, `get_uncertainty_summary`, `generate_evidence_pack` | Full V3 | Reliability interpretation only |
| District interval coverage reports | `reports/district_interval_coverage_v3/<run_id>/` | district summary artifacts if present | District-level interval evidence and limitations | `compare_cities`, `get_city_summary` | Usually limited/basic support unless district files are present | Partial administrative support only |
| External disagreement alignment reports | `reports/external_disagreement_alignment_v3/<run_id>/` | external comparison summary artifacts if present | WorldPop/GHS-POP disagreement context | `compare_cities`, `get_method_summary` | Usually limited/basic support unless report files are present | Structural comparators only |
| Unified manuscript package | `manuscript_package_city1_unified/` | `main.tex`, `supplement.tex`, `sections/`, `tables_tex/`, `figures/`, `supplement/`, `merge_traceability/` | Frozen manuscript sources, supplement, and traceability records | `get_method_summary`, `get_claim_boundaries` | Both V2 and V3 explanation layers | Scientific text only, no live model |
| City totals reference data | `data/external/city_population_reference_v2.csv` | one CSV | Official city totals and reference dates | `get_city_summary`, `get_available_cities`, `compare_cities` | All supported cities | Calibration anchor only |
| City status registry | `data/external/city_status_registry_v2.csv` | one CSV | Registry of city support, feature generation, and calibrated inference eligibility | `get_available_cities`, `get_city_summary` | All supported cities | Support metadata only |

## What V4 can explain from this inventory

- city coverage and support status;
- deterministic proxy-surface behavior;
- uncertainty summaries for the frozen v3 cities;
- hotspot screening and confidence-band separation;
- claim boundaries and limitation notes;
- city comparisons using frozen evidence only.

## What V4 cannot explain from this inventory

- new population estimates;
- new uncertainty estimates;
- truth reconstruction;
- untracked cities outside the frozen registry;
- evidence that does not exist in the project artifacts.

