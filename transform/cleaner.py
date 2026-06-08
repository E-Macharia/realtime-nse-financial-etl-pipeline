import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def clean_tick(raw_data: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Cleans and validates a raw tick record.
    Returns the cleaned dictionary, or None if the record is corrupt/invalid.
    """
    if not raw_data:
        return None

    try:
        # 1. Check required fields
        required_fields = ["ticker", "price", "volume", "timestamp"]
        for field in required_fields:
            if field not in raw_data or raw_data[field] is None:
                logger.warning(f"Discarding record: Missing required field '{field}'. Record: {raw_data}")
                return None

        # 2. Extract and cast types
        ticker = str(raw_data["ticker"]).strip().upper()
        
        try:
            price = float(raw_data["price"])
            volume = int(raw_data["volume"])
        except (ValueError, TypeError) as e:
            logger.warning(f"Discarding record: Invalid numeric type for ticker {ticker}. Error: {e}")
            return None

        # 3. Validate logical limits (no negative prices or volumes)
        if price <= 0.0:
            logger.warning(f"Discarding record: Price is non-positive for {ticker} ({price}).")
            return None
        
        if volume < 0:
            logger.warning(f"Discarding record: Negative volume for {ticker} ({volume}).")
            return None

        # 4. Standardize timestamps (ensure tz-aware UTC)
        ts = raw_data["timestamp"]
        if isinstance(ts, str):
            try:
                # Handle isoformat string conversion
                ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except ValueError:
                logger.warning(f"Discarding record: Invalid timestamp format string '{ts}'.")
                return None
                
        if not isinstance(ts, datetime):
            logger.warning(f"Discarding record: Timestamp is not a datetime object.")
            return None

        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        else:
            ts = ts.astimezone(timezone.utc)

        # 5. Extract optional fields
        percent_change = raw_data.get("percent_change")
        if percent_change is not None:
            try:
                percent_change = round(float(percent_change), 2)
            except (ValueError, TypeError):
                percent_change = 0.0
        else:
            percent_change = 0.0

        return {
            "ticker": ticker,
            "price": round(price, 2),
            "volume": volume,
            "timestamp": ts,
            "percent_change": percent_change
        }

    except Exception as e:
        logger.error(f"Unexpected error cleaning record {raw_data}: {e}")
        return None
