
import duckdb
import matplotlib.pyplot as plt
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_FILE = ROOT / "data" / "metrictrust.duckdb"
REPORTS_DIR = ROOT / "reports"

REPORTS_DIR.mkdir(parents=True, exist_ok=True)

con = duckdb.connect(str(DB_FILE), read_only=True)

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
finally:
    con.close()

if df.empty:
    raise RuntimeError("No KPI results found. Run calculate_kpis.py first.")

# Chart 1: Monthly closure rate
plt.figure(figsize=(13, 5))
plt.plot(
    df["month"],
    df["closure_rate_pct"],
    marker="o",
    linewidth=1.8
)
plt.title("MetricTrust — Monthly Sample Closure Rate")
plt.xlabel("Creation month")
plt.ylabel("Closure rate (%)")
plt.xticks(rotation=60)
plt.grid(True, alpha=0.3)
plt.tight_layout()

closure_chart = REPORTS_DIR / "monthly_closure_rate.png"
plt.savefig(closure_chart, dpi=150)
plt.close()

# Chart 2: Monthly sample request counts
plt.figure(figsize=(13, 5))
plt.bar(df["month"], df["total_requests"])
plt.title("MetricTrust — Monthly Sample Records")
plt.xlabel("Creation month")
plt.ylabel("Records in sample")
plt.xticks(rotation=60)
plt.grid(axis="y", alpha=0.3)
plt.tight_layout()

count_chart = REPORTS_DIR / "monthly_sample_counts.png"
plt.savefig(count_chart, dpi=150)
plt.close()

print("===== CHARTS CREATED =====")
print(f"Closure rate chart: {closure_chart}")
print(f"Monthly sample counts chart: {count_chart}")
print("\nFirst 5 months:")
print(df.head().to_string(index=False))
print("\nReminder: These are capped-sample metrics, not population totals.")
