# Unified City1 Framework Build Notes

## Scope

- package root: `manuscript_package_city1_unified/`
- task type: scientific manuscript integration
- existing source packages overwritten: no
- source packages deleted: no
- v2 manuscript modified by this phase: no
- v3 manuscript modified by this phase: no
- retraining performed: no
- new scientific results generated: no
- uncertainty validation rerun: no

## Source materials used

- `manuscript_package_v2/main.tex`
- `manuscript_package_v2/supplement.tex`
- `manuscript_package_v2/sections/*.tex`
- `manuscript_package_v2/tables_tex/*.tex`
- `manuscript_package_v2/tables/*.csv`
- `manuscript_package_v2/figures/*`
- `manuscript_package_v2/README.md`
- `manuscript_package_v3/main.tex`
- `manuscript_package_v3/supplement.tex`
- `manuscript_package_v3/sections/*.tex`
- `manuscript_package_v3/tables_tex/*.tex`
- `manuscript_package_v3/tables/*.csv`
- `manuscript_package_v3/figures/*`
- `reports/paper_v3_uncertainty/city1_v3_rf500m_e20_20260618T040646Z/*`
- `reports/hotspot_prioritization_v3/city1_v3_rf500m_e20_20260618T040646Z/PHASE_5_HOTSPOT_PRIORITIZATION_REPORT.md`
- `reports/uncertainty_validation_v3/city1_v3_rf500m_e20_20260618T040646Z/PHASE_6_UNCERTAINTY_VALIDATION_REPORT.md`

## Assets copied into the unified package

- copied `manuscript_package_v2/refs.bib` to `references.bib`
- copied deterministic figures into `figures/`
- copied uncertainty figures into `figures/`
- copied deterministic and uncertainty CSV tables into `tables/`

## New manuscript-facing files created

- `main.tex`
- `supplement.tex`
- all section `.tex` files under `sections/`
- unified table wrappers under `tables_tex/`
- unified supplement sections under `supplement/sections/`
- unified supplement tables under `supplement/tables_tex/`
- merged traceability CSV files under `merge_traceability/`
- `README.md`
- `build_notes.md`
- `manuscript_checklist.md`

## Integration decisions

- deterministic and uncertainty manuscripts were merged as Stage 1 and Stage 2 of one City1 framework
- `v2`, `v3`, and `v4` labels were minimized in the manuscript body
- the unified framework diagram merges the deterministic pipeline schematic and the uncertainty evidence-flow figure
- deterministic core results were retained in the main paper
- uncertainty city coverage, hotspot, and validation results were retained in the main paper
- technical appendices and expanded evidence matrices were moved to the supplement
- repeated wording was consolidated, but unique scientific content was preserved or explicitly logged

## Claim-boundary rules preserved

- no true cell-level census reconstruction claim
- no true census-uncertainty claim
- no confidence-score-as-probability claim
- no external-products-as-ground-truth claim
- no district-evidence-as-cell-truth claim
- future LLM layer included only as future work

## PDF compilation

- attempted: no
- status: blocked in local shell
- blocker: `pdflatex` and `bibtex` are not available in PATH in the current environment
- next step: compile in Overleaf or a TeX-enabled local setup

## Structural QA checks completed

- all required main-manuscript section files exist
- all required supplement section files exist
- all `\input{}` targets resolve from the unified package root
- all `\includegraphics{}` targets resolve from the unified package root
- no missing `\ref{}` labels were detected
- no missing bibliography keys were detected against `references.bib`
- no forbidden claim phrases were detected in unified `.tex` sources
- contribution map and all required traceability CSV files exist

## Remaining work before final polishing

- add author names and affiliations
- replace archival DOI sentence if repository deposit DOI is assigned
- run one Overleaf compile
- inspect float placement and table width visually
- perform one final line-level style pass after compile
