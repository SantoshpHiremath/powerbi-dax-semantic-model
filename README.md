# Power BI Semantic Model & DAX Measures

A star-schema semantic model (Fact + Dimension tables) built from the cleaned
85,748-row EV charging dataset used in my `ev-charging-dashboard` project
(City of Boulder Open Data Portal, Jan 2018 – Nov 2023), with DAX measures
written against it: base aggregations, time intelligence (YoY, YTD, rolling
averages), station ranking, and a data-quality measure. Every measure is
independently verified against the data with pandas and pytest.

## What it does

`measures.dax` contains syntactically valid DAX, written to be pasted directly
into Power BI Desktop's measure editor against the CSVs this project produces
(`Fact_ChargingSessions.csv`, `Dim_Date.csv`, `Dim_Station.csv`).

I computed each measure's expected output independently against the
underlying data using pandas (`src/verify_measures.py`,
`tests/test_measures.py` — 15 tests, all passing), including a cross-check
against the exact zero-energy-session count (9,969, 11.6%) already verified in
my `ev-charging-dashboard` project's README, confirming this model stays
consistent with the previously verified numbers.

## Data

The model is built on real public data (City of Boulder EV charging
sessions). The model is a single-fact-table star schema, a clean core pattern
that a larger model (snowflaked dimensions, role-playing dimensions, bridge
tables) would build on directly.

`src/build_star_schema.py` builds:

- **`Dim_Station`** — 50 rows, one per physical charging station.
- **`Dim_Date`** — 2,160 rows, a continuous calendar (every day from 2018-01-01 to 2023-11-30, including days with zero sessions), not just the dates that appear in the fact table. This matters because DAX time-intelligence functions like `DATESYTD` and `SAMEPERIODLASTYEAR` require a continuous date table to behave correctly on days with zero charging activity.
- **`Fact_ChargingSessions`** — 85,748 rows, one per charging session, with foreign keys to both dimensions. I checked referential integrity directly: every fact row maps to a valid `StationKey` and `DateKey`.

## Measure details

- `[Total Sessions]`, `[Total Energy (kWh)]`, `[Avg Energy per Session (kWh)]`, `[Total GHG Savings (kg)]`, `[Avg Session Duration (min)]`, `[Zero-Energy Session Rate]` — base aggregations, using `DIVIDE()` (not `/`) so a zero-denominator filter context returns `BLANK()` rather than an error, the standard DAX defensive pattern.
- `[Sessions LY]`, `[Sessions YoY Growth %]`, `[Energy YTD (kWh)]` — time intelligence via `SAMEPERIODLASTYEAR` and `DATESYTD`, requiring `Dim_Date` to be marked as the model's Date Table.
- `[Sessions 7-Day Rolling Avg]` — a trailing 7-day rolling average via `AVERAGEX(DATESINPERIOD(...))`, the standard Power BI pattern for smoothing daily-grain data.
- `[Station Rank by Sessions]`, `[Is Top 10 Station]` — `RANKX` over `ALL(Dim_Station[Station_Name])`, plus a reusable boolean measure for conditional formatting or filtering.
- `[Data Quality Flag Rate]` — the share of sessions flagged during cleaning, exposed as a report-level measure rather than only a one-time cleaning-script statistic, so data quality stays visible in the report itself.

## Tests

15 pytest tests, all passing, cover the star-schema build (continuous date
table, referential integrity, row counts) and the expected output of each
measure against values computed independently with pandas.

## Project structure

```
Dim_Date.csv, Dim_Station.csv, Fact_ChargingSessions.csv   # star schema
measures.dax                                               # DAX measures
src/build_star_schema.py
src/verify_measures.py
tests/test_measures.py
```

## Running it

```
python3 src/build_star_schema.py     # builds the 3 CSVs from the source dataset
python3 src/verify_measures.py       # independently verifies every measure's logic
python3 -m pytest tests/ -v          # 15 tests, all passing
```

## Notes

2023 is a **partial year** in this dataset (data ends 2023-11-30), so
`[Sessions YoY Growth %]` for 2023 is not a true 12-month-over-12-month
comparison. I flagged this in `verify_measures.py` and here; in a Power BI
report it calls for a visible note or a partial-period exclusion.

The measures are verified by independent pandas computation and are ready to
paste into Power BI Desktop's measure editor.

## Possible extensions

- Add a partial-period exclusion to `[Sessions YoY Growth %]`.
- Extend the model with additional dimensions (for example a port-type or
  operator dimension).
- Publish the model and measures in a Power BI report on top of the CSVs.
