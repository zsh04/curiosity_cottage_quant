from abc import ABC, abstractmethod
import pandas as pd
from opentelemetry import trace


class BaseStrategy(ABC):
    """Abstract base class for all Council strategies - enforces signal interface.

    All trading strategies inherit from this class and implement the Strategy Pattern.
    The Council (ensemble of strategies) votes on each trading decision, with Boyd
    aggregating and weighting their signals.

    **Required Methods**:
    - `name`: Unique strategy identifier (property)
    - `calculate_signal`: Core signal generation logic

    **Signal Convention**:
    - Range: [-1.0, 1.0]
    - +1.0: Strong buy
    -  0.0: Neutral/Hold
    - -1.0: Strong sell

    **Integration**:
    1. Implement this ABC
    2. Register in `STRATEGY_REGISTRY` (strategies/__init__.py)
    3. Add to Boyd's Council via `ENABLED_STRATEGIES`

    Attributes:
        tracer: OpenTelemetry tracer for this strategy

    Example:
        >>> class MyStrategy(BaseStrategy):
        ...     @property
        ...     def name(self): return "my_strategy"
        ...     def calculate_signal(self, data):
        ...         return 0.75  # Bullish signal
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
