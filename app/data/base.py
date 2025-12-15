from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
import pandas as pd


class MarketDataProvider(ABC):
    """
    Abstract Base Class for all market data providers.
    Enforces a unified interface for the DataAggregator.
    """

    @abstractmethod
    def get_bars(
        self, symbol: str, timeframe: str = "1D", limit: int = 100
    ) -> pd.DataFrame:
        """
        Fetches historical OHLCV data.
        Returns DataFrame with columns: [open, high, low, close, volume] and DatetimeIndex.
        """
        pass

    @abstractmethod
    def get_current_price(self, symbol: str) -> float:
        """
        Fetches the current real-time price.
        """
        pass

    @abstractmethod
    def get_account_summary(self) -> Dict[str, Any]:
        """
        Fetches account equity and usage.
        """
        pass

    @abstractmethod
    def get_news(self, symbol: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Fetches news headlines.
        """
        pass
