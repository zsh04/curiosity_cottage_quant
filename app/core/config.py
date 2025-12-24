"""Application configuration via Pydantic Settings (12-Factor App compliance).

Centralized environment-driven configuration for:
- Database URLs (Postgres, QuestDB, LanceDB)
- API keys (Alpaca, market data providers)
- Model parameters (forecasting, backtesting)
- Telemetry endpoints (OpenTelemetry)
- Risk limits and trading flags

All settings can be overridden via environment variables or .env file.
Follows 12-factor app methodology for configuration management.
"""

from typing import List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import os


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore"
    )

    # --- App Info ---
    PROJECT_NAME: str = "Curiosity Cottage Quant Engine"
    VERSION: str = "0.11.0"
    ENV: str = "DEV"  # DEV, PROD
    DEBUG: bool = False

    # --- Database ---
    DATABASE_URL: str = (
        "postgresql://user:password@localhost:5432/quant"  # Default dev URL
    )
    QUESTDB_URL: str = "http://localhost:9000"
    QUESTDB_ILP_HOST: str = "localhost"
    QUESTDB_ILP_PORT: int = 9009

    # --- LanceDB (Vector Memory) ---
    LANCEDB_URI: str = "data/lancedb"
    RAF_WINDOW_SIZE: int = 64
    RAF_TOP_K: int = 5

    # --- Forecasting (Chronos-Bolt) ---
    FORECAST_BATCH_SIZE: int = 32
    FORECAST_HORIZON: int = 12
    FORECAST_NUM_SAMPLES: int = 100  # High Res

    # --- Brokerage (Alpaca) ---
    LIVE_TRADING_ENABLED: bool = False
    ALPACA_API_KEY: str = ""
    ALPACA_API_SECRET: str = ""
    ALPACA_ENDPOINT: str = Field(
        default="https://paper-api.alpaca.markets", validation_alias="ALPACA_BASE_URL"
    )
    ALPACA_DATA_FEED: str = "iex"

    # --- Market Data Keys ---
    ALPHAVANTAGE_API_KEY: str = ""
    FINNHUB_API_KEY: str = ""
    TWELVEDATA_API_KEY: str = ""
    MARKETSTACK_API_KEY: str = ""
    TIINGO_API_KEY: str = ""

    # FRED (Federal Reserve Economic Data) - For Treasury yields
    # Get free API key: https://fred.stlouisfed.org/docs/api/api_key.html
    FRED_API_KEY: str = ""

    # --- Config ---
    # Dynamic Watchlist - loaded from config/watchlist.txt
    _watchlist_cache: list[str] | None = None

    @property
    def WATCHLIST(self) -> list[str]:
        """Load watchlist dynamically from config/watchlist.txt"""
        if self._watchlist_cache is not None:
            return self._watchlist_cache

        import logging
        from pathlib import Path

        default = ["SPY", "NVDA", "AAPL", "QQQ", "IWM", "MSFT", "GOOGL", "AMZN"]

        try:
            config_file = Path("config/watchlist.txt")
            if not config_file.exists():
                config_file = (
                    Path(__file__).parent.parent.parent / "config" / "watchlist.txt"
                )

            if config_file.exists():
                with open(config_file, "r") as f:
                    symbols = [
                        line.strip().upper()
                        for line in f
                        if line.strip() and not line.strip().startswith("#")
                    ]
                if symbols:
                    self._watchlist_cache = symbols
                    return symbols
        except Exception as e:
            logging.warning(f"Failed to load watchlist: {e}")

        self._watchlist_cache = default
        return default

    # --- LLM Configuration ---
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    LLM_MODEL: str = "gemma2:9b"
    OLLAMA_MODEL: str = "gemma2:9b"

    # --- Telemetry ---
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://localhost:4318"
    OTEL_EXPORTER_OTLP_HEADERS: str = ""
    IS_DOCKER: bool = False

    @field_validator("OTEL_EXPORTER_OTLP_ENDPOINT", mode="before")
    @classmethod
    def set_otel_endpoint(cls, v: str, info):
        is_docker = os.getenv("IS_DOCKER", "false").lower() == "true"
        if not v:
            return "http://cc_pulse:4318" if is_docker else "http://localhost:4318"
        return v


settings = Settings()

import logging

print(f"📡 Telemetry connected to {settings.OTEL_EXPORTER_OTLP_ENDPOINT}")
