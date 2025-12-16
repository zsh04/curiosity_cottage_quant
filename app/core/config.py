"""
Pydantic Settings (12-Factor App).
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- App Info ---
    PROJECT_NAME: str = "Curiosity Cottage Quant Engine"
    VERSION: str = "0.1.0-alpha"
    debug: bool = False

    # --- Database ---
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/cc_quant"

    # --- Brokerage (Alpaca) ---
    LIVE_TRADING_ENABLED: bool = (
        False  # Safety Switch (True = Live/Paper API, False = Dry Run)
    )
    ALPACA_API_KEY: str = ""
    ALPACA_SECRET_KEY: str = ""
    ALPACA_ENDPOINT: str = "https://paper-api.alpaca.markets"  # Default to paper

    # --- LLM ---
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    LLM_MODEL: str = "llama3"

    # --- Microservices ---
    CHRONOS_URL: str = "http://cc_chronos:8002"
    FINBERT_URL: str = "http://cc_finbert:8001"

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore"
    )


settings = Settings()
