
import duckdb
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DATA_FILE = ROOT / "data" / "raw" / "nyc_311_monthly_sample.csv"
DB_FILE = ROOT / "data" / "metrictrust.duckdb"
REPORT_FILE = ROOT / "reports" / "definition_impact.csv"

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

df = df.dropna(subset=["created_date", "unique_key"])
df["month"] = df["created_date"].dt.to_period("M").astype(str)

# Version 1: closed status defines a closed request.
# Version 2: non-null closure date defines a closed request.
impact = (
    df.groupby("month")
    .agg(
        total_requests=("unique_key", "nunique"),
        v1_closed_requests=(
            "status_normalized",
            lambda s: (s == "closed").sum()
        ),
        v2_closed_requests=(
            "closed_date",
            lambda s: s.notna().sum()
        )
    )
    .reset_index()
)

impact["v1_closure_rate_pct"] = (
    impact["v1_closed_requests"] / impact["total_requests"] * 100
).round(3)

impact["v2_closure_rate_pct"] = (
    impact["v2_closed_requests"] / impact["total_requests"] * 100
).round(3)

impact["definition_impact_pp"] = (
    impact["v2_closure_rate_pct"] - impact["v1_closure_rate_pct"]
).round(3)

impact["scenario_type"] = "SYNTHETIC DEFINITION COMPARISON"

# Save a reusable report.
REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
impact.to_csv(REPORT_FILE, index=False, encoding="utf-8-sig")

con = duckdb.connect(str(DB_FILE))

try:
    con.register("impact_df", impact)

    con.execute("""
        CREATE TABLE IF NOT EXISTS definition_impact_results (
            month VARCHAR,
            total_requests BIGINT,
            v1_closed_requests BIGINT,
            v2_closed_requests BIGINT,
            v1_closure_rate_pct DOUBLE,
            v2_closure_rate_pct DOUBLE,
            definition_impact_pp DOUBLE,
            scenario_type VARCHAR
        )
    """)

    con.execute("DELETE FROM definition_impact_results")

    con.execute("""
        INSERT INTO definition_impact_results
        SELECT
            month,
            total_requests,
            v1_closed_requests,
            v2_closed_requests,
            v1_closure_rate_pct,
            v2_closure_rate_pct,
            definition_impact_pp,
            scenario_type
        FROM impact_df
    """)

    print("===== DEFINITION IMPACT ANALYSIS =====")
    print(
        impact[
            [
                "month",
                "v1_closure_rate_pct",
                "v2_closure_rate_pct",
                "definition_impact_pp"
            ]
        ].head(12).to_string(index=False)
    )

    print("\n===== OVERALL SAMPLE COMPARISON =====")

    v1_total = int(impact["v1_closed_requests"].sum())
    v2_total = int(impact["v2_closed_requests"].sum())
    request_total = int(impact["total_requests"].sum())

    v1_rate = v1_total / request_total * 100
    v2_rate = v2_total / request_total * 100

    print(f"Monthly request-count sum: {request_total:,}")
    print(f"Version 1 closed-status requests: {v1_total:,}")
    print(f"Version 2 requests with closure date: {v2_total:,}")
    print(f"Version 1 closure rate: {v1_rate:.3f}%")
    print(f"Version 2 closure rate: {v2_rate:.3f}%")
    print(f"Definition impact: {v2_rate - v1_rate:.3f} percentage points")

finally:
    con.close()

print(f"\nCSV report saved to: {REPORT_FILE}")
print("Results saved to definition_impact_results.")
print("Synthetic comparison only; not an official NYC KPI change.")
