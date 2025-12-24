import os
import requests
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class AlphaVantageAdapter:
    """AlphaVantage API adapter - global quotes and daily adjusted series.

    **Rate Limit**: 5 req/min, 500/day (free tier)
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ALPHAVANTAGE_API_KEY")
        self.base_url = "https://www.alphavantage.co/query"

    def get_global_quote(self, symbol: str) -> Dict[str, Any]:
        """
        Get real-time price snapshot.
        """
        if not self.api_key:
            return {}

        params = {"function": "GLOBAL_QUOTE", "symbol": symbol, "apikey": self.api_key}

        try:
            response = requests.get(self.base_url, params=params, timeout=5)
            data = response.json()

            # AV returns dict like {"Global Quote": {"05. price": "123.45"}}
            if "Global Quote" in data:
                quote = data["Global Quote"]
                return {
                    "symbol": quote.get("01. symbol"),
                    "price": float(quote.get("05. price", 0.0)),
                    "volume": int(quote.get("06. volume", 0)),
                    "change_percent": quote.get("10. change percent"),
                }
            return {}
        except Exception as e:
            logger.warning(f"AlphaVantage Quote failed: {e}")
            return {}

    def get_daily_series(self, symbol: str) -> Dict[str, Any]:
        """
        Get Daily Time Series.
        """
        if not self.api_key:
            return {}

        params = {
            "function": "TIME_SERIES_DAILY_ADJUSTED",
            "symbol": symbol,
            "apikey": self.api_key,
        }

        try:
            response = requests.get(self.base_url, params=params, timeout=5)
            data = response.json()
            if "Time Series (Daily)" in data:
                return data["Time Series (Daily)"]
            return {}
        except Exception as e:
            logger.warning(f"AlphaVantage Daily failed: {e}")
            return {}
