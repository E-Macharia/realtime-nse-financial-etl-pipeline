import json
import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from config.settings import settings
from load.db import get_db
from load.models import ProcessedMetrics

logger = logging.getLogger("api_routes")
router = APIRouter()


def parse_datetime(val: Any) -> Optional[datetime]:
    """Parse datetime from various representations."""
    if not val:
        return None
    if isinstance(val, datetime):
        return val
    try:
        return datetime.fromisoformat(val.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


@router.get("/stocks/latest", response_model=List[Dict[str, Any]])
def get_latest_stocks(request: Request, db: Session = Depends(get_db)):
    """
    Fetch the latest price and indicators for all active tickers.
    Queries Redis cache first, falling back to PostgreSQL if unavailable.
    """
    redis_client = request.app.state.redis
    latest_data = []
    
    # 1. Attempt Redis retrieval
    if redis_client:
        try:
            keys = [f"stock:{ticker}:latest" for ticker in settings.TICKERS]
            cached_vals = redis_client.mget(keys)
            
            for val in cached_vals:
                if val:
                    latest_data.append(json.loads(val))
                    
            if len(latest_data) == len(settings.TICKERS):
                logger.debug("Served latest stock data from Redis cache.")
                return latest_data
        except Exception as e:
            logger.error(f"Failed to fetch from Redis cache: {e}. Falling back to PostgreSQL.")
            latest_data = []

    # 2. Database Fallback (if cache misses or Redis is down)
    logger.info("Cache miss or Redis offline. Fetching latest stock data from PostgreSQL database.")
    try:
        # Subquery to locate the maximum timestamp per ticker
        subq = (
            db.query(
                ProcessedMetrics.ticker,
                func.max(ProcessedMetrics.timestamp).label("max_ts")
            )
            .group_by(ProcessedMetrics.ticker)
            .subquery()
        )
        
        # Join main table to retrieve complete records
        records = (
            db.query(ProcessedMetrics)
            .join(
                subq,
                (ProcessedMetrics.ticker == subq.c.ticker) &
                (ProcessedMetrics.timestamp == subq.c.max_ts)
            )
            .all()
        )
        
        # Serialize database objects
        latest_data = [
            {
                "ticker": r.ticker,
                "timestamp": r.timestamp.isoformat(),
                "price": r.price,
                "percent_change": r.percent_change,
                "sma_5m": r.sma_5m,
                "sma_15m": r.sma_15m,
                "volatility": r.volatility,
                "momentum": r.momentum,
                "anomaly_detected": r.anomaly_detected,
                "anomaly_reason": r.anomaly_reason,
                "price_drop_alert": r.price_drop_alert,
            }
            for r in records
        ]
        
        # Cache back to Redis for subsequent calls
        if redis_client and latest_data:
            try:
                for item in latest_data:
                    redis_client.set(f"stock:{item['ticker']}:latest", json.dumps(item), ex=3600)
            except Exception as cache_err:
                logger.error(f"Failed to cache database results: {cache_err}")
                
        return latest_data
    except Exception as e:
        logger.error(f"Error querying latest stock prices from database: {e}")
        return []


@router.get("/stocks/history/{ticker}", response_model=List[Dict[str, Any]])
def get_stock_history(ticker: str, limit: int = Query(50, ge=1, le=500), db: Session = Depends(get_db)):
    """
    Retrieve historical data points for a specific ticker to populate chart series.
    Returns records in chronological order.
    """
    ticker_upper = ticker.strip().upper()
    try:
        records = (
            db.query(ProcessedMetrics)
            .filter(ProcessedMetrics.ticker == ticker_upper)
            .order_by(ProcessedMetrics.timestamp.desc())
            .limit(limit)
            .all()
        )
        
        # Reverse list to yield ascending chronological order for plotting
        history = [
            {
                "ticker": r.ticker,
                "timestamp": r.timestamp.isoformat(),
                "price": r.price,
                "percent_change": r.percent_change,
                "sma_5m": r.sma_5m,
                "sma_15m": r.sma_15m,
                "volatility": r.volatility,
                "momentum": r.momentum,
                "anomaly_detected": r.anomaly_detected,
                "anomaly_reason": r.anomaly_reason,
                "price_drop_alert": r.price_drop_alert,
            }
            for r in reversed(records)
        ]
        return history
    except Exception as e:
        logger.error(f"Error querying historical data for {ticker_upper}: {e}")
        return []


@router.get("/stocks/summary", response_model=Dict[str, Any])
def get_market_summary(request: Request, db: Session = Depends(get_db)):
    """
    Get aggregated market performance metrics, active alerts, and anomaly records.
    """
    latest = get_latest_stocks(request, db)
    if not latest:
        return {
            "top_gainer": None,
            "top_loser": None,
            "avg_volatility": 0.0,
            "total_active_alerts": 0,
            "total_anomalies_detected": 0,
            "active_alerts": [],
            "anomalies": []
        }

    # Extract metrics
    gainers = sorted(latest, key=lambda x: x["percent_change"] or 0.0, reverse=True)
    top_gainer = gainers[0] if gainers else None
    top_loser = gainers[-1] if gainers else None
    
    volatilities = [x["volatility"] for x in latest if x.get("volatility") is not None]
    avg_volatility = sum(volatilities) / len(volatilities) if volatilities else 0.0
    
    active_alerts = [x for x in latest if x.get("price_drop_alert")]
    anomalies = [x for x in latest if x.get("anomaly_detected")]

    return {
        "top_gainer": {
            "ticker": top_gainer["ticker"],
            "price": top_gainer["price"],
            "percent_change": top_gainer["percent_change"]
        } if top_gainer else None,
        "top_loser": {
            "ticker": top_loser["ticker"],
            "price": top_loser["price"],
            "percent_change": top_loser["percent_change"]
        } if top_loser else None,
        "avg_volatility": round(avg_volatility, 4),
        "total_active_alerts": len(active_alerts),
        "total_anomalies_detected": len(anomalies),
        "active_alerts": [x["ticker"] for x in active_alerts],
        "anomalies": [
            {"ticker": x["ticker"], "reason": x["anomaly_reason"]}
            for x in anomalies
        ]
    }


@router.websocket("/stocks/ws")
async def websocket_endpoint(websocket: WebSocket, db: Session = Depends(get_db)):
    """
    WebSocket endpoint serving real-time updates of processed metrics.
    Subscribes to Redis pub/sub channel.
    Falls back to PostgreSQL polling if Redis is down.
    """
    await websocket.accept()
    logger.info("WebSocket connection established.")
    
    redis_client = websocket.app.state.redis
    
    # Mode A: Redis Pub/Sub Subscriber
    if redis_client:
        pubsub = redis_client.pubsub()
        try:
            pubsub.subscribe("stock_updates")
            logger.info("WebSocket subscribed to Redis channel 'stock_updates'.")
            
            while True:
                # Poll pubsub with a timeout to keep the loop responsive
                message = pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message:
                    payload = message["data"]
                    await websocket.send_text(payload)
                # Small sleep to yield control to event loop
                await asyncio.sleep(0.01)
                
        except WebSocketDisconnect:
            logger.info("WebSocket disconnected (client closed connection).")
        except Exception as e:
            logger.error(f"WebSocket Redis connection error: {e}. Transitioning to PostgreSQL database polling.")
            # Fall back to polling database
            await db_polling_fallback(websocket, db)
        finally:
            try:
                pubsub.unsubscribe("stock_updates")
                pubsub.close()
            except Exception:
                pass
    # Mode B: Database Polling Fallback
    else:
        logger.warning("Redis is offline. WebSocket starting in PostgreSQL database polling mode.")
        await db_polling_fallback(websocket, db)


async def db_polling_fallback(websocket: WebSocket, db: Session):
    """
    Fallback loop that queries the database every 2 seconds for new data.
    Keeps track of last sent timestamps per ticker.
    """
    last_sent_timestamps: Dict[str, datetime] = {}
    
    try:
        while True:
            # Query the latest rows from database
            subq = (
                db.query(
                    ProcessedMetrics.ticker,
                    func.max(ProcessedMetrics.timestamp).label("max_ts")
                )
                .group_by(ProcessedMetrics.ticker)
                .subquery()
            )
            
            records = (
                db.query(ProcessedMetrics)
                .join(
                    subq,
                    (ProcessedMetrics.ticker == subq.c.ticker) &
                    (ProcessedMetrics.timestamp == subq.c.max_ts)
                )
                .all()
            )
            
            for r in records:
                # Check if this timestamp is newer than what we previously broadcasted
                last_ts = last_sent_timestamps.get(r.ticker)
                # Normalize database timestamp to offset-naive or tz-aware matching
                record_ts = r.timestamp
                
                if not last_ts or record_ts > last_ts:
                    last_sent_timestamps[r.ticker] = record_ts
                    
                    payload = {
                        "ticker": r.ticker,
                        "timestamp": r.timestamp.isoformat(),
                        "price": r.price,
                        "percent_change": r.percent_change,
                        "sma_5m": r.sma_5m,
                        "sma_15m": r.sma_15m,
                        "volatility": r.volatility,
                        "momentum": r.momentum,
                        "anomaly_detected": r.anomaly_detected,
                        "anomaly_reason": r.anomaly_reason,
                        "price_drop_alert": r.price_drop_alert
                    }
                    
                    await websocket.send_json(payload)
            
            # Poll interval
            await asyncio.sleep(2.0)
            
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected in database polling mode.")
    except Exception as e:
        logger.error(f"Error in WebSocket database polling fallback: {e}")
