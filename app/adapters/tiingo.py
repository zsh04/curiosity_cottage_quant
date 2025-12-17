import requests
import os
from typing import List, Optional, Dict, Any


class TiingoAdapter:
    """
    Adapter for Tiingo API (News & Sentiment).
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("TIINGO_API_KEY")
        if not self.api_key:
            raise ValueError("Tiingo API Key (TIINGO_API_KEY) must be set.")

        self.base_url = "https://api.tiingo.com/tiingo"

    def fetch_news(self, tickers: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Fetch news articles for given tickers from Tiingo.
        """
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Token {self.api_key}",
        }

        url = f"{self.base_url}/news"
        params: Dict[str, Any] = {"tickers": tickers, "limit": limit}

        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            return response.json()
        else:
            print(
                f"Error fetching Tiingo news: {response.status_code} - {response.text}"
            )
            return []

    def get_latest_price(self, symbol: str) -> float:
        """
        Fetch real-time price from Tiingo IEX feed.
        """
        url = f"{self.base_url.replace('/tiingo', '/iex')}/{symbol}"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Token {self.api_key}",
        }

        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    return float(data[0].get("tngoLast", data[0].get("last", 0.0)))
            return 0.0
        except Exception as e:
            print(f"Tiingo Price Fetch Error: {e}")
            return 0.0

    def get_historical_data(self, symbol: str, start_date: str) -> List[Dict[str, Any]]:
        """
        Fetch EOD historical data.
        """
        url = f"{self.base_url}/daily/{symbol}/prices"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Token {self.api_key}",
        }
        params = {"startDate": start_date, "columns": "date,open,high,low,close,volume"}

        try:
            response = requests.get(url, headers=headers, params=params)
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            print(f"Tiingo History Fetch Error: {e}")
            return []
