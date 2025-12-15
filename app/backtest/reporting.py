import pandas as pd
import numpy as np


class PerformanceReporter:
    """
    Calculates and reports backtest metrics.
    """

    def __init__(self, portfolio_history: list[dict]):
        """
        portfolio_history: List of dicts with 'timestamp', 'total_equity'
        """
        self.raw_history = portfolio_history
        self.history_df = pd.DataFrame()  # Cache or remove

    def calculate_metrics(self) -> dict:
        if not self.raw_history:
            return {}

        # Convert to DF on demand
        df = pd.DataFrame(self.raw_history)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df.set_index("timestamp", inplace=True)
        df["returns"] = df["total_equity"].pct_change()

        total_return = (df["total_equity"].iloc[-1] / df["total_equity"].iloc[0]) - 1.0

        returns = df["returns"].dropna()
        if len(returns) > 1:
            sharpe = (returns.mean() / returns.std()) * np.sqrt(365 * 24)  # Crypto 24/7
        else:
            sharpe = 0.0

        # Drawdown
        cum_returns = (1 + returns).cumprod()
        running_max = cum_returns.cummax()
        drawdown = (cum_returns - running_max) / running_max
        max_drawdown = drawdown.min()

        return {
            "total_return_pct": total_return * 100,
            "sharpe_ratio": sharpe,
            "max_drawdown_pct": max_drawdown * 100,
        }

    def generate_report(self):
        metrics = self.calculate_metrics()
        if not metrics:
            return "No trades or history."

        return {
            "Total Return": f"{metrics['total_return_pct']:.2f}%",
            "Sharpe Ratio": f"{metrics['sharpe_ratio']:.2f}",
            "Max Drawdown": f"{metrics['max_drawdown_pct']:.2f}%",
        }
