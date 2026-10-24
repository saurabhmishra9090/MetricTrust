
import requests
import pandas as pd
from pathlib import Path

API_URL = "https://data.cityofnewyork.us/resource/erm2-nwe9.json"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_FILE = PROJECT_ROOT / "data" / "raw" / "nyc_311_monthly_sample.csv"

MONTHLY_LIMIT = 1000
AGENCIES = ("NYPD", "DOT", "DEP")

all_records = []

for year in range(2023, 2026):
    for month in range(1, 13):
        start_date = f"{year}-{month:02d}-01T00:00:00"

        if month == 12:
            end_date = f"{year + 1}-01-01T00:00:00"
        else:
            end_date = f"{year}-{month + 1:02d}-01T00:00:00"

        agency_filter = ",".join(f"'{agency}'" for agency in AGENCIES)

        params = {
            "$select": (
                "unique_key,created_date,closed_date,agency,"
                "agency_name,status,complaint_type,descriptor"
            ),
            "$where": (
                f"created_date >= '{start_date}' "
                f"AND created_date < '{end_date}' "
                f"AND agency in ({agency_filter})"
            ),
            "$order": "created_date DESC",
            "$limit": MONTHLY_LIMIT
        }

        try:
            response = requests.get(API_URL, params=params, timeout=60)
            response.raise_for_status()
            records = response.json()

            all_records.extend(records)

            print(
                f"{year}-{month:02d}: "
                f"{len(records):,} records downloaded"
            )

        except (requests.RequestException, ValueError) as error:
            print(f"ERROR for {year}-{month:02d}: {error}")
            raise

if not all_records:
    raise RuntimeError("No records downloaded. Check the API query.")

df = pd.DataFrame(all_records)

# Keep only one row per request ID if any IDs repeat across monthly batches.
df = df.drop_duplicates(subset=["unique_key"])

df["created_date"] = pd.to_datetime(
    df["created_date"], errors="coerce"
)

df = df.sort_values("created_date").reset_index(drop=True)

df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

print("\n===== MONTHLY SAMPLE COMPLETE =====")
print(f"Total unique request IDs: {len(df):,}")
print(f"Total columns: {len(df.columns)}")
print(f"Saved to: {OUTPUT_FILE}")
print(f"Date range: {df['created_date'].min()} to {df['created_date'].max()}")
