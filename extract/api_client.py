import time
import random
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import yfinance as yf
import requests

from config.settings import settings

logger = logging.getLogger(__name__)


class GBMStockSimulator:
    """
    Simulates stock price movements using Geometric Brownian Motion (GBM).
    Formula: S_t = S_{t-1} * exp((mu - 0.5 * sigma^2) * dt + sigma * W_t)
    Also simulates realistic trading volumes and periodic market shocks/anomalies.
    """
    def __init__(self, tickers: list[str]):
        # Base prices representing realistic values for prominent NSE (Kenya) stocks (in KES)
        base_prices = {
            "SCOM.KE": 16.50,
            "EQTY.KE": 43.50,
            "KCB.KE": 31.20,
            "COOP.KE": 12.80,
            "EABL.KE": 135.00,
            "ABSA.KE": 13.10,
            "BAT.KE": 410.00,
            "NCBA.KE": 42.50,
            "SBIC.KE": 115.00,
            "KEGN.KE": 2.25
        }
        
        # Track active price, daily open price, and rolling volume parameters
        self.prices: Dict[str, float] = {t: base_prices.get(t, 1000.0) for t in tickers}
        self.open_prices: Dict[str, float] = {t: base_prices.get(t, 1000.0) for t in tickers}
        self.tickers = tickers
        
        # Ingestion params (dt is fraction of daily trading seconds, approx 5s/24300s of market day)
        self.dt = 5.0 / 24300.0
        
        # Simulated drift (annualized return) and volatility for GBM
        self.mu = 0.05       # 5% drift
        self.sigma = 0.15    # 15% volatility
        
        # Average volume to scale random volume generation
        self.base_volume = {
            t: random.randint(10000, 50000) for t in tickers
        }

    def generate_next_tick(self, ticker: str) -> Dict[str, Any]:
        """
        Simulate the next stock tick: price, volume, timestamp, percent_change
        """
        current_price = self.prices[ticker]
        open_price = self.open_prices[ticker]
        
        # 1. Geometric Brownian Motion calculation
        epsilon = random.normalvariate(0.0, 1.0)
        exponent = (self.mu - 0.5 * self.sigma ** 2) * self.dt + self.sigma * (self.dt ** 0.5) * epsilon
        next_price = current_price * float(random.choice([1.0, 1.0]) * (2.71828 ** exponent))
        
        # 2. Inject periodic shocks (e.g., flash crash or earnings report anomaly)
        # 0.5% chance of a severe drop (> 5%)
        # 0.5% chance of a price surge (> 4%)
        shock_roll = random.random()
        is_shock = False
        shock_type = None
        
        if shock_roll < 0.005:  # Flash crash / price drop > 5%
            next_price *= random.uniform(0.93, 0.945)
            is_shock = True
            shock_type = "price_drop"
            logger.warning(f"Simulating a price drop shock for {ticker}!")
        elif shock_roll > 0.995:  # Price shock surge (volatility)
            next_price *= random.uniform(1.04, 1.06)
            is_shock = True
            shock_type = "price_surge"
            logger.info(f"Simulating a price surge shock for {ticker}!")
            
        # 3. Simulate volume
        avg_vol = self.base_volume[ticker]
        next_volume = int(random.lognormvariate(0.0, 0.5) * (avg_vol / 100)) # typical volume
        
        # 0.8% chance of a volume anomaly (volume spike)
        if random.random() < 0.008:
            next_volume = int(avg_vol * random.uniform(4.0, 8.0))
            is_shock = True
            shock_type = "volume_spike" if not shock_type else f"{shock_type}+volume_spike"
            logger.warning(f"Simulating a volume spike for {ticker}!")

        # Keep track of updated price
        self.prices[ticker] = round(next_price, 2)
        
        # Percent change from daily open
        pct_change = ((self.prices[ticker] - open_price) / open_price) * 100.0
        
        # If price has changed drastically from base, reset open price at random interval
        if random.random() < 0.001:
            self.open_prices[ticker] = self.prices[ticker]

        return {
            "ticker": ticker,
            "price": self.prices[ticker],
            "volume": next_volume,
            "timestamp": datetime.now(timezone.utc),
            "percent_change": round(pct_change, 2),
            "simulated": True,
            "shock_type": shock_type
        }


class APIClient:
    """
    Fintech-grade API client containing yfinance wrappers and simulation fallback mechanisms.
    """
    def __init__(self, tickers: list[str] = settings.TICKERS, simulation_mode: bool = settings.SIMULATION_MODE):
        self.tickers = tickers
        self.simulation_mode = simulation_mode
        self.simulator = GBMStockSimulator(tickers)
        logger.info(
            f"API Client initialized. Mode: {'SIMULATION' if self.simulation_mode else 'LIVE (yfinance)'}"
        )

    def fetch_stock_tick(self, ticker: str, max_retries: int = 3, backoff_factor: float = 1.5) -> Optional[Dict[str, Any]]:
        """
        Fetches the latest tick data for a stock ticker.
        If SIMULATION_MODE is enabled or market is closed/rate limits hit, it uses the GBM Simulator.
        """
        if self.simulation_mode:
            return self.simulator.generate_next_tick(ticker)

        # Live yfinance extraction with robust retry and backoff mechanisms
        retries = 0
        while retries < max_retries:
            try:
                # yfinance fetch
                ticker_obj = yf.Ticker(ticker)
                
                # Get info (uses fast_info which is quicker and avoids HTML parsing errors)
                info = ticker_obj.fast_info
                
                price = info.get("last_price")
                volume = info.get("last_volume")
                
                # Check for invalid returns (common if API is blocked or rate limited)
                if price is None or price <= 0:
                    raise ValueError(f"Invalid last_price fetched for {ticker}: {price}")
                
                # Default volume check
                if volume is None or volume <= 0:
                    volume = random.randint(1000, 5000) # Fallback volume

                # Compute change from previous close
                prev_close = info.get("previous_close")
                pct_change = 0.0
                if prev_close and prev_close > 0:
                    pct_change = ((price - prev_close) / prev_close) * 100.0

                return {
                    "ticker": ticker,
                    "price": round(price, 2),
                    "volume": int(volume),
                    "timestamp": datetime.now(timezone.utc),
                    "percent_change": round(pct_change, 2),
                    "simulated": False,
                    "shock_type": None
                }

            except Exception as e:
                retries += 1
                wait_time = backoff_factor ** retries
                logger.warning(
                    f"Attempt {retries}/{max_retries} to fetch live data for {ticker} failed: {e}. "
                    f"Retrying in {wait_time:.1f}s..."
                )
                time.sleep(wait_time)

        # Fallback to simulation engine if API fails
        logger.warning(f"All retries failed to fetch live data for {ticker}. Falling back to simulation engine.")
        return self.simulator.generate_next_tick(ticker)
