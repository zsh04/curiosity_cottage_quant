import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from app.backtest.engine import BacktestEngine
from app.backtest.feed import HistoricalCSVDataFeed
from app.backtest.execution import SimulatedExecutionHandler
from app.backtest.portfolio import Portfolio
from app.backtest.strategy import (
    Strategy,
    PhysicsStrategy,
    MomentumStrategy,
    MeanReversionStrategy,
    BreakoutStrategy,
)
from app.backtest.events import SignalEvent


# --- 1. Define Baseline Strategy ---
class BuyAndHoldStrategy(Strategy):
    def __init__(self):
        self.invested = False

    def calculate_signals(self, event, event_queue):
        if event.type == "MARKET":
            if not self.invested:
                # Buy on first bar
                signal = SignalEvent(event.timestamp, event.symbol, "LONG")
                event_queue.put(signal)
                self.invested = True


# --- 2. Synthetic Data Generator ---
def generate_synthetic_data(symbol="ETH", days=365):
    dates = pd.date_range(
        end=datetime.now(), periods=days * 24, freq="h"
    )  # Hourly data
    n = len(dates)

    # Geometric Brownian Motion
    dt = 1.0 / (365.0 * 24.0)  # Correct: 1 hour in years
    mu = 0.1  # 10% annual drift
    sigma = 0.8  # 80% annual vol (Crypto-like)

    prices = np.zeros(n)
    sigma = 0.3  # 30% annual vol

    prices = [100.0]
    for _ in range(n - 1):  # n-1 because we already have the first price
        prev = prices[-1]
        drift = mu * prev * dt
        shock = sigma * prev * np.random.randn() * np.sqrt(dt)  # Correct scaling
        price = prev + drift + shock
        prices.append(price)

    # Ensure prices are positive
    prices = np.maximum(0.01, prices)

    df = pd.DataFrame(
        {
            "open": prices,
            "high": prices * 1.002,
            "low": prices * 0.998,
            "close": prices,
            "volume": 1000,
        },
        index=dates,
    )

    return {symbol: df}


# --- 3. Simulation Runner ---
def run_simulation(strategy_cls, strategy_name, data):
    print(f"\n--- Running Simulation: {strategy_name} ---")
    feed = HistoricalCSVDataFeed(data)
    portfolio = Portfolio(initial_capital=10000.0)
    execution = SimulatedExecutionHandler()

    if strategy_name == "Physics":
        strategy = strategy_cls(lookback_window=50)
    else:
        strategy = strategy_cls()

    engine = BacktestEngine(feed, portfolio, execution, strategy)
    engine.run()

    # Reporting
    metrics = portfolio.performance_reporter.calculate_metrics()
    print(f"Total Return: {metrics.get('total_return_pct', 0):.2f}%")
    print(f"Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}")
    print(f"Max Drawdown: {metrics.get('max_drawdown_pct', 0):.2f}%")

    final_equity = (
        portfolio.history[-1]["total_equity"]
        if portfolio.history
        else portfolio.initial_capital
    )
    print(f"Final Equity: ${final_equity:.2f}")


if __name__ == "__main__":
    data = generate_synthetic_data()

    # Run Baseline
    run_simulation(BuyAndHoldStrategy, "Buy & Hold", data)

    # Run Physics
    run_simulation(PhysicsStrategy, "Physics", data)

    # Run Momentum
    run_simulation(MomentumStrategy, "Momentum (SMA 50/200)", data)

    # Run Mean Reversion
    run_simulation(MeanReversionStrategy, "Mean Reversion (BB 20, 2)", data)

    # Run Breakout
    run_simulation(BreakoutStrategy, "Breakout (20 Day High*)", data)
