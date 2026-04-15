# Overleaf Compile Checklist

This checklist is the first real compile pass for the frozen `City1 v2` manuscript package.

## Upload

1. Zip the contents of `manuscript_package_v2`.
2. Create a new Overleaf project with `Upload Project`.
3. Set `main.tex` as the main file.
4. After the main paper compiles, switch to `supplement.tex` and confirm the supplement also compiles cleanly.

## Compile checks

Confirm all of the following:

- `main.tex` compiles without missing-file errors.
- All `\cite{}` entries resolve.
- `refs.bib` renders without broken bibliography items.
- All figure paths under `figures/` resolve.
- All table inputs under `tables_tex/` resolve.
- `figure_pipeline_schematic.tex` renders correctly inside the figure environment.
- Supplementary Tables `S1--S4` render without table-overflow or missing-package errors.

## Main-paper content lock

Confirm the compiled manuscript still contains:

- Figures 1--6 only in the main paper
- Tables 1--5 only in the main paper
- no Streamlit or UI screenshots in the main paper
- no detailed qualitative case panels in the main paper by default
- the new `Interpretation and Practical Implications` subsection reads as part of `Results`, not as a pasted add-on

## Visual pass

Review the compiled PDF page by page and check:

- figures appear in a sensible order relative to the narrative
- captions are readable and not cut off
- tables fit the page and do not overwhelm the surrounding text
- there are no obvious overfull or underfull layout problems that damage readability
- no placeholder text from older drafts remains visible
- the `Data and Code Availability` block looks intentional rather than appended
- supplement technical appendices look curated rather than like a raw archive

## Terminology consistency

Check that the compiled text consistently uses:

- `City1 v2`
- `random forest`
- `ridge`
- `500 m`
- `WorldPop`
- `GHS-POP`
- `OpenStreetMap (OSM)` then `OSM`
- `leave-one-city-out (LOCO)` then `LOCO`
- `spatial block cross-validation` then `spatial block CV`

## After compile

If compile succeeds, the next pass should be:

1. final visual cleanup
2. author, affiliation, and venue metadata insertion
3. target journal template migration
4. final supplement polish
