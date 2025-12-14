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
        self.history = pd.DataFrame(portfolio_history)
        if not self.history.empty:
            self.history["timestamp"] = pd.to_datetime(self.history["timestamp"])
            self.history.set_index("timestamp", inplace=True)
            self.history["returns"] = self.history["total_equity"].pct_change()

    def generate_report(self):
        if self.history.empty:
            return "No trades or history."

        total_return = (
            self.history["total_equity"].iloc[-1] / self.history["total_equity"].iloc[0]
        ) - 1.0

        returns = self.history["returns"].dropna()
        if len(returns) > 1:
            sharpe = (returns.mean() / returns.std()) * np.sqrt(252)  # Annulized
        else:
            sharpe = 0.0

        # Drawdown
        cum_returns = (1 + returns).cumprod()
        running_max = cum_returns.cummax()
        drawdown = (cum_returns - running_max) / running_max
        max_drawdown = drawdown.min()

        report = {
            "Total Return": f"{total_return:.2%}",
            "Sharpe Ratio": f"{sharpe:.2f}",
            "Max Drawdown": f"{max_drawdown:.2%}",
        }
        return report
