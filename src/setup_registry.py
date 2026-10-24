
import duckdb
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DB_PATH = PROJECT_ROOT / "data" / "metrictrust.duckdb"
SQL_PATH = PROJECT_ROOT / "sql" / "01_metric_registry.sql"

if not SQL_PATH.exists():
    raise FileNotFoundError(f"SQL file not found: {SQL_PATH}")

connection = duckdb.connect(str(DB_PATH))

try:
    sql_script = SQL_PATH.read_text(encoding="utf-8")
    connection.execute(sql_script)

    metrics = connection.execute(
        """
        SELECT metric_id, metric_name, version, is_current
        FROM metric_registry
        ORDER BY metric_id
        """
    ).fetchall()

    rules = connection.execute(
        """
        SELECT rule_id, rule_name, severity, version, is_active
        FROM reconciliation_rule_registry
        ORDER BY rule_id
        """
    ).fetchall()

    print("===== METRICTRUST REGISTRY =====")

    print("\nRegistered KPIs:")
    for metric in metrics:
        print(metric)

    print("\nRegistered reconciliation rules:")
    for rule in rules:
        print(rule)

    print(f"\nDatabase saved at: {DB_PATH}")

finally:
    connection.close()
