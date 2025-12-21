"""
Pydantic Settings (12-Factor App).
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
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/cc_quant"
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

    # --- Config ---
    WATCHLIST: list[str] = [
        "SPY",
        "NVDA",
        "AAPL",
        "QQQ",
        "IWM",
        "MSFT",
        "GOOGL",
        "AMZN",
    ]

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
