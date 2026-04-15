# District Source Catalog v2

This layer records the official `stat.gov.kz` district-population table names currently visible in the regional spreadsheet catalogs.

It is not a district benchmark by itself.

Its role is:

- make the official district-source path reproducible
- preserve the discovered option IDs for `Almaty`, `Astana`, and `Shymkent`
- support the next extraction pass when direct district values are pulled from the official tables

## Build Command

```powershell
.\.venv\Scripts\python.exe scripts\build_district_source_catalog_v2.py --output-csv data/external/district_population_table_catalog_v2.csv
```

## Output

- `data/external/district_population_table_catalog_v2.csv`

## Current Use

This catalog helps separate two things:

- `district benchmark already completed`
- `official district table path already confirmed`

Today that means:

- `Almaty` has a completed benchmark and a confirmed official table path
- `Astana` and `Shymkent` have a confirmed official table path, even though their district benchmark references are not fully materialized yet

## Why It Matters

Without this layer, the remaining gap for `Astana` and `Shymkent` looks vague.

With this layer, the remaining task becomes precise:

1. resolve the exact official district values from the confirmed table path
2. build the district reference CSV
3. run the benchmark
4. rebuild the status registry and the paper report
