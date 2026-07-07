import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.main import app
from load.db import get_db
from load.models import Base, ProcessedMetrics

# Setup an isolated SQLite engine for API route tests
engine = create_engine("sqlite://")
Base.metadata.create_all(bind=engine)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Dependency override yielding a clean SQLite session."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Bind the dependency override in the FastAPI application
app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    """Clear database and seed mock records before every API test case."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    # Add a mock metric record to test API queries
    db.add(ProcessedMetrics(
        ticker="SCOM.KE",
        timestamp=datetime.now(timezone.utc),
        price=16.50,
        percent_change=1.25,
        sma_5m=16.30,
        sma_15m=16.10,
        volatility=0.045,
        momentum=0.85,
        anomaly_detected=False,
        price_drop_alert=False
    ))
    db.commit()
    db.close()


def test_get_latest_stocks():
    """Verify that /stocks/latest retrieves seeded metrics successfully."""
    response = client.get("/stocks/latest")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["ticker"] == "SCOM.KE"
    assert data[0]["price"] == 16.50


def test_get_market_summary():
    """Verify that /stocks/summary calculates top performings correctly."""
    response = client.get("/stocks/summary")
    assert response.status_code == 200
    data = response.json()
    assert "top_gainer" in data
    assert data["top_gainer"]["ticker"] == "SCOM.KE"
    assert data["top_gainer"]["price"] == 16.50
