import pytest
import pandas as pd
import queue
from datetime import datetime, timedelta
from app.backtest.events import SignalEvent
from app.backtest.engine import BacktestEngine
from app.backtest.feed import HistoricalCSVDataFeed
from app.backtest.execution import SimulatedExecutionHandler
from app.backtest.portfolio import Portfolio


class MockStrategy:
    """
    Simple Strategy that buys on the first bar.
    """

    def __init__(self):
        self.invested = False

    def calculate_signals(self, event, event_queue):
        if event.type == "MARKET" and not self.invested:
            # Buy Signal
            signal = SignalEvent(
                timestamp=event.timestamp,
                symbol=event.symbol,
                direction="LONG",
                strength=1.0,
            )
            event_queue.put(signal)
            self.invested = True


class TestBacktestIntegration:
    def test_full_backtest_run(self):
        # 1. Setup Data
        dates = pd.date_range(start="2023-01-01", periods=5, freq="D")
        df = pd.DataFrame(
            {
                "open": [100, 101, 102, 103, 104],
                "high": [102, 103, 104, 105, 106],
                "low": [99, 100, 101, 102, 103],
                "close": [101, 102, 103, 104, 105],
                "volume": [1000, 1000, 1000, 1000, 1000],
            },
            index=dates,
        )

        data_feed = HistoricalCSVDataFeed({"AAPL": df})

        # 2. Setup Components
        portfolio = Portfolio(initial_capital=10000.0)
        execution = SimulatedExecutionHandler(latency_ms=0)  # Instant fill for test
        strategy = MockStrategy()

        # 3. Setup Engine
        engine = BacktestEngine(data_feed, portfolio, execution, strategy)

        # 4. Run
        engine.run()

        # 5. Assertions
        # Should have bought 100 shares at approx 101 + slippage/comm
        assert "AAPL" in portfolio.positions
        assert 90 <= portfolio.positions["AAPL"] <= 100, (
            f"Expected ~100 shares, got {portfolio.positions['AAPL']}"
        )
        assert portfolio.current_cash < 10000.0  # Spent money

        # Check holdings value info
        assert "AAPL" in portfolio.holdings
        assert portfolio.holdings["AAPL"]["last_price"] == 105.0  # Last close
