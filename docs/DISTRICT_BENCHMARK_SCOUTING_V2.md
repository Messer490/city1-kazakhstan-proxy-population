# District Benchmark Scouting v2

This note records the first scouting pass for a free `district benchmark` layer for City1 v2.

## Goal

Find district-level public data that can be used to benchmark City1 v2 without paid data.

The strongest target is:

- district population

Useful secondary layers:

- district migration
- district housing completions
- district housing stock
- district labor indicators
- district investment indicators

## Main conclusion

For `City1 v2`, the best first benchmark cities are:

1. `Almaty`
2. `Astana`
3. `Shymkent`

Why these three:

- they are already important production cities in the current v2 story
- they have official city totals already in the v2 reference
- `stat.gov.kz` exposes district-level population-oriented table names for all three
- district-level auxiliary indicators are also available for at least parts of the urban system

## Source strategy

Primary source:

- `stat.gov.kz`

Fallback / support source:

- `data.egov.kz`

Current assessment:

- `stat.gov.kz` is strong enough to serve as the primary benchmark source
- `eGov` is not required for the first implementation pass
- `eGov` can still help later with auxiliary administrative reference layers

## Candidate 1: Almaty

Readiness: `A`

Why Almaty is the strongest first benchmark:

- Almaty is already a validated baseline city in City1 v2
- the Almaty regional statistics page publishes current city totals
- the Almaty spreadsheets catalog explicitly lists district population table names
- the Almaty dynamic tables also expose district-level migration and district-level construction / investment indicators

Evidence:

- Almaty regional page with current city totals and links to spreadsheets and dynamic tables:
  - https://stat.gov.kz/ru/region/almaty/
- Almaty spreadsheets catalog:
  - https://stat.gov.kz/ru/region/almaty/spreadsheets/
- Almaty dynamic demographic tables:
  - https://stat.gov.kz/ru/region/almaty/dynamic-tables/38/

District-relevant table names visible on the Almaty spreadsheets page:

- `Численность населения в разрезе районов`
- `Численность населения города Алматы в разрезе районов`
- `Численность населения города Алматы по полу в разрезе районов`

District-relevant dynamic tables visible on the Almaty city page:

- `Ввод в эксплуатацию жилых зданий (районы)`
- `Инвестиции в жилищное строительство по районам`
- `Инвестиции в основной капитал по районам`
- `Внешняя миграция населения (по районам)(по годам)`

Best use in v2:

- district population benchmark
- district migration cross-check
- district housing / investment auxiliary validation

## Candidate 2: Astana

Readiness: `A-`

Why Astana is a strong second benchmark:

- Astana is already a validated baseline city in City1 v2
- the Astana regional page publishes current city totals
- the Astana spreadsheets catalog explicitly lists district population table names
- the Astana catalog also shows district-level labor and industrial table names

Evidence:

- Astana regional page:
  - https://stat.gov.kz/ru/region/astana/
- Astana spreadsheets catalog:
  - https://stat.gov.kz/ru/region/astana/spreadsheets/
- Astana dynamic demographic tables:
  - https://stat.gov.kz/ru/region/astana/dynamic-tables/38/

District-relevant table names visible on the Astana spreadsheets page:

- `Об изменении численности населения в разрезе районов`
- `Об уточненной численности населения в разрезе районов`
- `Численность населения в разрезе районов`
- `Численность населения по полу в разрезе районов`
- `Численность населения по районам`
- `Основные индикаторы рынка труда в разрезе районов`

Best use in v2:

- district population benchmark
- district labor benchmark
- district industrial / construction auxiliary benchmark

## Candidate 3: Shymkent

Readiness: `B+`

Why Shymkent is still a good benchmark city:

- Shymkent is already a validated baseline city in City1 v2
- the Shymkent regional page publishes current city totals
- the Shymkent spreadsheets catalog explicitly lists district population table names
- the city page exposes at least some district-level housing indicators

Why Shymkent is slightly weaker than Almaty and Astana:

- in the current v2 batch Shymkent has lower OSM completeness than the strongest cities
- feature sparsity warnings are already known for some optional layers

Evidence:

- Shymkent regional page:
  - https://stat.gov.kz/ru/region/shymkent/
- Shymkent spreadsheets catalog:
  - https://stat.gov.kz/ru/region/shymkent/spreadsheets/
- Shymkent dynamic demographic tables:
  - https://stat.gov.kz/ru/region/shymkent/dynamic-tables/38/

District-relevant table names visible on the Shymkent spreadsheets page:

- `Об изменении численности населения г. Шымкент в разрезе районов`
- `Численность населения в разрезе районов`
- `Численность населения города Шымкент в разрезе районов`
- `Численность населения города Шымкент по полу в разрезе районов`
- `Численность населения города Шымкент по районам`

District-relevant indicator visible on the Shymkent city page:

- `Ввод в эксплуатацию жилых зданий по районам`

Best use in v2:

- district population benchmark
- district housing benchmark
- stress-test case for a city with weaker OSM completeness

## What is realistically usable for v2

Strongly usable now:

- district population tables from `stat.gov.kz` for Almaty, Astana, and Shymkent
- district auxiliary tables for housing, migration, labor, and investments where available

Likely available geometry source:

- OpenStreetMap administrative boundaries for intracity districts

This means the expected benchmark workflow is feasible:

1. build district polygons
2. spatially aggregate cell predictions to district level
3. compare predicted district shares or totals against official district tables

## Recommended first implementation order

1. `Almaty`
2. `Astana`
3. `Shymkent`

This order is recommended because it maximizes:

- current v2 relevance
- benchmark strength
- likelihood of clean official district tables

## Suggested benchmark protocol

For each city:

1. collect district polygons
2. collect district population table for the same or closest possible date
3. aggregate City1 v2 grid predictions to districts
4. compare:
   - district total
   - district share of city population
   - district rank order
5. report:
   - MAE
   - RMSE
   - MAPE if stable
   - Pearson / Spearman correlation

## Risks

- district boundaries in OSM may not perfectly match statistical district boundaries
- publication dates may not perfectly align
- some district tables may be cataloged but still need manual retrieval or cleaning
- for Shymkent, lower OSM completeness may depress benchmark quality

## Recommendation

The district benchmark should start with `Almaty` as the first production implementation.

Then:

- expand to `Astana`
- then expand to `Shymkent`

That will give City1 v2 the strongest district-level scientific upgrade without changing the core task definition.
