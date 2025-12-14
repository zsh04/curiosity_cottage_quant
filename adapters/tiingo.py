import requests
import os
from typing import List, Dict, Any


class TiingoAdapter:
    """
    Adapter for Tiingo API (News & Sentiment).
    """

    def __init__(self, api_key: str = None):
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
        params = {"tickers": tickers, "limit": limit}

        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            return response.json()
        else:
            print(
                f"Error fetching Tiingo news: {response.status_code} - {response.text}"
            )
            return []
