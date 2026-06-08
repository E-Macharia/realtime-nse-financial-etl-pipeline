import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List
import pandas as pd
import numpy as np
from sqlalchemy.orm import Session

from config.settings import settings
from load.models import RawStockData

logger = logging.getLogger(__name__)


def get_historical_ticks(db: Session, ticker: str, window_minutes: int = 20) -> List[RawStockData]:
    """
    Fetches raw stock ticks for a ticker from the database within the last N minutes.
    """
    cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
    return (
        db.query(RawStockData)
        .filter(
            RawStockData.ticker == ticker,
            RawStockData.timestamp >= cutoff_time
        )
        .order_by(RawStockData.timestamp.asc())
        .all()
    )


def calculate_metrics(db: Session, current_tick: Dict[str, Any]) -> Dict[str, Any]:
    """
    Computes technical indicators and performs anomaly/alert detection.
    Combines the current tick with recent database ticks.
    """
    ticker = current_tick["ticker"]
    
    # 1. Fetch historical ticks (query last 20 mins of ticks to comfortably cover 15m window)
    history = get_historical_ticks(db, ticker, window_minutes=25)
    
    # Convert historical objects to dictionary representations
    records = []
    for h in history:
        records.append({
            "price": h.price,
            "volume": h.volume,
            "timestamp": h.timestamp,
            "percent_change": h.percent_change or 0.0
        })
        
    # Append the current tick to include it in the rolling calculation
    records.append({
        "price": current_tick["price"],
        "volume": current_tick["volume"],
        "timestamp": current_tick["timestamp"],
        "percent_change": current_tick["percent_change"]
    })
    
    # 2. Build pandas DataFrame
    df = pd.DataFrame(records)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp")
    df = df.drop_duplicates(subset=["timestamp"], keep="last")
    df.set_index("timestamp", inplace=True)
    
    # Define outputs with fallback defaults
    sma_5m = None
    sma_15m = None
    volatility = 0.0
    momentum = 0.0
    anomaly_detected = False
    anomaly_reason = None
    price_drop_alert = False
    
    try:
        # Calculate moving averages using time-based window
        sma_5m = float(df["price"].rolling("5min").mean().iloc[-1])
        sma_15m = float(df["price"].rolling("15min").mean().iloc[-1])
        
        # Volatility: rolling std of percent changes over last 5m
        vol_series = df["percent_change"].rolling("5min").std()
        if len(vol_series) > 1 and not pd.isna(vol_series.iloc[-1]):
            volatility = float(vol_series.iloc[-1])
            
        # Momentum: percentage return compared to price 5 minutes ago
        target_time = df.index[-1] - pd.Timedelta(minutes=5)
        # Using asof to locate price at target time
        price_5m_index = df.index.asof(target_time)
        if not pd.isna(price_5m_index):
            price_5m_ago = df.loc[price_5m_index, "price"]
            if isinstance(price_5m_ago, pd.Series):
                price_5m_ago = price_5m_ago.iloc[-1]
            price_5m_ago = float(price_5m_ago)
            if price_5m_ago > 0:
                momentum = float(((df["price"].iloc[-1] - price_5m_ago) / price_5m_ago) * 100.0)

        # 3. Anomaly & Alert Rules
        anomalies = []
        
        # Rule A: Volume anomaly (volume spike > mean + 3 * std over 15 minutes)
        vol_mean = df["volume"].rolling("15min").mean().iloc[-1]
        vol_std = df["volume"].rolling("15min").std().iloc[-1]
        
        if not pd.isna(vol_mean) and vol_mean > 0:
            if not pd.isna(vol_std) and vol_std > 0:
                vol_threshold = vol_mean + settings.ANOMALY_SD_MULTIPLIER * vol_std
            else:
                vol_threshold = vol_mean * 3.0  # Fallback if insufficient points for std
            
            if current_tick["volume"] > vol_threshold:
                anomalies.append("volume_spike")
                logger.warning(
                    f"[ANOMALY] Volume spike detected for {ticker}: "
                    f"Current={current_tick['volume']}, Threshold={vol_threshold:.1f}"
                )

        # Rule B: Price Shock (absolute change exceeds 3 * standard deviation of recent volatility)
        if volatility > 0.01: # ignore tiny oscillations
            price_change_limit = settings.ANOMALY_SD_MULTIPLIER * volatility
            if abs(current_tick["percent_change"]) > price_change_limit:
                anomalies.append("price_shock")
                logger.warning(
                    f"[ANOMALY] Price shock detected for {ticker}: "
                    f"Change={current_tick['percent_change']}%, Threshold={price_change_limit:.2f}%"
                )

        # Flag anomaly state
        if anomalies:
            anomaly_detected = True
            anomaly_reason = ", ".join(anomalies)

        # Rule C: Price Drop Alert (price drops > 5.0% compared to 5-minute maximum price)
        max_price_5m = df["price"].rolling("5min").max().iloc[-1]
        if not pd.isna(max_price_5m) and max_price_5m > 0:
            drop_pct = ((max_price_5m - current_tick["price"]) / max_price_5m) * 100.0
            if drop_pct >= settings.ALERT_PRICE_DROP_PCT:
                price_drop_alert = True
                logger.critical(
                    f"[ALERT] {ticker} Price dropped by {drop_pct:.2f}% from its 5-minute high of {max_price_5m}!"
                )

    except Exception as e:
        logger.error(f"Error calculating financial indicators for {ticker}: {e}", exc_info=True)

    # Return structured dict to be upserted to processed_metrics table
    return {
        "ticker": ticker,
        "timestamp": current_tick["timestamp"],
        "price": current_tick["price"],
        "percent_change": current_tick["percent_change"],
        "sma_5m": round(sma_5m, 2) if sma_5m else None,
        "sma_15m": round(sma_15m, 2) if sma_15m else None,
        "volatility": round(volatility, 4),
        "momentum": round(momentum, 2),
        "anomaly_detected": anomaly_detected,
        "anomaly_reason": anomaly_reason,
        "price_drop_alert": price_drop_alert
    }
