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
        """
        Initialize Bollinger Band Mean Reversion Strategy.

        **Constants** (Statistical Justification):

        1. **window = 20** (Rolling Window):
           - Theory: Industry standard for intermediate-term mean reversion
           - Origin: John Bollinger (1980s) empirical testing
           - Chosen: 20 days ≈ 1 trading month
           - Physical meaning: Typical mean reversion cycle time
           - Alternative: 10 (short-term), 50 (long-term)
           - Empirical: Most liquid for options (monthly expiry)
           - Reference: Bollinger (2001) "Bollinger on Bollinger Bands"

        2. **num_std = 2.0** (Standard Deviation Multiplier):
           - Theory: 2σ = 95% confidence interval (Gaussian assumption)
           - Statistical basis: P(|X| > 2σ) ≈ 0.05 (rare event)
           - Chosen: 2.0 = Trade-off between frequency and significance
           - If 1.0σ: Too frequent (68% capture, many false signals)
           - If 3.0σ: Too rare (99.7% capture, miss opportunities)
           - Empirical: 2.0σ optimal for stock indices (SPY, QQQ)
           - Market note: Financial returns are fat-tailed (not Gaussian)
           - Empirical adjustment: May need 2.5σ for crypto/volatility
           - Reference: Achelis (2000) "Technical Analysis from A to Z"
        """
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
