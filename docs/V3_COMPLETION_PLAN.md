# City1 v3 Completion Plan

## Objective

Complete `City1 v3` as an **uncertainty-aware extension of City1 v2** without redesigning the v2 science.

`v2` builds the calibrated proxy population surface.  
`v3` adds bounded reliability information around that surface.

## Phase Status

- Phase 1: **completed** - audit and repo status check
- Phase 2: **completed** - data contract and directory conventions frozen
- Phase 3: **completed** - v3 uncertainty ensemble trained
- Phase 4: **completed** - v3 uncertainty inference generated for Almaty, Astana, Semey, and Shymkent
- Phase 5: **completed** - hotspot prioritization evidence package generated
- Phase 6: **partially completed** - uncertainty validation evidence stack with explicit district limitation
- Phase 7: **completed with carried limitations** - paper-facing package frozen under `reports/paper_v3_uncertainty/city1_v3_rf500m_e20_20260618T040646Z`
- Phase 8: **not started** - manuscript package

## Paper-facing package path

- `reports/paper_v3_uncertainty/city1_v3_rf500m_e20_20260618T040646Z`

## Key tables

- `reports/paper_v3_uncertainty/city1_v3_rf500m_e20_20260618T040646Z/tables/table1_v3_city_coverage.csv`
- `reports/paper_v3_uncertainty/city1_v3_rf500m_e20_20260618T040646Z/tables/table2_uncertainty_interval_coverage.csv`
- `reports/paper_v3_uncertainty/city1_v3_rf500m_e20_20260618T040646Z/tables/table3_error_uncertainty_alignment.csv`
- `reports/paper_v3_uncertainty/city1_v3_rf500m_e20_20260618T040646Z/tables/table4_hotspot_prioritization_summary.csv`
- `reports/paper_v3_uncertainty/city1_v3_rf500m_e20_20260618T040646Z/tables/table5_confidence_band_summary.csv`
- `reports/paper_v3_uncertainty/city1_v3_rf500m_e20_20260618T040646Z/tables/table6_district_external_limitations_summary.csv`
- `reports/paper_v3_uncertainty/city1_v3_rf500m_e20_20260618T040646Z/tables/table7_hotspot_stability_summary.csv`

## Key figures

- `reports/paper_v3_uncertainty/city1_v3_rf500m_e20_20260618T040646Z/figures/fig1_v3_pipeline.png`
- `reports/paper_v3_uncertainty/city1_v3_rf500m_e20_20260618T040646Z/figures/fig2_uncertainty_output_example.png`
- `reports/paper_v3_uncertainty/city1_v3_rf500m_e20_20260618T040646Z/figures/fig3_confidence_band_distribution.png`
- `reports/paper_v3_uncertainty/city1_v3_rf500m_e20_20260618T040646Z/figures/fig4_hotspot_prioritization_by_city.png`
- `reports/paper_v3_uncertainty/city1_v3_rf500m_e20_20260618T040646Z/figures/fig5_uncertainty_validation_summary.png`
- `reports/paper_v3_uncertainty/city1_v3_rf500m_e20_20260618T040646Z/figures/fig6_hotspot_stability_summary.png`

## Phase 8 start condition

Phase 8 can start if the manuscript preserves the following:

- v3 is framed as an uncertainty-aware screening and interpretation layer
- hotspot stability and uncertainty burden separation are presented as the strongest support
- interval coverage and external disagreement are described as mixed
- district interval coverage is described as partial rather than solved

## Unresolved limitations that must carry into the manuscript

- v3 does not estimate true census uncertainty
- confidence_score is not a truth probability
- district interval coverage remains partial unless frozen district polygon/cell assignment artifacts are added
- external products are structural benchmarks, not ground truth
- the held-out LOCO-like Phase 6 evidence was produced in a bounded local configuration
