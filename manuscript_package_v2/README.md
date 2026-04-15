# City1 v2 Manuscript Package

This folder is a clean manuscript-oriented bundle built from the frozen `City1 v2` package.

## What is already here

For the article, we already have almost all critical figures and source tables:

- model comparison
- grid-size benchmark
- OSM completeness
- district benchmark
- external benchmark
- ablation
- qualitative validation
- supplementary surface maps

The only genuinely new main-paper figure that was still missing as a standalone asset was a conceptual pipeline schematic. That figure is included here as LaTeX/TikZ code:

- `figures/figure_pipeline_schematic.tex`

This is better than generating an AI image, because for a scientific paper we usually need a clear schematic, not a decorative illustration.

## Folder structure

- `main.tex`
  - Overleaf-ready manuscript skeleton
- `supplement.tex`
  - supplement manuscript for evidence synthesis, technical appendices, detailed qualitative panels, and extra supporting material
- `figures/`
  - all copied paper-package figure assets
  - LaTeX/TikZ pipeline schematic
- `tables/`
  - copied CSV tables from `reports/paper_v2_baseline/tables`
- `sections/`
  - section skeletons for the manuscript
- `source_text/`
  - manuscript-critical source markdown and freeze docs

## Main-paper figure plan

- Figure 1:
  - `figures/figure_pipeline_schematic.tex`
- Figure 2:
  - `figures/figure_model_comparison.png`
  - `figures/figure_grid_size_benchmark.png`
- Figure 3:
  - `figures/figure_district_benchmark.png`
  - `figures/figure_osm_completeness.png`
- Figure 4:
  - `figures/figure_external_benchmark_pearson.png`
  - `figures/figure_external_benchmark_hotspot_iou.png`
- Figure 5:
  - `figures/figure_ablation_loco.png`
- Figure 6:
  - `figures/figure_qualitative_overview_almaty.png`
  - `figures/figure_qualitative_overview_astana.png`

## Supplement figure plan

- Supplement Figure S1:
  - `figures/figure_qualitative_cases_almaty.png`
  - `figures/figure_qualitative_cases_astana.png`
- Supplement Figure S2:
  - `figures/figure_surface_almaty.png`
  - `figures/figure_surface_semey.png`
- Supplement Figure S3:
  - `figures/figure_city_status.png`
  - `figures/figure_qa_warnings.png`

## Supplement technical tables and appendices

- Supplementary Table S1:
  - validation-evidence matrix
- Supplementary Table S2:
  - frozen city registry and coverage
- Supplementary Table S3:
  - frozen feature inventory by family
- Supplementary Table S4:
  - weak-label weights
- Supplementary Section S4:
  - calibration rule and uniform fallback behavior

## Important source files for writing

- `source_text/city1_v2_zero_draft_ru.md`
- `source_text/city1_v2_manuscript_en.md`
- `source_text/MANUSCRIPT_MAP_V2.md`
- `source_text/paper_report_summary.md`
- `source_text/FINAL_STATUS_V2.md`
- `source_text/PAPER_POSITIONING_V2.md`
- `source_text/V2_BASELINE_SCOPE.md`

## What is still needed later

The package is now strong enough for the final manuscript pass, but a few paper-finishing items still belong to the next stage:

- target journal template
- author list and affiliations
- final table formatting for the target venue
- final compile and layout pass in Overleaf
- final line-by-line alignment against the frozen numbers

The bibliography metadata in `refs.bib` has already been cleaned for the currently cited sources. What remains is venue-specific polish after the first successful compile.

The package also now includes a `V3_DIFFERENTIATION_ROADMAP.md` note that records intentionally excluded next-step items such as uncertainty layers, richer explainability, and downstream use cases, so they do not drift back into the frozen `v2` manuscript.

Venue-specific author and submission metadata are tracked separately in `SUBMISSION_METADATA_CHECKLIST.md` so that the scientific package can remain frozen while journal-facing fields are completed later.

## Bottom line

Yes, we already have the critical figure set needed to write the paper.

No, we do not currently need AI-generated "photos" to make the paper credible.

What we do need is:

- disciplined figure selection
- strong captions
- a clean LaTeX manuscript structure
- careful alignment of text to the frozen evidence package
- a successful Overleaf compile and visual pass
