import os
import requests
import pandas as pd
from typing import Dict, List, Any
from app.data.base import MarketDataProvider


class FinnhubProvider(MarketDataProvider):
    """
    Provider for News and Sentiment (The Analyst's Eyes).
    """

    def __init__(self):
        self.api_key = os.getenv("FINNHUB_API_KEY")
        self.base_url = "https://finnhub.io/api/v1"

    def get_bars(
        self, symbol: str, timeframe: str = "1D", limit: int = 100
    ) -> pd.DataFrame:
        return pd.DataFrame()  # Not primary for bars

    def get_current_price(self, symbol: str) -> float:
        return 0.0  # Not primary

    def get_account_summary(self) -> Dict[str, Any]:
        return {}  # Not applicable

    def get_news(self, symbol: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Fetches company news.
        """
        # Date range: last 3 days
        from datetime import datetime, timedelta

        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")

        url = f"{self.base_url}/company-news?symbol={symbol}&from={start_date}&to={end_date}&token={self.api_key}"

        try:
            resp = requests.get(url)
            data = resp.json()

            formatted = []
            for item in data[:limit]:
                formatted.append(
                    {
                        "headline": item.get("headline"),
                        "summary": item.get("summary"),
                        "url": item.get("url"),
                        "source": item.get("source"),
                        "published_at": item.get("datetime"),
                    }
                )
            return formatted
        except Exception as e:
            print(f"Finnhub Error: {e}")
            return []

    def get_general_news(self, category: str = "general") -> List[Dict[str, Any]]:
        """
        Specific to Finnhub: Get general market news.
        """
        url = f"{self.base_url}/news?category={category}&token={self.api_key}"
        try:
            resp = requests.get(url)
            data = resp.json()
            # ... formatting similar to above ...
            return data[:5]
        except Exception as e:
            print(f"Finnhub General News Error: {e}")
            return []
