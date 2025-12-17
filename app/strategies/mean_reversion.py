import pandas as pd
from app.strategies.base import BaseStrategy


class BollingerReversionStrategy(BaseStrategy):
    """
    Mean Reversion Strategy using Bollinger Bands.
    "BollingerReversion_V1"

    Logic:
    - Buy if Price < Lower Band
    - Sell if Price > Upper Band
    - Neutral otherwise
    """

    def __init__(self, window: int = 20, num_std: float = 2.0):
        super().__init__()
        self.window = window
        self.num_std = num_std

    @property
    def name(self) -> str:
        return "BollingerReversion_V1"

    def calculate_signal(self, market_data: pd.DataFrame) -> float:
        with self.tracer.start_as_current_span("calculate_signal") as span:
            if len(market_data) < self.window:
                return 0.0

            # Calculate Bands
            series = market_data["close"]
            rolling_mean = series.rolling(window=self.window).mean()
            rolling_std = series.rolling(window=self.window).std()

            upper_band = rolling_mean + (rolling_std * self.num_std)
            lower_band = rolling_mean - (rolling_std * self.num_std)

            current_price = series.iloc[-1]
            current_upper = upper_band.iloc[-1]
            current_lower = lower_band.iloc[-1]

            span.set_attribute("bb.price", current_price)
            span.set_attribute("bb.upper", current_upper)
            span.set_attribute("bb.lower", current_lower)

            signal = 0.0
            if current_price < current_lower:
                signal = 1.0  # Buy Reversion
            elif current_price > current_upper:
                signal = -1.0  # Sell Reversion

            span.set_attribute("bb.signal", signal)

            return signal
