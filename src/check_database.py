
from pathlib import Path
import duckdb

db_path = Path(__file__).resolve().parent.parent / "data" / "metrictrust.duckdb"

print("MetricTrust database verification")
print("Database exists:", db_path.exists())

if not db_path.exists():
    print("ERROR: Database file not found.")
    raise SystemExit(1)

con = duckdb.connect(str(db_path), read_only=True)

try:
    tables = con.execute("SHOW TABLES").fetchall()

    print("\nTables found:")
    for (table_name,) in tables:
        print(f"\n--- {table_name} ---")

        columns = con.execute(
            f"PRAGMA table_info('{table_name}')"
        ).fetchall()

        for column in columns:
            print(f"  {column[1]}: {column[2]}")

finally:
    con.close()

print("\nDatabase verification complete.")
