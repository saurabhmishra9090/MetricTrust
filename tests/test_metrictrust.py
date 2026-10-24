
import pandas as pd
import pytest

from src.metric_logic import (
    calculate_closure_rate,
    find_mt001_violations,
    detect_threshold_signal,
    compare_closure_rates,
)


def test_closure_rate_calculation():
    assert calculate_closure_rate(4, 3) == 75.0


def test_zero_requests_returns_zero():
    assert calculate_closure_rate(0, 0) == 0.0


def test_closure_rate_rejects_invalid_counts():
    with pytest.raises(ValueError):
        calculate_closure_rate(10, 11)

    with pytest.raises(ValueError):
        calculate_closure_rate(-1, 0)


def test_mt001_flags_closed_without_closed_date():
    df = pd.DataFrame({
        "unique_key": [101, 102, 103],
        "status": ["Closed", "Pending", "Closed"],
        "closed_date": [None, None, "2026-01-02"],
    })

    violations = find_mt001_violations(df)

    assert len(violations) == 1
    assert violations.iloc[0]["unique_key"] == 101


def test_mt001_is_case_insensitive_and_trims_spaces():
    df = pd.DataFrame({
        "status": [" closed ", "CLOSED", "Pending"],
        "closed_date": [None, "2026-01-02", None],
    })

    violations = find_mt001_violations(df)

    assert len(violations) == 1
    assert violations.iloc[0]["status"] == " closed "


def test_mt001_rejects_missing_required_columns():
    df = pd.DataFrame({"status": ["Closed"]})

    with pytest.raises(ValueError):
        find_mt001_violations(df)


def test_threshold_signal():
    assert detect_threshold_signal(100.0, 99.5, 0.5) is True
    assert detect_threshold_signal(100.0, 99.8, 0.5) is False


def test_threshold_signal_handles_missing_values():
    assert detect_threshold_signal(float("nan"), 99.5, 0.5) is False


def test_definition_impact():
    result = compare_closure_rates(
        total_requests=100,
        status_closed_requests=90,
        requests_with_closed_date=92,
    )

    assert result["status_based_rate_pct"] == 90.0
    assert result["date_based_rate_pct"] == 92.0
    assert result["definition_impact_pp"] == 2.0


def test_synthetic_change_label():
    change_reason = "SYNTHETIC TEST: formula changed"

    assert "SYNTHETIC" in change_reason.upper()

def test_mt001_flags_only_closed_requests_missing_closure_date():
    df = pd.DataFrame({
        "status": ["Closed", "Closed", "Pending"],
        "closed_date": [None, "2025-01-10", None],
    })

    violations = find_mt001_violations(df)

    assert len(violations) == 1
    assert violations.iloc[0]["status"] == "Closed"
    assert pd.isna(violations.iloc[0]["closed_date"])

