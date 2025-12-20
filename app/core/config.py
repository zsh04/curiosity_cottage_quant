"""
Pydantic Settings (12-Factor App).
"""

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore"
    )

    # --- App Info ---
    PROJECT_NAME: str = "Curiosity Cottage Quant Engine"
    VERSION: str = "0.1.0-alpha"
    DEBUG: bool = False

    # --- Database ---
    # Default to Localhost for dev convenience
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/cc_quant"

    # --- Brokerage (Alpaca) ---
    LIVE_TRADING_ENABLED: bool = False  # Safety Switch
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

    # --- Data Feed Config ---
    ALPACA_DATA_FEED: str = "iex"
    WATCHLIST: list[str] = ["SPY", "NVDA", "AAPL"]

    # --- LLM Configuration ---
    # Default: Localhost (typical for running run.py)
    # Docker Override: http://cc_brain:11434 (set in docker-compose)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    LLM_MODEL: str = "gemma2:9b"
    OLLAMA_MODEL: str = "gemma2:9b"

    # --- Reasoning Engine ---
    # REASONING_MODE and GOOGLE_API_KEY removed (Rolled Back)

    # --- Legacy Microservices Removed ---
    # Chronos and FinBERT are now local libraries running on Metal GPU
    # No network calls required

    # --- Telemetry ---
    # Defaults to empty/disabled if not provided
    # --- Telemetry ---
    # Defaults to empty/disabled if not provided
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://localhost:4318"  # Default Metal
    OTEL_EXPORTER_OTLP_HEADERS: str = ""
    IS_DOCKER: bool = False

    @field_validator("OTEL_EXPORTER_OTLP_ENDPOINT", mode="before")
    @classmethod
    def set_otel_endpoint(cls, v: str, info):
        # If user provides a value in ENV, allow it (Pydantic does this by default if we return v)
        # But we want to implement the logic: If Docker -> cc_pulse, else -> localhost
        # This is tricky because `IS_DOCKER` is also a field.
        # Simpler approach: Check os.environ or rely on the fact that if IS_DOCKER=true is set in env, we might want to override.
        # Actually, the requirement is "If running in Docker (check env IS_DOCKER), use cc_pulse".

        import os

        is_docker = os.getenv("IS_DOCKER", "false").lower() == "true"

        if not v:  # If not set in ENV
            if is_docker:
                return "http://cc_pulse:4318"
            return "http://localhost:4318"
        return v

    OTEL_EXPORTER_OTLP_HEADERS: str = ""


settings = Settings()

# Governance: Log Telemetry Connection
import logging

logger = logging.getLogger("CC_INIT")
# Basic console print if logger not configured yet
print(f"📡 Telemetry connected to {settings.OTEL_EXPORTER_OTLP_ENDPOINT}")
