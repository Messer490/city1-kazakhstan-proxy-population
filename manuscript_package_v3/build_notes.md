# City1 v3 Build Notes

## Assembly summary

- package root: `manuscript_package_v3/`
- primary frozen evidence source: `reports/paper_v3_uncertainty/city1_v3_rf500m_e20_20260618T040646Z/`
- manuscript scope: Phase 8 only
- v2 manuscript modified: no
- new results generated: no
- retraining performed: no
- Phase 6 rerun performed: no

## Files copied into the manuscript package

- copied `reports/paper_v3_uncertainty/.../tables/*.csv` into `manuscript_package_v3/tables/`
- copied `reports/paper_v3_uncertainty/.../figures/*.png` into `manuscript_package_v3/figures/`
- copied `manuscript_package_v2/refs.bib` into `manuscript_package_v3/references.bib`

## LaTeX package structure created

- `main.tex`
- `supplement.tex`
- `sections/00_abstract.tex` through `sections/10_data_and_code_availability.tex`
- `tables_tex/` with manuscript-facing LaTeX tables
- `supplement/sections/` and `supplement/tables_tex/`

## Source interpretation rules followed

- manuscript claims were drafted from the frozen Phase 7 package and the explicitly required Phase 3-6 reports
- mixed evidence was preserved
- district partial status was preserved
- no true census-uncertainty language was introduced

## Unresolved placeholders

- author names and affiliations
- archival DOI

## PDF compilation

- attempted: no
- status: blocked in local shell
- notes: `pdflatex` and `bibtex` were not available in PATH in the current environment, so compilation should be completed in Overleaf or a TeX-enabled local setup.

## Structural checks completed

- required Phase 7 paper-facing tables were present and copied
- required Phase 7 paper-facing figures were present and copied
- all manuscript section files were created
- all supplementary tables were created
- citation keys were checked against `references.bib`
- `\ref{}` targets were checked against defined `\label{}` entries
