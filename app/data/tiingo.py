import os
import requests
import pandas as pd
from typing import Dict, List, Any
from app.data.base import MarketDataProvider


class TiingoProvider(MarketDataProvider):
    """
    Tiingo implementation for Market Data (Stocks, Crypto, News).
    Uses IEX for realtime and End-of-Day for history.
    """

    def __init__(self):
        self.api_key = os.getenv("TIINGO_API_KEY")
        self.base_url = "https://api.tiingo.com"
        if not self.api_key:
            print("Warning: TIINGO_API_KEY not found.")

    def _get_headers(self):
        return {
            "Content-Type": "application/json",
            "Authorization": f"Token {self.api_key}",
        }

    def get_bars(
        self, symbol: str, timeframe: str = "1D", limit: int = 100
    ) -> pd.DataFrame:
        """
        Fetches historical data.
        Tiingo primarily does EOD for free plans via /tiingo/daily/{ticker}/prices.
        For intraday (IEX), it's /iex/{ticker}/prices.
        """
        # Defaulting to EOD for 1D, IEX for intraday if needed
        if timeframe == "1D":
            endpoint = f"/tiingo/daily/{symbol}/prices"
            # Daily endpoint defaults to daily freq.
            # sort is usually not needed or handled by start date.
            params = {
                "startDate": (
                    pd.Timestamp.now() - pd.Timedelta(days=limit * 2)
                ).strftime("%Y-%m-%d"),
                "sort": "date",
            }
        else:
            # Tiingo IEX Intraday
            endpoint = f"/iex/{symbol}/prices"
            params = {
                "resampleFreq": "1min" if timeframe == "1Min" else "1hour",
                "columns": "open,high,low,close,volume",
            }

        url = f"{self.base_url}{endpoint}"
        try:
            # Note: headers are set in _get_headers
            resp = requests.get(url, headers=self._get_headers(), params=params)
            resp.raise_for_status()
            data = resp.json()

            if not data:
                return pd.DataFrame()

            df = pd.DataFrame(data)
            # Tiingo returns 'date', 'open', 'high', 'low', 'close', 'volume', 'adjClose', etc.
            # We standardize to date index

            if "date" in df.columns:
                df["timestamp"] = pd.to_datetime(df["date"])
                df.set_index("timestamp", inplace=True)
                df.sort_index(inplace=True)

            # Select and rename to standard lowercase
            # Tiingo is already mostly lowercase
            if "adjClose" in df.columns:
                # Use adjusted close if available for EOD?
                # Base class usually expects raw or adjusted? Let's use close.
                pass

            return df[["open", "high", "low", "close", "volume"]].tail(limit)

        except Exception as e:
            print(f"Tiingo Error: {e}")
            return pd.DataFrame()

    def get_current_price(self, symbol: str) -> float:
        """
        Uses Tiingo IEX Top of Book for real-time price.
        """
        url = f"{self.base_url}/iex/{symbol}"
        try:
            resp = requests.get(url, headers=self._get_headers())
            resp.raise_for_status()
            data = resp.json()
            # Returns list of 1 dict: [{'ticker': 'AAPL', 'tngoLast': 150.0, ...}]
            if data and len(data) > 0:
                # prefer 'tngoLast' or 'last'
                return float(data[0].get("tngoLast") or data[0].get("last", 0.0))
            return 0.0
        except Exception as e:
            print(f"Tiingo Price Error: {e}")
            return 0.0

    def get_account_summary(self) -> Dict[str, Any]:
        """Tiingo is a data provider, not a broker."""
        return {}

    def get_news(self, symbol: str, limit: int = 5) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/tiingo/news"
        # Documentation: https://www.tiingo.com/documentation/news
        # Headers: {'Content-Type': 'application/json', 'Authorization': 'Token <your_token>'}
        headers = self._get_headers()
        headers["Content-Type"] = "application/json"

        params = {"tickers": symbol, "limit": limit}

        try:
            resp = requests.get(url, headers=headers, params=params)
            resp.raise_for_status()
            articles = resp.json()
            # Standardize
            results = []
            for art in articles:
                results.append(
                    {
                        "headline": art.get("title"),
                        "url": art.get("url"),
                        "summary": art.get("description"),
                        "source": art.get("source", {}).get("name", "Tiingo"),
                    }
                )
            return results
        except Exception as e:
            print(f"Tiingo News Error: {e}")
            return []
