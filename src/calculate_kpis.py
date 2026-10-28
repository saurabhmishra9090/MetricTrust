
import duckdb
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DATA_FILE = ROOT / "data" / "raw" / "nyc_311_monthly_sample.csv"
DB_FILE = ROOT / "data" / "metrictrust.duckdb"

if not DATA_FILE.exists():
    raise FileNotFoundError(f"Dataset not found: {DATA_FILE}")

df = pd.read_csv(DATA_FILE)

df["created_date"] = pd.to_datetime(
    df["created_date"], errors="coerce"
)
df["closed_date"] = pd.to_datetime(
    df["closed_date"], errors="coerce"
)

df["status_normalized"] = (
    df["status"].astype("string").str.strip().str.lower()
)

df["month"] = df["created_date"].dt.to_period("M").astype("string")

df = df.dropna(subset=["created_date", "unique_key"])

# KPI 1: distinct request IDs per creation month.
# KPI 2: closed-status requests / all requests in the month.
monthly = (
    df.groupby("month")
    .agg(
        total_requests=("unique_key", "nunique"),
        closed_requests=("status_normalized", lambda s: (s == "closed").sum()),
        missing_closed_dates=("closed_date", lambda s: s.isna().sum()),
    )
    .reset_index()
)

monthly["closure_rate_pct"] = (
    monthly["closed_requests"] / monthly["total_requests"] * 100
).round(2)

# MT-001: Closed status but no closure date.
violations = df[
    (df["status_normalized"] == "closed")
    & (df["closed_date"].isna())
].copy()


con = duckdb.connect(str(DB_FILE))

try:
    con.register("monthly_df", monthly)
    con.register("violations_df", violations)

    con.execute("""
        CREATE TABLE IF NOT EXISTS monthly_kpi_results (
            month VARCHAR,
            total_requests BIGINT,
            closed_requests BIGINT,
            missing_closed_dates BIGINT,
            closure_rate_pct DOUBLE
        )
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS reconciliation_violations (
            unique_key VARCHAR,
            created_date TIMESTAMP,
            agency VARCHAR,
            status VARCHAR,
            rule_id VARCHAR
        )
    """)

    # Replace prior results so rerunning the script does not append duplicates.
    con.execute("DELETE FROM monthly_kpi_results")
    con.execute("DELETE FROM reconciliation_violations")

    con.execute("""
        INSERT INTO monthly_kpi_results
        SELECT month, total_requests, closed_requests,
               missing_closed_dates, closure_rate_pct
        FROM monthly_df
    """)

    con.execute("""
        INSERT INTO reconciliation_violations
        SELECT CAST(unique_key AS VARCHAR),
               CAST(created_date AS TIMESTAMP),
               CAST(agency AS VARCHAR),
               CAST(status AS VARCHAR),
               'MT-001'
        FROM violations_df
    """)

    print("===== MONTHLY KPI RESULTS (SAMPLE) =====")
    print(con.execute("""
        SELECT *
        FROM monthly_kpi_results
        ORDER BY month
        LIMIT 12
    """).df().to_string(index=False))

    print("\n===== MT-001 RECONCILIATION =====")
    print("Violation count:", con.execute(
        "SELECT COUNT(*) FROM reconciliation_violations"
    ).fetchone()[0])

    print("\n===== OVERALL SAMPLE SUMMARY =====")
    print(con.execute("""
        SELECT
            SUM(total_requests) AS monthly_request_count_sum,
            SUM(closed_requests) AS monthly_closed_count_sum,
            ROUND(
                SUM(closed_requests) * 100.0
                / NULLIF(SUM(total_requests), 0), 2
            ) AS weighted_closure_rate_pct
        FROM monthly_kpi_results
    """).df().to_string(index=False))

finally:
    con.close()

print(f"\nResults saved in: {DB_FILE}")
print("Note: These are capped-sample KPIs, not NYC population totals.")
