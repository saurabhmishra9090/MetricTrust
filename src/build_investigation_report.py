
import duckdb
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_FILE = ROOT / "data" / "metrictrust.duckdb"
REPORT_FILE = ROOT / "reports" / "investigation_report.csv"

con = duckdb.connect(str(DB_FILE), read_only=True)

events = []

try:
    # 1. Month-to-month KPI and data-quality signals
    monthly = con.execute("""
        SELECT *
        FROM drift_results
        ORDER BY month
    """).df()
    monthly["previous_closure_rate_pct"] = monthly["closure_rate_pct"].shift(1)
    monthly["previous_missing_date_rate_pct"] = monthly["missing_closed_date_rate_pct"].shift(1)
        
    for _, row in monthly.iterrows():
        if bool(row["performance_signal"]):
            events.append({
                "event_type": "PERFORMANCE_SIGNAL",
                "month": row["month"],
                "metric_id": "CLOSURE_RATE",
                "severity": "REVIEW",
                "signal_name": "Monthly closure-rate change",
                "observed_value": row["closure_rate_pct"],
               "previous_value": row["previous_closure_rate_pct"],
                "change_pp": row["closure_rate_change_pp"],
                "details": (
                    "Month-to-month closure-rate change crossed "
                    "the configured threshold."
                ),
                "scenario_type": "CAPPED_SAMPLE"
            })

        if bool(row["data_quality_signal"]):
            events.append({
                "event_type": "DATA_QUALITY_SIGNAL",
                "month": row["month"],
                "metric_id": "CLOSURE_RATE",
                "severity": "REVIEW",
                "signal_name": "Missing closure-date rate change",
                "observed_value": row["missing_closed_date_rate_pct"],
                "previous_value": row["previous_missing_date_rate_pct"],
                "change_pp": row["missing_date_rate_change_pp"],
                "details": (
                    "Month-to-month missing closure-date rate "
                    "crossed the configured threshold."
                ),
                "scenario_type": "CAPPED_SAMPLE"
            })

    # 2. KPI definition changes
    definitions = con.execute("""
        SELECT *
        FROM definition_drift_results
        ORDER BY metric_id, current_version
    """).df()

    for _, row in definitions.iterrows():
        events.append({
            "event_type": "DEFINITION_DRIFT",
            "month": str(row["effective_from"])[:7],
            "metric_id": row["metric_id"],
            "severity": "REVIEW",
            "signal_name": (
                f"Formula changed: v{row['previous_version']} "
                f"to v{row['current_version']}"
            ),
            "observed_value": row["current_formula"],
            "previous_value": row["previous_formula"],
            "change_pp": None,
            "details": row["change_reason"],
            "scenario_type": row["change_type"]
        })

    # 3. Quantified impact of the synthetic definition change
    impact = con.execute("""
        SELECT
            SUM(v1_closed_requests) AS v1_closed,
            SUM(v2_closed_requests) AS v2_closed,
            SUM(total_requests) AS monthly_request_count_sum,
            SUM(v1_closed_requests) * 100.0
                / NULLIF(SUM(total_requests), 0) AS v1_rate,
            SUM(v2_closed_requests) * 100.0
                / NULLIF(SUM(total_requests), 0) AS v2_rate
        FROM definition_impact_results
    """).df().iloc[0]

    if pd.notna(impact["v1_rate"]) and pd.notna(impact["v2_rate"]):
        events.append({
            "event_type": "DEFINITION_IMPACT",
            "month": "ALL_SAMPLE_MONTHS",
            "metric_id": "CLOSURE_RATE",
            "severity": "INFORMATIONAL",
            "signal_name": "Synthetic formula impact",
            "observed_value": round(float(impact["v2_rate"]), 3),
            "previous_value": round(float(impact["v1_rate"]), 3),
            "change_pp": round(
                float(impact["v2_rate"] - impact["v1_rate"]), 3
            ),
            "details": (
                "Version 1 uses Closed status; version 2 uses "
                "non-null closed_date. Monthly cohorts may overlap "
                "in request IDs. This is a synthetic comparison."
            ),
            "scenario_type": "SYNTHETIC"
        })

    # 4. Reconciliation rule violations
    violations = con.execute("""
        SELECT
            CAST(created_date AS DATE) AS violation_date,
            rule_id,
            COUNT(*) AS violation_count
        FROM reconciliation_violations
        GROUP BY 1, 2
        ORDER BY 1, 2
    """).df()

    for _, row in violations.iterrows():
        events.append({
            "event_type": "RECONCILIATION_VIOLATION",
            "month": str(row["violation_date"])[:7],
            "metric_id": None,
            "severity": "HIGH",
            "signal_name": row["rule_id"],
            "observed_value": int(row["violation_count"]),
            "previous_value": None,
            "change_pp": None,
            "details": "One or more records failed a reconciliation rule.",
            "scenario_type": "CAPPED_SAMPLE"
        })

finally:
    con.close()

columns = [
    "event_type",
    "month",
    "metric_id",
    "severity",
    "signal_name",
    "observed_value",
    "previous_value",
    "change_pp",
    "details",
    "scenario_type"
]

report = pd.DataFrame(events, columns=columns)
REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
report.to_csv(REPORT_FILE, index=False, encoding="utf-8-sig")

print("===== METRICTRUST INVESTIGATION REPORT =====")
print("Total investigation events:", len(report))

if report.empty:
    print("No investigation events found.")
else:
    print("\nEvents by type:")
    print(report["event_type"].value_counts().to_string())

    print("\nReport preview:")
    print(report.head(15).to_string(index=False))

print(f"\nCSV report saved to: {REPORT_FILE}")
print("Sample-based findings and synthetic scenarios are labelled.")
