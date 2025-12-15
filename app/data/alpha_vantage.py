import os
import requests
from typing import Dict, List, Any
import pandas as pd
from app.data.base import MarketDataProvider


class AlphaVantageProvider(MarketDataProvider):
    """
    Provider for Macro Economics (The Macro Scope).
    Yields, CPI, GDP.
    """

    def __init__(self):
        self.api_key = os.getenv("ALPHAVANTAGE_API_KEY")
        self.base_url = "https://www.alphavantage.co/query"

    def get_bars(
        self, symbol: str, timeframe: str = "1D", limit: int = 100
    ) -> pd.DataFrame:
        return pd.DataFrame()

    def get_current_price(self, symbol: str) -> float:
        return 0.0

    def get_account_summary(self) -> Dict[str, Any]:
        return {}

    def get_news(self, symbol: str, limit: int = 5) -> List[Dict[str, Any]]:
        return []

    def get_treasury_yield(self, maturity: str = "10year") -> float:
        """
        Fetches Treasury Yield.
        """
        params = {
            "function": "TREASURY_YIELD",
            "interval": "daily",
            "maturity": maturity,
            "apikey": self.api_key,
        }
        try:
            resp = requests.get(self.base_url, params=params)
            data = resp.json()
            # Parse time series
            if "data" in data and len(data["data"]) > 0:
                # Latest value
                latest = data["data"][0]
                return float(latest["value"])
            return 4.0  # Fallback 4%
        except Exception as e:
            print(f"AlphaVantage Error: {e}")
            return 4.0
