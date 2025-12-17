from abc import ABC, abstractmethod
import pandas as pd
from opentelemetry import trace


class BaseStrategy(ABC):
    """
    Abstract Base Class for all trading strategies.
    Ensures a consistent interface for signal generation.
    """

    def __init__(self):
        self.tracer = trace.get_tracer(f"strategy.{self.name}")

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Unique identifier for the strategy.
        """
        pass

    @abstractmethod
    def calculate_signal(self, market_data: pd.DataFrame) -> float:
        """
        Calculates the trading signal based on provided market data.

        Args:
            market_data (pd.DataFrame): DataFrame containing at least 'close' price
                                        and a DatetimeIndex.

        Returns:
            float: Signal strength between -1.0 (Strong Sell) and 1.0 (Strong Buy).
                   0.0 indicates Neutral/Hold.
        """
        pass
