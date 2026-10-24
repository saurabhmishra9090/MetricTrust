
import duckdb
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_FILE = ROOT / "data" / "metrictrust.duckdb"

# Initial investigation thresholds; these are configurable,
# not official business-approved thresholds.
CLOSURE_RATE_THRESHOLD_PP = 0.5
MISSING_DATE_RATE_THRESHOLD_PP = 0.5

con = duckdb.connect(str(DB_FILE))

try:
    df = con.execute("""
        SELECT
            month,
            total_requests,
            closed_requests,
            closure_rate_pct,
            missing_closed_dates
        FROM monthly_kpi_results
        ORDER BY month
    """).df()

    if df.empty:
        raise RuntimeError(
            "No KPI results found. Run calculate_kpis.py first."
        )

    # Calculate missing closure-date percentage for each month.
    df["missing_closed_date_rate_pct"] = (
        df["missing_closed_dates"] / df["total_requests"] * 100
    )

    # Compare each month with the previous month.
    df["previous_closure_rate_pct"] = df["closure_rate_pct"].shift(1)
    df["closure_rate_change_pp"] = (
        df["closure_rate_pct"] - df["previous_closure_rate_pct"]
    )

    df["previous_missing_date_rate_pct"] = (
        df["missing_closed_date_rate_pct"].shift(1)
    )
    df["missing_date_rate_change_pp"] = (
        df["missing_closed_date_rate_pct"]
        - df["previous_missing_date_rate_pct"]
    )

    # Initial sample-level drift signals.
    df["performance_signal"] = (
        df["closure_rate_change_pp"].abs()
        >= CLOSURE_RATE_THRESHOLD_PP
    )

    df["data_quality_signal"] = (
        df["missing_date_rate_change_pp"].abs()
        >= MISSING_DATE_RATE_THRESHOLD_PP
    )

    # Read KPI definition versions from the registry.
    definition_versions = con.execute("""
        SELECT metric_id, COUNT(*) AS version_count
        FROM metric_registry
        GROUP BY metric_id
    """).df()

    print("===== METRICTRUST DRIFT DETECTION =====")
    print("\nKPI definition versions:")
    print(definition_versions.to_string(index=False))

    print("\nMonth-to-month sample signals:")
    display_columns = [
        "month",
        "closure_rate_pct",
        "closure_rate_change_pp",
        "performance_signal",
        "missing_closed_date_rate_pct",
        "missing_date_rate_change_pp",
        "data_quality_signal",
    ]
    print(df[display_columns].round(3).to_string(index=False))

    # Save results for later dashboard use.
    con.execute("""
        CREATE TABLE IF NOT EXISTS drift_results (
            month VARCHAR,
            closure_rate_pct DOUBLE,
            closure_rate_change_pp DOUBLE,
            performance_signal BOOLEAN,
            missing_closed_date_rate_pct DOUBLE,
            missing_date_rate_change_pp DOUBLE,
            data_quality_signal BOOLEAN
        )
    """)

    con.execute("DELETE FROM drift_results")

    result_df = df[[
        "month",
        "closure_rate_pct",
        "closure_rate_change_pp",
        "performance_signal",
        "missing_closed_date_rate_pct",
        "missing_date_rate_change_pp",
        "data_quality_signal",
    ]]

    con.register("drift_df", result_df)

    con.execute("""
        INSERT INTO drift_results
        SELECT * FROM drift_df
    """)

    print("\n===== SIGNAL SUMMARY =====")
    print(
        "Month-to-month performance signals:",
        int(df["performance_signal"].sum())
    )
    print(
        "Month-to-month data-quality signals:",
        int(df["data_quality_signal"].sum())
    )
    print(
        "KPI IDs with multiple registered versions:",
        int((definition_versions["version_count"] > 1).sum())
    )

    print("\nResults saved to the drift_results table.")
    print(
        "Caution: These are sample-level signals, "
        "not confirmed citywide drift."
    )

finally:
    con.close()
