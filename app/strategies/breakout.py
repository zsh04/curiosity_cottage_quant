import pandas as pd

from app.strategies.base import BaseStrategy
from app.lib.memory import FractalMemory


class FractalBreakoutStrategy(BaseStrategy):
    """Donchian Channel breakouts on fracdiff-stationary prices.

    Combines López de Prado's fracdiff with turtle trading breakouts.
    **Best**: Trending markets | **Worst**: Choppy (false breakouts)
    """

    def __init__(self, window: int = 20):
        """
        Initialize Fractal Breakout Strategy.

        Uses fractional differentiation to achieve stationarity,
        then detects breakouts against rolling extrema.

        **Constants** (Donchian Channel Standard):

        1. **window = 20** (Breakout Detection Window):
           - Theory: Donchian Channel (turtle trading) standard
           - Origin: Richard Dennis & William Eckhardt (1980s)
           - Chosen: 20 days = Monthly breakout detection
           - Physical meaning: Time to establish support/resistance
           - Rule: Breakout if current > max(past 20) or < min(past 20)
           - Alternative: 10 (faster), 55 (slower Donchian standard)
           - Historical note: Original Turtles used 20/55 dual system
           - Empirical: 20 days optimal for trend-following (backtested)
           - Reference: Covel (2007) "Complete TurtleTrader"

        2. **window * 2 = 40** (Minimum Data Requirement):
           - Rationale: Need sufficient data for fracdiff + rolling window
           - Fracdiff drops initial points (transient removal)
           - Rolling window needs 'window' more points
           - Safety factor: 2x window ensures statistical stability
        """
        super().__init__()
        self.window = window

    @property
    def name(self) -> str:
        return "FractalBreakout_V1"

    def calculate_signal(self, market_data: pd.DataFrame) -> float:
        with self.tracer.start_as_current_span("calculate_signal") as span:
            # Need enough data for fracdiff and rolling window
            # FracDiff drops data, rolling window needs more.
            # safe lower bound check: window * 3 or similar.
            if len(market_data) < self.window * 2:
                return 0.0

            series = market_data["close"]

            # 1. Transform to Stationary Series
            # find_optimal_d returns (d, transformed_series_list)
            # We explicitly want the transformed series as pd.Series
            try:
                d, stationary_list = FractalMemory.find_optimal_d(series.tolist())
                stationary_series = pd.Series(stationary_list, index=series.index)
                span.set_attribute("fractal.d", d)
            except Exception as e:
                span.record_exception(e)
                print(f"Error in FracDiff: {e}")
                return 0.0

            if stationary_series.empty or len(stationary_series) < self.window:
                return 0.0

            # 2. Calculate Rolling Max/Min (Shifted by 1 to represent PRIOR bars)
            # We want to know if CURRENT value broke the range of the PAST N bars.
            rolling_max = stationary_series.rolling(window=self.window).max().shift(1)
            rolling_min = stationary_series.rolling(window=self.window).min().shift(1)

            current_val = stationary_series.iloc[-1]
            prior_max = rolling_max.iloc[-1]
            prior_min = rolling_min.iloc[-1]

            span.set_attribute("fractal.stat_val", current_val)
            span.set_attribute("fractal.prior_max", prior_max)
            span.set_attribute("fractal.prior_min", prior_min)

            signal = 0.0

            # Check for NaN (rolling window start)
            if pd.isna(prior_max) or pd.isna(prior_min):
                return 0.0

            if current_val > prior_max:
                signal = 1.0
            elif current_val < prior_min:
                signal = -1.0

            span.set_attribute("fractal.signal", signal)

            return signal
