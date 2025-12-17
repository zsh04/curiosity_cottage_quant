import os
import requests
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class MarketStackAdapter:
    """
    Adapter for MarketStack API.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("MARKETSTACK_API_KEY")
        self.base_url = "http://api.marketstack.com/v1"

    def get_eod_latest(self, symbol: str) -> Dict[str, Any]:
        """
        Get latest End-of-Day data.
        """
        if not self.api_key:
            return {}

        url = f"{self.base_url}/eod/latest"
        params = {"access_key": self.api_key, "symbols": symbol}

        try:
            response = requests.get(url, params=params, timeout=5)
            data = response.json()
            if "data" in data and len(data["data"]) > 0:
                item = data["data"][0]
                return {
                    "symbol": item.get("symbol"),
                    "date": item.get("date"),
                    "close": item.get("close"),
                    "volume": item.get("volume"),
                }
            return {}
        except Exception as e:
            logger.warning(f"MarketStack EOD failed: {e}")
            return {}
