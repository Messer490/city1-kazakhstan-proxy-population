# Cleanup Audit v2

This file records the manuscript-focused cleanup decision for the maintained `City1 v2` repository.

## Keep list

The clean package keeps the maintained baseline system:

- `app_v2.py`
- `src/city1/`
- `scripts/`
- `tests/`
- `docs/`
- `requirements.txt`
- `requirements-optional.txt`
- `data/`
- `models/`
- `reports/`
- `README.md`

## Removed from the clean manuscript package

The following paths were intentionally removed after being archived elsewhere:

- legacy notebooks `A*.ipynb`
- `Simulated Telco Index.ipynb`
- `csv/`
- `GeoJson/`
- `legacy/`

The following local or regenerable junk was also removed:

- `.venv/`
- `cache/`
- `__pycache__/`
- `.ipynb_checkpoints/`
- `.sixth/`
- empty helper folders such as `app/`

## Rationale

The manuscript package is meant to keep only the frozen `v2` baseline, its reproducible workflows, and its final evaluation artifacts. Historical research materials were preserved in a separate archive before this cleanup and are no longer needed inside the active writing package.
