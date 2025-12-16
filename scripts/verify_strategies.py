import sys
import unittest
from unittest.mock import MagicMock

# 1. Mock dependencies (pandas, numpy, otel, statsmodels)
sys.modules["numpy"] = MagicMock()
sys.modules["pandas"] = MagicMock()
sys.modules["opentelemetry"] = MagicMock()
sys.modules["opentelemetry.trace"] = MagicMock()
sys.modules["statsmodels"] = MagicMock()
sys.modules["statsmodels.tsa"] = MagicMock()
sys.modules["statsmodels.tsa.stattools"] = MagicMock()

# Make sure we can import strategies
# app.strategies... imports pandas/numpy. Mocks above ensure it works.
from app.strategies.mean_reversion import BollingerReversionStrategy
from app.strategies.trend import KalmanMomentumStrategy


class TestStrategiesMocked(unittest.TestCase):
    def setUp(self):
        # We need to setup what numpy.tanh returns, and what pandas DataFrame does.
        self.mock_np = sys.modules["numpy"]
        self.mock_pd = sys.modules["pandas"]

        # Mock tanh to just return the input (identity) for testing simple flow
        # or implement simple logic if we want to verify normalization.
        # Let's verify data flow. Logic depends on numpy.
        # If we mock numpy, we can't easily verify numerical logic unless we implement side_effects.
        self.mock_pd.isna.return_value = False

    def test_trend_strategy_flow(self):
        """Verify Trend Strategy calls Kalman Filter and formats output"""
        strategy = KalmanMomentumStrategy()

        mock_df = MagicMock()
        mock_df.empty = False
        # Mock values property to return a list of prices
        mock_df.__getitem__.return_value.values = [100, 101, 102]

        # We also need to mock KinematicKalmanFilter because it's imported in trend.py
        # BUT, trend.py imports 'KinematicKalmanFilter'.
        # If app.lib.kalman.kinematic imports numpy, we are safe (mocked).
        # We need to mock the KF instance behavior to control 'velocity'

        with unittest.mock.patch(
            "app.strategies.trend.KinematicKalmanFilter"
        ) as MockKF:
            # Setup KF instance
            mock_kf_instance = MockKF.return_value
            # Setup update return value. update() returns StateEstimate object.
            mock_est = MagicMock()
            mock_est.velocity = 0.5  # Positive velocity
            mock_kf_instance.update.return_value = mock_est

            # Setup np.tanh to return comparable value
            # e.g. tanh(0.5 * 10) ~ 0.999
            self.mock_np.tanh.return_value = 0.99

            signal = strategy.calculate_signal(mock_df)

            print(f"Trend Signal (Mocked): {signal}")
            self.assertEqual(signal, 0.99)

            # Verify Flow
            MockKF.assert_called()  # KF initialized
            self.assertEqual(
                mock_kf_instance.update.call_count, 3
            )  # Called for each price

    def test_reversion_strategy_flow(self):
        """Verify Reversion Strategy calculates bands and compares prices"""
        strategy = BollingerReversionStrategy(window=20, num_std=2.0)

        mock_df = MagicMock()
        # Need len(df) >= 20
        # When len(mock_df) is called, it returns mock_df.__len__()
        mock_df.__len__.return_value = 30

        print(f"DEBUG: len(mock_df) = {len(mock_df)}")

        # When strategy checks len(market_data), it uses len().
        # However, strategy also uses market_data['close'].
        # In implementation:
        # if len(market_data) < self.window: return 0.0
        # series = market_data['close']
        # rolling_mean = series.rolling(...)

        # We need to make sure 'series' is returned properly
        mock_series = MagicMock()
        mock_df.__getitem__.return_value = mock_series

        # DEBUG: Verify mock connection
        retrieved_series = mock_df["close"]
        print(
            f"DEBUG: mock_df['close'] is mock_series? {retrieved_series is mock_series}"
        )
        print(f"DEBUG: Retrieved series ID: {id(retrieved_series)}")
        print(f"DEBUG: Mock series ID: {id(mock_series)}")

        # When accessing market_data['close'], MagicMock returns a NEW mock by default
        # unless configured. We correctly configured it above.

        # Rolling mocks
        mock_rolling = MagicMock()
        mock_series.rolling.return_value = mock_rolling

        mock_mean_series = MagicMock()
        mock_std_series = MagicMock()
        mock_rolling.mean.return_value = mock_mean_series
        mock_rolling.std.return_value = mock_std_series

        # Mock Arithmetic Chain for Bands
        # upper = mean + (std * 2)
        # lower = mean - (std * 2)

        mock_std_term = MagicMock()
        mock_std_series.__mul__.return_value = mock_std_term

        mock_upper_band = MagicMock()
        mock_lower_band = MagicMock()

        mock_mean_series.__add__.return_value = mock_upper_band
        mock_mean_series.__sub__.return_value = mock_lower_band

        # Set values for iloc[-1]
        # Price=90. Lower=95. Upper=105. -> Price < Lower -> Buy (1.0)
        mock_series.iloc.__getitem__.return_value = 90.0
        mock_lower_band.iloc.__getitem__.return_value = 95.0
        mock_upper_band.iloc.__getitem__.return_value = 105.0

        # Calculate Signal
        signal = strategy.calculate_signal(mock_df)
        print(f"Reversion Signal (Mocked): {signal}")

        self.assertEqual(signal, 1.0)  # Should be Buy

        # Assert calls were made
        mock_series.rolling.assert_called_with(window=20)
        mock_rolling.mean.assert_called()
        mock_rolling.std.assert_called()

    def test_reversion_instantiation(self):
        """Simple test to check class structure"""
        strategy = BollingerReversionStrategy()
        self.assertEqual(strategy.name, "BollingerReversion_V1")
        self.assertEqual(strategy.window, 20)

    def test_fractal_breakout_strategy(self):
        """Verify Fractal Breakout Logic"""
        # Import inside method to avoid top-level import issues if file is missing (though we just created it)
        from app.strategies.breakout import FractalBreakoutStrategy

        strategy = FractalBreakoutStrategy()

        mock_df = MagicMock()
        mock_df.__len__.return_value = 50  # > window*2
        # Mock series
        mock_series = MagicMock()
        mock_df.__getitem__.return_value = mock_series

        # Mock fd.find_min_d
        # It's an instance variable strategy.fd
        # We need to replace strategy.fd with a Mock
        strategy.fd = MagicMock()

        # Setup specific scenario:
        # Stationary series has a spike at the end.
        # Length of stationary series must be sufficient.

        # We need a REAL pandas series for the stationary series to allow .rolling().max() to work logic-wise?
        # Or we mock the chain again.
        # Since logic is: rolling_max = stationary.rolling().max().shift(1)
        # It's getting complicated to Mock 3 levels deep (rolling->max->shift->iloc).

        # Since we use dependency mocking, let's mock the return of find_min_d
        # to be a MagicMock that behaves correctly structure-wise.

        mock_stat_series = MagicMock()
        strategy.fd.find_min_d.return_value = (0.5, mock_stat_series)

        mock_stat_series.empty = False
        mock_stat_series.__len__.return_value = 50

        # Mock the rolling check chain:
        # rolling_max = stat.rolling().max().shift(1)

        mock_rolling = MagicMock()
        mock_stat_series.rolling.return_value = mock_rolling

        mock_rolling_max = MagicMock()
        mock_rolling.max.return_value = mock_rolling_max

        mock_shifted_max = MagicMock()
        mock_rolling_max.shift.return_value = mock_shifted_max

        # Same for min
        mock_rolling_min = MagicMock()
        mock_rolling.min.return_value = mock_rolling_min
        mock_shifted_min = MagicMock()
        mock_rolling_min.shift.return_value = mock_shifted_min

        # Comparison Logic:
        # current_val > prior_max -> 1.0

        # Values:
        # current (stat.iloc[-1]) = 100
        # prior_max (shifted.iloc[-1]) = 90
        # prior_min = 10

        mock_stat_series.iloc.__getitem__.return_value = 100.0
        mock_shifted_max.iloc.__getitem__.return_value = 90.0
        mock_shifted_min.iloc.__getitem__.return_value = 10.0

        # If arithmetic/comparison needs to be mocked?
        # 100.0 > 90.0 is native float comparison if .return_value works.

        signal = strategy.calculate_signal(mock_df)
        print(f"Fractal Signal (Mocked): {signal}")

        self.assertEqual(signal, 1.0)

        # Verify call chain
        strategy.fd.find_min_d.assert_called()
        mock_stat_series.rolling.assert_called_with(window=20)


if __name__ == "__main__":
    unittest.main()
