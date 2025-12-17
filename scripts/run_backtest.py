"""
Production-Grade Backtester for CC-V2 Strategies.
Uses MarketService, PhysicsService, and STRATEGY_REGISTRY.
Implements Physics Veto: If Alpha < 2.0, signal is forced to 0.
"""

import pandas as pd
import numpy as np
from typing import List, Dict
from app.services.market import MarketService
from app.services.physics import PhysicsService
from app.strategies import STRATEGY_REGISTRY


class BacktestEngine:
    """
    Simple Vectorized Backtest Engine.
    Simulates trading strategies with Physics Veto.
    """

    def __init__(self, symbol: str = "SPY"):
        self.symbol = symbol
        self.market_service = MarketService()
        self.physics_service = PhysicsService()
        self.results = []

    def fetch_data(self) -> List[float]:
        """Fetch historical price data via MarketService."""
        print(f"📊 Fetching market data for {self.symbol}...")
        snapshot = self.market_service.get_market_snapshot(self.symbol)
        history = snapshot.get("history", [])

        if len(history) < 50:
            raise ValueError(
                f"Insufficient data: {len(history)} bars. Need at least 50."
            )

        print(f"✅ Fetched {len(history)} bars")
        return history

    def run_strategy(self, strategy, history: List[float]) -> Dict:
        """
        Run a single strategy on the price history.

        Returns:
            {
                'name': str,
                'sharpe': float,
                'total_return': float,
                'signals': List[float]
            }
        """
        print(f"\n🧪 Testing Strategy: {strategy.name}")

        # Convert to DataFrame for strategy compatibility
        df = pd.DataFrame({"close": history})

        # Storage
        signals = []
        pnl = []

        # Minimum window for strategy calculation
        min_window = 20

        for t in range(min_window, len(history)):
            # Rolling window up to time t
            window = df.iloc[: t + 1].copy()

            try:
                # Calculate strategy signal
                signal = strategy.calculate_signal(window)
            except Exception as e:
                # If strategy fails, use neutral signal
                signal = 0.0

            # --- PHYSICS VETO ---
            # Analyze regime on the last 100 bars (or whatever is available)
            lookback = min(100, t)
            regime_window = history[t - lookback : t + 1]

            try:
                regime_analysis = self.physics_service.analyze_regime(regime_window)
                alpha = regime_analysis.get("alpha", 3.0)

                # If Critical Regime (alpha < 2.0), veto the signal
                if alpha < 2.0:
                    signal = 0.0

            except Exception:
                # If physics fails, allow the signal
                pass

            signals.append(signal)

            # Calculate return (if we have next bar)
            if t < len(history) - 1:
                market_return = (history[t + 1] - history[t]) / history[t]
                strategy_return = signal * market_return
                pnl.append(strategy_return)

        # --- METRICS ---
        if len(pnl) == 0:
            return {
                "name": strategy.name,
                "sharpe": 0.0,
                "total_return": 0.0,
                "num_trades": 0,
            }

        avg_return = np.mean(pnl)
        std_return = np.std(pnl)

        # Sharpe Ratio (annualized assuming daily data)
        if std_return > 1e-9:
            sharpe = (avg_return / std_return) * np.sqrt(252)
        else:
            sharpe = 0.0

        # Total Return
        cumulative_return = np.prod([1 + r for r in pnl]) - 1
        total_return_pct = cumulative_return * 100

        # Count non-zero signals as "trades"
        num_trades = sum(1 for s in signals if abs(s) > 0.01)

        return {
            "name": strategy.name,
            "sharpe": sharpe,
            "total_return": total_return_pct,
            "num_trades": num_trades,
        }

    def run_all_strategies(self):
        """Run backtest for all registered strategies."""
        print("=" * 60)
        print("🏁 STRATEGY BACKTEST - CURIOSITY COTTAGE V2")
        print("=" * 60)

        # Fetch data once
        history = self.fetch_data()

        # Test each strategy
        for strategy in STRATEGY_REGISTRY:
            result = self.run_strategy(strategy, history)
            self.results.append(result)

        # Print Results Table
        self.print_results()

    def print_results(self):
        """Print comparison table of all strategies."""
        print("\n" + "=" * 60)
        print("📊 BACKTEST RESULTS")
        print("=" * 60)
        print(f"{'Strategy':<30} {'Sharpe':<10} {'Return %':<12} {'Trades':<10}")
        print("-" * 60)

        # Sort by Sharpe Ratio
        sorted_results = sorted(self.results, key=lambda x: x["sharpe"], reverse=True)

        for result in sorted_results:
            print(
                f"{result['name']:<30} "
                f"{result['sharpe']:<10.2f} "
                f"{result['total_return']:<12.2f} "
                f"{result['num_trades']:<10}"
            )

        print("=" * 60)

        # Winner
        if sorted_results:
            winner = sorted_results[0]
            print(f"\n🏆 WINNER: {winner['name']} (Sharpe: {winner['sharpe']:.2f})")


if __name__ == "__main__":
    engine = BacktestEngine(symbol="SPY")
    engine.run_all_strategies()
