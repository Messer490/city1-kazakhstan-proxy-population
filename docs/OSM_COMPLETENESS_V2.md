# OSM Completeness Score v2

City1 v2 now includes an explicit `OSM completeness score`.

## Why it exists

The model can technically run even when some OSM layers are sparse or partially missing.

That is useful for engineering robustness, but scientifically it must be visible.

The completeness score gives a compact signal about how strong the OSM-derived feature coverage looks for a city.

## What it uses

The score combines:

- critical coverage:
  - buildings
  - roads
  - POI accessibility
- optional coverage:
  - bus stops
  - parks
  - schools
  - hospitals
  - retail/shop proxy
- feature density:
  - building area
  - road length
  - total floor area
- warning penalty:
  - OSM extraction warnings
  - QA warnings

## Labels

- `excellent` >= 85
- `good` >= 70
- `moderate` >= 55
- `weak` < 55

## Batch report

```powershell
.\.venv\Scripts\python.exe scripts\build_osm_completeness_report_v2.py --features-dir data/processed/features_v2_batch1 --output-dir reports/osm_completeness_v2
```

Outputs:

- `osm_completeness_summary.csv`
- `osm_completeness_scores.png`
- `osm_completeness_report.md`
