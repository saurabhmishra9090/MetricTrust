
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILE = ROOT / "data" / "raw" / "nyc_311_monthly_sample.csv"

df = pd.read_csv(FILE)

df["created_date"] = pd.to_datetime(
    df["created_date"], errors="coerce"
)

df["month"] = df["created_date"].dt.to_period("M").astype(str)

print("===== METRICTRUST DATA AUDIT =====")

print("\n1. Dataset overview")
print("Total rows:", len(df))
print("Unique request IDs:", df["unique_key"].nunique())
print("Repeated request IDs:", df["unique_key"].duplicated().sum())
print("Invalid created dates:", df["created_date"].isna().sum())

print("\n2. Records per month")
print(df.groupby("month").size().to_string())

print("\n3. Agency distribution")
print(df["agency"].value_counts(dropna=False).to_string())

print("\n4. Status distribution")
print(df["status"].value_counts(dropna=False).to_string())

print("\n5. Missing values")
print(df.isna().sum().to_string())

print("\n===== AUDIT COMPLETE =====")

print("\n6. Closure date reconciliation")

df["closed_date"] = pd.to_datetime(
    df["closed_date"], errors="coerce"
)

df["missing_closed_date"] = df["closed_date"].isna()

print("\nMissing closed date by status:")
print(
    df.groupby("status")["missing_closed_date"]
    .sum()
    .to_string()
)

print("\nClosed status but missing closed date:")
print(
    df[
        (df["status"].str.lower() == "closed")
        & (df["missing_closed_date"])
    ][["unique_key", "created_date", "agency", "status"]]
    .head(10)
    .to_string(index=False)
)
