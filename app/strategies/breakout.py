import pandas as pd
import numpy as np
from app.strategies.base import BaseStrategy
from app.lib.memory import FractalMemory


class FractalBreakoutStrategy(BaseStrategy):
    """
    Fractal Breakout Strategy.
    "FractalBreakout_V1"

    Logic:
    - Dynamically fractionally differentiate the price series to stationarity (find min d).
    - Detect breakout of the Stationary Series against its 20-day rolling Max/Min.
    - Signal:
      - Stationary Value > Prior 20-Bar Max -> Buy (1.0)
      - Stationary Value < Prior 20-Bar Min -> Sell (-1.0)
    """

    def __init__(self, window: int = 20):
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
