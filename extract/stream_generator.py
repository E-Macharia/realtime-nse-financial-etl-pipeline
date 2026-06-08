import time
import json
import logging
from datetime import datetime
import redis

from config.settings import settings
from extract.api_client import APIClient
from transform.cleaner import clean_tick
from transform.indicators import calculate_metrics
from load.db import init_db, SessionLocal, upsert_raw_stock_data, upsert_processed_metrics

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("stream_generator")


def json_serializer(obj):
    """Custom JSON serializer for datetime objects."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


class StreamGeneratorETL:
    def __init__(self):
        # Initialize Database
        init_db()
        
        # Initialize API client
        self.api_client = APIClient()
        
        # Connect to Redis with graceful fallback
        self.redis_client = None
        try:
            self.redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                password=settings.REDIS_PASSWORD,
                decode_responses=True,
                socket_timeout=2.0
            )
            # Ping Redis to test connection
            self.redis_client.ping()
            logger.info("Connected to Redis cache successfully.")
        except Exception as e:
            logger.warning(
                f"Could not connect to Redis cache: {e}. "
                f"Redis caching and publishing will be disabled."
            )
            self.redis_client = None

    def run(self):
        logger.info(
            f"Starting Ingestion Stream. Interval: {settings.STREAM_INTERVAL_SECONDS} seconds."
        )
        
        while True:
            start_time = time.time()
            db = SessionLocal()
            
            try:
                for ticker in settings.TICKERS:
                    # 1. EXTRACT
                    raw_tick = self.api_client.fetch_stock_tick(ticker)
                    if not raw_tick:
                        continue
                    
                    # 2. TRANSFORM (Clean)
                    cleaned_tick = clean_tick(raw_tick)
                    if not cleaned_tick:
                        continue
                    
                    # 3. LOAD (Idempotent Raw Insert)
                    try:
                        raw_record = upsert_raw_stock_data(db, cleaned_tick)
                    except Exception as e:
                        logger.error(f"Error saving raw stock data for {ticker}: {e}")
                        db.rollback()
                        continue
                    
                    # 4. TRANSFORM (Indicators & Anomalies)
                    metrics = calculate_metrics(db, cleaned_tick)
                    
                    # 5. LOAD (Idempotent Processed Insert)
                    try:
                        processed_record = upsert_processed_metrics(db, metrics)
                    except Exception as e:
                        logger.error(f"Error saving processed metrics for {ticker}: {e}")
                        db.rollback()
                        continue
                    
                    # 6. CACHE & PUBLISH (Redis)
                    if self.redis_client:
                        try:
                            # Cache latest metrics
                            redis_key = f"stock:{ticker}:latest"
                            serialized_metrics = json.dumps(metrics, default=json_serializer)
                            
                            # Cache values for 1 hour
                            self.redis_client.set(redis_key, serialized_metrics, ex=3600)
                            
                            # Publish metric to updates channel
                            self.redis_client.publish("stock_updates", serialized_metrics)
                            
                        except Exception as e:
                            logger.error(f"Redis cache/publish failed for {ticker}: {e}")
                
            except Exception as e:
                logger.error(f"Error in streaming ingestion loop: {e}", exc_info=True)
            finally:
                db.close()
                
            # 7. Regulate timing to prevent drift
            elapsed_time = time.time() - start_time
            sleep_time = max(0.1, settings.STREAM_INTERVAL_SECONDS - elapsed_time)
            
            logger.debug(f"Loop cycle completed in {elapsed_time:.2f}s. Sleeping for {sleep_time:.2f}s.")
            time.sleep(sleep_time)


if __name__ == "__main__":
    etl = StreamGeneratorETL()
    etl.run()
