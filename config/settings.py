import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database Settings
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "postgres")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "finance_db")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", 5432))

    @property
    def database_url(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # Redis Settings
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", 6379))
    REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD", "")

    # ETL Pipeline Settings
    TICKERS: List[str] = [
        "SCOM.KE",
        "EQTY.KE",
        "KCB.KE",
        "COOP.KE",
        "EABL.KE",
        "ABSA.KE",
        "BAT.KE",
        "NCBA.KE",
        "SBIC.KE",
        "KEGN.KE"
    ]
    EXCHANGE: str = os.getenv("EXCHANGE", "Nairobi Securities Exchange (NSE)")
    STREAM_INTERVAL_SECONDS: int = int(os.getenv("STREAM_INTERVAL_SECONDS", 5))
    
    # Mode Settings
    # If True, runs the simulated stock stream using Geometric Brownian Motion.
    # If False, fetches live data using yfinance (though during market closed hours, GBM or latest history is served).
    SIMULATION_MODE: bool = os.getenv("SIMULATION_MODE", "true").lower() == "true"

    # Financial Transformations Configurations
    SMA_FAST_WINDOW_MINUTES: int = 5
    SMA_SLOW_WINDOW_MINUTES: int = 15
    VOLATILITY_WINDOW_SIZE: int = 12  # Number of samples (e.g. 1 min at 5s interval)
    ANOMALY_SD_MULTIPLIER: float = 3.0  # Threshold for anomaly flags
    ALERT_PRICE_DROP_PCT: float = 5.0  # Alert when drops more than this value

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
