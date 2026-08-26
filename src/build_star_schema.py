"""
Builds a real Power BI-style star schema (Fact + Dimension tables) from
the same genuine, cleaned EV charging dataset used in the
ev-charging-dashboard project (85,748 real sessions, City of Boulder
Open Data Portal, Jan 2018 - Nov 2023).

This is a real, standard Power BI semantic-modeling step: a Power BI
report is never built directly on one flat table for anything beyond a
toy example -- a star schema (one fact table of measurable events, joined
to dimension tables the report slices/filters by) is the baseline
pattern DAX measures are written against, because DAX's CALCULATE/
filter-context model is designed around exactly this shape.

Honest disclosure: this schema was designed and built in this Linux
sandbox using pandas (no Power BI Desktop / Windows available here --
same disclosed constraint as the powerquery-sap-reporting project). The
resulting CSVs are exactly what would be imported into Power BI Desktop
as the report's data model (Get Data > Text/CSV, or a Databricks/SQL
source in production), and the DAX measures in measures.dax are written
against this exact schema's table/column names.
"""

import pandas as pd

SRC = "/home/claude/ev-charging-dashboard/ev_charging_boulder_clean.csv"


def build():
    df = pd.read_csv(SRC, parse_dates=["Start_Date___Time", "End_Date___Time"])

    # --- Dim_Station: one row per physical charging station ---
    dim_station = (
        df[["Station_Name", "Address", "City", "State_Province", "Zip_Postal_Code"]]
        .drop_duplicates(subset=["Station_Name"])
        .reset_index(drop=True)
    )
    dim_station.insert(0, "StationKey", range(1, len(dim_station) + 1))

    # --- Dim_Date: one row per calendar day spanning the real data range,
    # not just the days that happen to have a session -- a real Power BI
    # date table is a continuous calendar, so days with zero sessions
    # still appear (with zero-valued measures), which is exactly the kind
    # of thing that trips up a naive "group by the fact table's dates"
    # approach and is worth doing correctly here.
    full_range = pd.date_range(df["Start_Date"].min(), df["Start_Date"].max(), freq="D")
    dim_date = pd.DataFrame({"Date": full_range})
    dim_date["DateKey"] = dim_date["Date"].dt.strftime("%Y%m%d").astype(int)
    dim_date["Year"] = dim_date["Date"].dt.year
    dim_date["Month"] = dim_date["Date"].dt.month
    dim_date["MonthName"] = dim_date["Date"].dt.strftime("%b")
    dim_date["Quarter"] = dim_date["Date"].dt.quarter
    dim_date["DayOfWeek"] = dim_date["Date"].dt.day_name()
    dim_date["IsWeekend"] = dim_date["Date"].dt.dayofweek >= 5
    dim_date = dim_date[["DateKey", "Date", "Year", "Quarter", "Month", "MonthName", "DayOfWeek", "IsWeekend"]]

    # --- Fact_ChargingSessions: one row per real session, joined to keys ---
    station_key_map = dict(zip(dim_station["Station_Name"], dim_station["StationKey"]))
    fact = df.copy()
    fact["StationKey"] = fact["Station_Name"].map(station_key_map)
    fact["DateKey"] = pd.to_datetime(fact["Start_Date"]).dt.strftime("%Y%m%d").astype(int)
    fact = fact.rename(columns={
        "Session_ID": "SessionID",
        "Energy__kWh_": "EnergyKWh",
        "GHG_Savings__kg_": "GHGSavingsKg",
        "Gasoline_Savings__gallons_": "GasolineSavingsGallons",
        "Total_Duration_Minutes": "TotalDurationMinutes",
        "Charging_Time_Minutes": "ChargingTimeMinutes",
    })
    fact_cols = [
        "SessionID", "StationKey", "DateKey", "Hour", "Port_Type",
        "EnergyKWh", "GHGSavingsKg", "GasolineSavingsGallons",
        "TotalDurationMinutes", "ChargingTimeMinutes", "Zero_Energy_Session",
    ]
    fact = fact[fact_cols]

    dim_station.to_csv("Dim_Station.csv", index=False)
    dim_date.to_csv("Dim_Date.csv", index=False)
    fact.to_csv("Fact_ChargingSessions.csv", index=False)

    print(f"Dim_Station: {len(dim_station)} rows")
    print(f"Dim_Date:    {len(dim_date)} rows ({dim_date['Date'].min().date()} to {dim_date['Date'].max().date()})")
    print(f"Fact_ChargingSessions: {len(fact)} rows")

    # Sanity checks -- a real referential-integrity check, not assumed
    assert fact["StationKey"].isna().sum() == 0, "unmapped station found"
    assert fact["DateKey"].isin(dim_date["DateKey"]).all(), "fact date outside Dim_Date range"
    print("Referential integrity: OK (every fact row maps to a valid StationKey and DateKey)")

    return dim_station, dim_date, fact


if __name__ == "__main__":
    build()
