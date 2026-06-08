import time
import logging
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.dialects.postgresql import insert

from config.settings import settings
from load.models import Base, RawStockData, ProcessedMetrics

logger = logging.getLogger(__name__)

# Configure SQLAlchemy engine with pool settings
engine = create_engine(
    settings.database_url,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=1800,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency yielding a db session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(max_retries: int = 5, delay_seconds: int = 5) -> None:
    """
    Initialize database schema (creates tables if they do not exist).
    Includes retry mechanism to wait for the database container to become ready.
    """
    logger.info("Initializing database...")
    for attempt in range(1, max_retries + 1):
        try:
            # Test connection
            with engine.connect() as conn:
                logger.info("Database connection established successfully.")
            # Create tables
            Base.metadata.create_all(bind=engine)
            logger.info("Database schema initialized successfully.")
            return
        except Exception as e:
            logger.warning(
                f"Database connection attempt {attempt}/{max_retries} failed: {e}. "
                f"Retrying in {delay_seconds} seconds..."
            )
            time.sleep(delay_seconds)
    raise RuntimeError("Could not connect to database after maximum retries.")


def upsert_raw_stock_data(db: Session, raw_data_dict: dict) -> RawStockData:
    """
    Perform an idempotent upsert of raw stock data using PostgreSQL's ON CONFLICT statement.
    """
    stmt = insert(RawStockData).values(**raw_data_dict)
    
    # On conflict of (ticker, timestamp), do nothing (or we could update fields if necessary)
    upsert_stmt = stmt.on_conflict_do_nothing(
        index_elements=["ticker", "timestamp"]
    )
    
    db.execute(upsert_stmt)
    db.commit()
    
    # Query back to return the object
    return (
        db.query(RawStockData)
        .filter_by(
            ticker=raw_data_dict["ticker"],
            timestamp=raw_data_dict["timestamp"]
        )
        .first()
    )


def upsert_processed_metrics(db: Session, metrics_dict: dict) -> ProcessedMetrics:
    """
    Perform an idempotent upsert of processed metrics using PostgreSQL's ON CONFLICT statement.
    """
    stmt = insert(ProcessedMetrics).values(**metrics_dict)
    
    # On conflict of (ticker, timestamp), update all calculation fields
    update_dict = {
        col: stmt.excluded[col]
        for col in [
            "price",
            "percent_change",
            "sma_5m",
            "sma_15m",
            "volatility",
            "momentum",
            "anomaly_detected",
            "anomaly_reason",
            "price_drop_alert"
        ]
    }
    
    upsert_stmt = stmt.on_conflict_do_update(
        index_elements=["ticker", "timestamp"],
        set_=update_dict
    )
    
    db.execute(upsert_stmt)
    db.commit()
    
    return (
        db.query(ProcessedMetrics)
        .filter_by(
            ticker=metrics_dict["ticker"],
            timestamp=metrics_dict["timestamp"]
        )
        .first()
    )
