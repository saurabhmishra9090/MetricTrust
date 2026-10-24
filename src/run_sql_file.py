
import duckdb
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_FILE = ROOT / "data" / "metrictrust.duckdb"
SQL_FILE = ROOT / "sql" / "02_definition_change_test.sql"

con = duckdb.connect(str(DB_FILE))

try:
    sql_text = SQL_FILE.read_text(encoding="utf-8")
    statements = [
        statement.strip()
        for statement in sql_text.split(";")
        if statement.strip()
    ]

    for statement in statements:
        result = con.execute(statement)

        if statement.upper().startswith("SELECT"):
            print(result.df().to_string(index=False))

    print("\nDefinition-change test executed.")

finally:
    con.close()
