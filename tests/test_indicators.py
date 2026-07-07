import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from load.models import Base, RawStockData
from transform.indicators import calculate_metrics


@pytest.fixture
def db_session():
    """Fixture creating an in-memory SQLite database for time-series testing."""
    engine = create_engine("sqlite://")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


def test_calculate_metrics_basic(db_session):
    """Verify standard SMA and volatility values when historical records are present."""
    ticker = "SCOM.KE"
    base_time = datetime.now(timezone.utc) - timedelta(minutes=10)
    
    # Seed 10 historical records to populate the rolling window (one every 10 seconds)
    for i in range(10):
        tick_time = base_time + timedelta(seconds=i * 10)
        db_session.add(RawStockData(
            ticker=ticker,
            price=15.0 + (i * 0.1),  # gradual upward trend: 15.0 to 15.9
            volume=5000,
            timestamp=tick_time,
            percent_change=0.5
        ))
    db_session.commit()
    
    # Current tick to analyze
    current_tick = {
        "ticker": ticker,
        "price": 16.0,
        "volume": 5000,
        "timestamp": base_time + timedelta(seconds=100),
        "percent_change": 0.6
    }
    
    metrics = calculate_metrics(db_session, current_tick)
    
    assert metrics is not None
    assert metrics["ticker"] == ticker
    assert metrics["price"] == 16.0
    # SMA 5m should be successfully computed
    assert metrics["sma_5m"] is not None
    assert metrics["sma_5m"] > 15.0
    assert metrics["anomaly_detected"] is False


def test_calculate_metrics_volume_anomaly(db_session):
    """Verify that a massive volume spike triggers a volume anomaly flag."""
    ticker = "SCOM.KE"
    base_time = datetime.now(timezone.utc) - timedelta(minutes=10)
    
    # Seed historical records with low standard volume
    for i in range(12):
        tick_time = base_time + timedelta(seconds=i * 10)
        db_session.add(RawStockData(
            ticker=ticker,
            price=15.0,
            volume=1000,
            timestamp=tick_time,
            percent_change=0.0
        ))
    db_session.commit()
    
    # Current tick with a 10x volume spike
    current_tick = {
        "ticker": ticker,
        "price": 15.0,
        "volume": 10000,
        "timestamp": base_time + timedelta(seconds=120),
        "percent_change": 0.0
    }
    
    metrics = calculate_metrics(db_session, current_tick)
    
    assert metrics["anomaly_detected"] is True
    assert "volume_spike" in metrics["anomaly_reason"]
