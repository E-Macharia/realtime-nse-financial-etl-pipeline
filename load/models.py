from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, UniqueConstraint, Index
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class RawStockData(Base):
    """
    Stores raw stock tick data ingested from the market source.
    """
    __tablename__ = "raw_stock_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(20), nullable=False)
    price = Column(Float, nullable=False)
    volume = Column(Integer, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    percent_change = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("ticker", "timestamp", name="uq_raw_ticker_timestamp"),
        Index("idx_raw_ticker_timestamp", "ticker", "timestamp"),
    )

    def __repr__(self) -> str:
        return f"<RawStockData(ticker={self.ticker}, price={self.price}, timestamp={self.timestamp})>"


class ProcessedMetrics(Base):
    """
    Stores technical indicators, moving averages, and anomaly flags computed by the transform layer.
    """
    __tablename__ = "processed_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(20), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    
    # Prices & Changes
    price = Column(Float, nullable=False)
    percent_change = Column(Float, nullable=True)

    # Technical Indicators
    sma_5m = Column(Float, nullable=True)
    sma_15m = Column(Float, nullable=True)
    volatility = Column(Float, nullable=True)
    momentum = Column(Float, nullable=True)

    # Anomaly / Alert flags
    anomaly_detected = Column(Boolean, default=False, nullable=False)
    anomaly_reason = Column(String(255), nullable=True)
    price_drop_alert = Column(Boolean, default=False, nullable=False)
    
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("ticker", "timestamp", name="uq_processed_ticker_timestamp"),
        Index("idx_processed_ticker_timestamp", "ticker", "timestamp"),
    )

    def __repr__(self) -> str:
        return (
            f"<ProcessedMetrics(ticker={self.ticker}, price={self.price}, "
            f"sma_5m={self.sma_5m}, sma_15m={self.sma_15m}, anomaly={self.anomaly_detected})>"
        )
