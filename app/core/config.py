"""
Pydantic Settings (12-Factor App).
"""

from pydantic import Field
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
    TIINGO_API_KEY: str = ""
    FINNHUB_API_KEY: str = ""

    # --- LLM Configuration ---
    # Default: Localhost (typical for running run.py)
    # Docker Override: http://cc_brain:11434 (set in docker-compose)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    LLM_MODEL: str = "gemma2:9b"
    OLLAMA_MODEL: str = "gemma2:9b"

    # --- Microservices (Defaults = Localhost) ---
    # In Docker, these MUST be overridden via ENV vars to "http://cc_chronos:8000" etc.
    CHRONOS_URL: str = "http://localhost:8002"
    FINBERT_URL: str = "http://localhost:8001"

    # --- Telemetry ---
    # Defaults to empty/disabled if not provided
    OTEL_EXPORTER_OTLP_ENDPOINT: str = ""
    OTEL_EXPORTER_OTLP_HEADERS: str = ""


settings = Settings()
