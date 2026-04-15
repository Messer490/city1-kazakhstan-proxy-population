# Figure and Table Plan for the Main Paper

This file fixes the recommended split between `main paper` and `supplement` so the manuscript stays strong without becoming visually overloaded.

## Honest editorial verdict

The current figure stack is scientifically strong enough to support the paper.

It is **not weak**, but it is still too broad to place every available asset in the main paper. The right move is not to add random screenshots or decorative images. The right move is to keep the figures that directly support the central claim and move supporting detail to the supplement.

## What should NOT go into the main paper

- Streamlit screenshots
- raw app outputs as UI captures
- QA dashboard screenshots
- every city map we have

Reason:
- the paper is about a reproducible calibrated proxy population baseline
- it is not a software demo paper
- UI screenshots dilute scientific tone unless the paper is specifically about the interface

If a Streamlit panel explains something useful, it should be reformatted into a paper-style figure or table, not inserted as a UI screenshot.

## Recommended main-paper figures

### Figure 1. Pipeline schematic
- `figures/figure_pipeline_schematic.tex`

Why it stays:
- the paper needs one clear conceptual overview
- this replaces the temptation to use screenshots or ad hoc workflow diagrams

### Figure 2. Baseline selection composite
- `figures/figure_model_comparison.png`
- `figures/figure_grid_size_benchmark.png`

Why it stays:
- this figure justifies the frozen production identity
- it answers why `random_forest` and why `500 m`

### Figure 3. Internal and data-quality composite
- `figures/figure_district_benchmark.png`
- `figures/figure_osm_completeness.png`

Why it stays:
- it shows both the partial internal administrative support and the input-reliability context
- it helps the reader understand why the evidence is useful but bounded

### Figure 4. External benchmark composite
- `figures/figure_external_benchmark_pearson.png`
- `figures/figure_external_benchmark_hotspot_iou.png`

Why it stays:
- external validation is one of the strongest parts of the paper
- this figure supports the claim that different independent products confirm different aspects of the surface

### Figure 5. Ablation
- `figures/figure_ablation_loco.png`

Why it stays:
- the ablation story is one of the strongest scientific contributions
- it shows that built form is dominant, while the full model still performs best

### Figure 6. Qualitative overview
- `figures/figure_qualitative_overview_almaty.png`
- `figures/figure_qualitative_overview_astana.png`

Why it stays:
- qualitative validation belongs in the main paper
- overview maps are cleaner and more readable in the body than detailed case panels

## Recommended supplement figures

### Supplement Figure S1. Qualitative cases
- `figures/figure_qualitative_cases_almaty.png`
- `figures/figure_qualitative_cases_astana.png`

Why it moves:
- it is valuable evidence
- but it is more detailed than the main narrative needs on first read
- it works better as supporting detail after the overview figure

### Supplement Figure S2. Example surfaces
- `figures/figure_surface_almaty.png`
- `figures/figure_surface_semey.png`

Why it moves:
- useful for readers who want extra visual examples
- not essential for the main argument once qualitative overview is already included

### Supplement Figure S3. Operational visuals if needed
- `figures/figure_city_status.png`
- `figures/figure_qa_warnings.png`

Why they move:
- useful for reproducibility appendix or supplement
- too operational for the main scientific narrative

## Recommended main-paper tables

### Table 1. Study coverage summary
- derived from:
  - `tables/city_status_table.csv`
  - `tables/osm_completeness_table.csv`

### Table 2. Core model and grid validation summary
- derived from:
  - `tables/model_validation_table.csv`
  - `tables/grid_size_summary_table.csv`

### Table 3. District benchmark summary
- source:
  - `tables/district_benchmark_metrics_table.csv`

### Table 4. External benchmark summary
- source:
  - `tables/external_benchmark_summary_table.csv`

### Table 5. Ablation summary
- source:
  - `tables/ablation_summary_table.csv`

## Recommended supplement tables

- validation-evidence matrix
- frozen city registry and coverage
- frozen feature inventory by family
- weak-label weights
- `tables/qa_city_summary_table.csv`
- `tables/grid_size_city_recommendations_table.csv`
- `tables/external_benchmark_metrics_table.csv`
- `tables/ablation_selected_extras_table.csv`
- `tables/qualitative_validation_case_table.csv`

## Final recommendation

For the main paper, keep **6 figures** and **5 tables**.

That is strong enough to look serious and complete, but still compact enough to avoid visual overload.

If we try to push every asset into the main paper, the manuscript will feel less focused, not more impressive.
