import os
import requests
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class TwelveDataAdapter:
    """Twelve Data API adapter - real-time prices and time series.

    **Intervals**: 1min/5min/15min/30min/1h/1day/1week/1month
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("TWELVEDATA_API_KEY")
        self.base_url = "https://api.twelvedata.com"

    def get_price(self, symbol: str) -> float:
        """
        Get real-time price.
        """
        if not self.api_key:
            return 0.0

        url = f"{self.base_url}/price"
        try:
            response = requests.get(
                url, params={"symbol": symbol, "apikey": self.api_key}, timeout=5
            )
            data = response.json()
            # {price: "123.45"}
            if "price" in data:
                return float(data["price"])
            return 0.0
        except Exception as e:
            logger.warning(f"TwelveData Price failed: {e}")
            return 0.0

    def get_time_series(
        self, symbol: str, interval: str = "1day", outputsize: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get time series.
        """
        if not self.api_key:
            return []

        url = f"{self.base_url}/time_series"
        params = {
            "symbol": symbol,
            "interval": interval,
            "outputsize": outputsize,
            "apikey": self.api_key,
        }

        try:
            response = requests.get(url, params=params, timeout=5)
            data = response.json()
            if "values" in data:
                # Returns list of {datetime, open, high, low, close, volume}
                # Sort is descending by default
                return sorted(data["values"], key=lambda x: x["datetime"])
            return []
        except Exception as e:
            logger.warning(f"TwelveData Series failed: {e}")
            return []
