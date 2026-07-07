import pytest
from datetime import datetime, timezone
from transform.cleaner import clean_tick


def test_clean_tick_valid():
    """Verify that a valid tick is correctly cleaned, types are cast, and timezone is set."""
    raw = {
        "ticker": "scom.ke",
        "price": "16.50",
        "volume": 25000,
        "timestamp": datetime(2026, 6, 8, 14, 0, 0),
        "percent_change": -1.25
    }
    
    cleaned = clean_tick(raw)
    assert cleaned is not None
    assert cleaned["ticker"] == "SCOM.KE"
    assert cleaned["price"] == 16.50
    assert cleaned["volume"] == 25000
    assert cleaned["timestamp"].tzinfo == timezone.utc
    assert cleaned["percent_change"] == -1.25


def test_clean_tick_invalid_price():
    """Verify that ticks with non-positive prices are discarded (return None)."""
    raw = {
        "ticker": "SCOM.KE",
        "price": "-1.50",
        "volume": 100,
        "timestamp": datetime.now()
    }
    assert clean_tick(raw) is None


def test_clean_tick_invalid_volume():
    """Verify that ticks with negative volume are discarded."""
    raw = {
        "ticker": "SCOM.KE",
        "price": 16.50,
        "volume": -50,
        "timestamp": datetime.now()
    }
    assert clean_tick(raw) is None


def test_clean_tick_missing_required():
    """Verify that ticks missing required fields are discarded."""
    raw = {
        "ticker": "SCOM.KE",
        "price": 16.50,
        "timestamp": datetime.now()
    }
    assert clean_tick(raw) is None
