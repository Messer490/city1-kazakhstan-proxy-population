# Project Structure v2

This document defines the clean manuscript-focused structure of the maintained `City1 v2` repository after legacy materials were archived externally.

## Production Core

These paths are part of the active maintained system:

- `src/city1/`
  - feature generation
  - CRS handling
  - OSM extraction
  - QA
  - training
  - inference
  - validation
- `scripts/`
  - reproducible CLI workflows
- `tests/`
  - regression protection for the maintained core
- `docs/`
  - maintained documentation and paper-facing positioning
- `data/external/`
  - official references and cached official tables
- `data/processed/`
  - v2-generated artifacts
- `models/`
  - trained model and ablation artifacts
- `reports/`
  - QA, benchmark, validation, ablation, qualitative, and paper outputs
- `app_v2.py`
  - maintained Streamlit interface

## Legacy note

Legacy notebooks, old research folders, and archive-heavy root materials are no longer part of this clean manuscript package. They were archived externally before the current cleanup so the maintained repository can stay focused on the frozen `v2` baseline.

## Working rule

When adding or changing maintained production logic:

- edit `src/city1/`
- expose workflows through `scripts/`
- document them in `docs/`
- test them in `tests/`

Do not rebuild the project around legacy notebooks or retired archive folders.
