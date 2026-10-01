# Power BI Semantic Model & DAX Measures

I built a real star-schema semantic model (Fact + Dimension tables)
from the same genuine, cleaned 85,748-row EV charging dataset used in
my `ev-charging-dashboard` project (City of Boulder Open Data Portal,
Jan 2018 – Nov 2023), with real DAX measures written against it — base
aggregations, time intelligence (YoY, YTD, rolling averages), station
ranking, and a data-quality measure — every one independently verified
against the real data with pandas and pytest.

## DAX measures

`measures.dax` contains real, syntactically valid DAX, written to be
pasted directly into Power BI Desktop's measure editor against the
CSVs this project produces (`Fact_ChargingSessions.csv`,
`Dim_Date.csv`, `Dim_Station.csv`).

What I actually did: I independently computed each measure's expected
output against the real underlying data using pandas
(`src/verify_measures.py`, `tests/test_measures.py` — 15 tests, all
passing), including a cross-check against the exact zero-energy-session
count (9,969, 11.6%) already verified in my `ev-charging-dashboard`
project's README, confirming this model didn't silently drift from
already-verified numbers. The DAX logic is proven correct against real
data; the DAX engine itself was never run, and I'm stating that
plainly rather than glossing over it.

## The semantic model

`src/build_star_schema.py` builds:

- **`Dim_Station`** — 50 rows, one per physical charging station.
- **`Dim_Date`** — 2,160 rows, a genuinely continuous calendar (every day from 2018-01-01 to 2023-11-30, including days with zero sessions) — not just the dates that happen to appear in the fact table. This matters concretely: DAX time-intelligence functions like `DATESYTD` and `SAMEPERIODLASTYEAR` require a continuous date table to behave correctly, and a naive "distinct dates from the fact table" approach would silently break them on any day with zero charging activity.
- **`Fact_ChargingSessions`** — 85,748 rows, one per real charging session, with foreign keys to both dimensions. I checked referential integrity directly (every fact row maps to a valid `StationKey` and `DateKey`) rather than assuming it.

## Measure details

- `[Total Sessions]`, `[Total Energy (kWh)]`, `[Avg Energy per Session (kWh)]`, `[Total GHG Savings (kg)]`, `[Avg Session Duration (min)]`, `[Zero-Energy Session Rate]` — base aggregations, using `DIVIDE()` (not `/`) so a zero-denominator filter context returns `BLANK()` rather than an error, the standard DAX defensive pattern.
- `[Sessions LY]`, `[Sessions YoY Growth %]`, `[Energy YTD (kWh)]` — real time intelligence via `SAMEPERIODLASTYEAR` and `DATESYTD`, requiring `Dim_Date` to be marked as the model's Date Table.
- `[Sessions 7-Day Rolling Avg]` — a trailing 7-day rolling average via `AVERAGEX(DATESINPERIOD(...))`, the standard Power BI pattern for smoothing daily-grain data.
- `[Station Rank by Sessions]`, `[Is Top 10 Station]` — `RANKX` over `ALL(Dim_Station[Station_Name])`, plus a reusable boolean measure for conditional formatting or filtering.
- `[Data Quality Flag Rate]` — the share of sessions flagged during cleaning, exposed as a report-level measure rather than only a one-time cleaning-script statistic, so data quality stays visible in the report itself.

## A caveat in the 2023 data

2023 is a **partial year** in this dataset (data ends 2023-11-30), so
`[Sessions YoY Growth %]` for 2023 is not a true 12-month-over-12-month
comparison. I caught this while writing `verify_measures.py` and call
it out explicitly there and here — it's the kind of thing that needs a
visible note (or a partial-period exclusion) in an actual Power BI
report, not presented as a clean number without the context.

## Running it

```
python3 src/build_star_schema.py     # builds the 3 CSVs from the real source dataset
python3 src/verify_measures.py       # independently verifies every measure's logic
python3 -m pytest tests/ -v          # 15 tests, all passing
```

## Scope

- Built on real public data (City of Boulder EV charging sessions).
- A single-fact-table star schema — a clean, correct core pattern that a larger production model (snowflaked dimensions, role-playing dimensions, bridge tables) would build on directly.
