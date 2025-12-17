import os
import requests
import logging
import time
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class FinnhubAdapter:
    """
    Adapter for Finnhub API.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("FINNHUB_API_KEY")
        self.base_url = "https://finnhub.io/api/v1"

    def get_quote(self, symbol: str) -> Dict[str, Any]:
        """
        Get real-time quote.
        """
        if not self.api_key:
            return {}

        headers = {"X-Finnhub-Token": self.api_key}
        url = f"{self.base_url}/quote"

        try:
            response = requests.get(
                url, params={"symbol": symbol}, headers=headers, timeout=5
            )
            data = response.json()
            # Returns {c: price, d: change, dp: percent, h: high, l: low, o: open, pc: prev_close}
            if "c" in data and data["c"] > 0:
                return {
                    "symbol": symbol,
                    "price": float(data["c"]),
                    "high": float(data["h"]),
                    "low": float(data["l"]),
                    "open": float(data["o"]),
                }
            return {}
        except Exception as e:
            logger.warning(f"Finnhub Quote failed: {e}")
            return {}

    def get_candles(
        self, symbol: str, resolution: str = "D", count: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get stock candles.
        resolution: 1, 5, 15, 30, 60, D, W, M
        """
        if not self.api_key:
            return []

        headers = {"X-Finnhub-Token": self.api_key}
        url = f"{self.base_url}/stock/candle"
        to_time = int(time.time())
        from_time = to_time - (count * 86400 * 2)  # Rough buffer

        params = {
            "symbol": symbol,
            "resolution": resolution,
            "from": from_time,
            "to": to_time,
        }

        try:
            response = requests.get(url, params=params, headers=headers, timeout=5)
            data = response.json()
            # Returns {c: [], h: [], ... s: "ok"}
            if data.get("s") == "ok":
                candles = []
                length = len(data["c"])
                for i in range(length):
                    candles.append(
                        {
                            "close": data["c"][i],
                            "high": data["h"][i],
                            "low": data["l"][i],
                            "open": data["o"][i],
                            "volume": data["v"][i],
                            "time": data["t"][i],
                        }
                    )
                return candles[-count:]
            return []
        except Exception as e:
            logger.warning(f"Finnhub Candles failed: {e}")
            return []
