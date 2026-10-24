
import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = PROJECT_ROOT / "data" / "raw" / "nyc_311_sample.csv"

df = pd.read_csv(DATA_FILE)

print("===== METRICTRUST: DATA PROFILE =====")

print("\n1. Agency distribution:")
print(df["agency"].value_counts(dropna=False))

print("\n2. Status distribution:")
print(df["status"].value_counts(dropna=False))

print("\n3. Unique request IDs:")
print("Unique IDs:", df["unique_key"].nunique())
print("Duplicate IDs:", df["unique_key"].duplicated().sum())

print("\n4. Date range:")
df["created_date"] = pd.to_datetime(
    df["created_date"], errors="coerce"
)
print("Earliest:", df["created_date"].min())
print("Latest:", df["created_date"].max())

print("\n5. Missing closed dates by status:")
print(
    df.groupby("status")["closed_date"]
    .apply(lambda s: s.isna().sum())
)

print("\n===== PROFILE COMPLETE =====")
