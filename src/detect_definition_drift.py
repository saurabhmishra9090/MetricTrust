
import duckdb
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_FILE = ROOT / "data" / "metrictrust.duckdb"

con = duckdb.connect(str(DB_FILE))

try:
    registry = con.execute("""
        SELECT
            metric_id,
            metric_name,
            version,
            formula_definition,
            effective_from,
            effective_to,
            is_current,
            change_reason
        FROM metric_registry
        ORDER BY metric_id, version
    """).df()

    drift_rows = []

    for metric_id, versions in registry.groupby("metric_id"):
        versions = versions.sort_values("version")

        if len(versions) < 2:
            continue

        for i in range(1, len(versions)):
            previous = versions.iloc[i - 1]
            current = versions.iloc[i]

            formula_changed = (
                previous["formula_definition"]
                != current["formula_definition"]
            )

            if formula_changed:
                reason = str(current["change_reason"])
                change_type = (
                    "SYNTHETIC"
                    if "SYNTHETIC" in reason.upper()
                    else "UNCLASSIFIED"
                )

                drift_rows.append({
                    "metric_id": metric_id,
                    "previous_version": int(previous["version"]),
                    "current_version": int(current["version"]),
                    "previous_formula": previous["formula_definition"],
                    "current_formula": current["formula_definition"],
                    "effective_from": current["effective_from"],
                    "change_type": change_type,
                    "change_reason": reason
                })

    columns = [
        "metric_id",
        "previous_version",
        "current_version",
        "previous_formula",
        "current_formula",
        "effective_from",
        "change_type",
        "change_reason"
    ]

    drift_df = pd.DataFrame(drift_rows, columns=columns)

    con.execute("""
        CREATE TABLE IF NOT EXISTS definition_drift_results (
            metric_id VARCHAR,
            previous_version INTEGER,
            current_version INTEGER,
            previous_formula VARCHAR,
            current_formula VARCHAR,
            effective_from DATE,
            change_type VARCHAR,
            change_reason VARCHAR
        )
    """)

    con.execute("DELETE FROM definition_drift_results")

    if not drift_df.empty:
        con.register("drift_df", drift_df)
        con.execute("""
            INSERT INTO definition_drift_results
            SELECT
                metric_id,
                previous_version,
                current_version,
                previous_formula,
                current_formula,
                CAST(effective_from AS DATE),
                change_type,
                change_reason
            FROM drift_df
        """)
        con.unregister("drift_df")

    print("===== DEFINITION DRIFT REPORT =====")

    if drift_df.empty:
        print("No formula changes detected in the registered versions.")
    else:
        print(drift_df.to_string(index=False))

    print("\nDefinition changes detected:", len(drift_df))
    print("Results saved to definition_drift_results.")

finally:
    con.close()
