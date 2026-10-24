
import pandas as pd


def calculate_closure_rate(total_requests, closed_requests):
    """Calculate closure rate as a percentage."""
    if total_requests < 0 or closed_requests < 0:
        raise ValueError("Request counts cannot be negative.")

    if closed_requests > total_requests:
        raise ValueError(
            "Closed requests cannot exceed total requests."
        )

    if total_requests == 0:
        return 0.0

    return round(closed_requests / total_requests * 100, 3)


def find_mt001_violations(df):
    """
    Find records marked Closed whose closed_date is missing.
    Returns a DataFrame containing the violating records.
    """
    required_columns = {"status", "closed_date"}
    missing_columns = required_columns - set(df.columns)

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {sorted(missing_columns)}"
        )

    status = df["status"].astype("string").str.strip().str.lower()
    closed_date = pd.to_datetime(
        df["closed_date"], errors="coerce"
    )

    mask = status.eq("closed") & closed_date.isna()
    return df.loc[mask].copy()


def detect_threshold_signal(current_value, previous_value, threshold):
    """
    Detect whether the absolute change reaches the threshold.
    Values and threshold must use the same unit.
    """
    if threshold < 0:
        raise ValueError("Threshold cannot be negative.")

    if pd.isna(current_value) or pd.isna(previous_value):
        return False

    return abs(current_value - previous_value) >= threshold


def compare_closure_rates(
    total_requests,
    status_closed_requests,
    requests_with_closed_date
):
    """Compare two closure definitions on the same cohort."""
    status_rate = calculate_closure_rate(
        total_requests, status_closed_requests
    )
    date_rate = calculate_closure_rate(
        total_requests, requests_with_closed_date
    )

    return {
        "status_based_rate_pct": status_rate,
        "date_based_rate_pct": date_rate,
        "definition_impact_pp": round(date_rate - status_rate, 3),
    }
