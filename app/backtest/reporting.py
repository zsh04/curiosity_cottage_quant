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
            "sortino_ratio": self._calculate_sortino(returns),
            "tail_ratio": self._calculate_tail_ratio(returns),
            "win_rate": self._calculate_win_rate(returns)
        }

    def _calculate_sortino(self, returns: pd.Series, risk_free: float = 0.0) -> float:
        """
        Sortino Ratio: Excess Return / Downside Deviation.
        Only penalizes harmful volatility.
        """
        if len(returns) < 2:
            return 0.0
        
        excess_returns = returns - risk_free
        downside_returns = excess_returns[excess_returns < 0]
        
        if len(downside_returns) == 0:
            return 10.0 # Perfect score (no losses)
            
        downside_std = np.std(downside_returns) * np.sqrt(365 * 24) # Annualized
        annualized_return = returns.mean() * (365 * 24)
        
        if downside_std == 0:
            return 10.0
            
        return float(annualized_return / downside_std)

    def _calculate_tail_ratio(self, returns: pd.Series) -> float:
        """
        Tail Ratio: P95 (Gains) / abs(P5 (Losses)).
        Wrapper for 'Predatory Physics' (Positive Skew).
        > 1.0 implies larger wins than losses.
        """
        if len(returns) < 10:
            return 0.0
            
        p95 = np.percentile(returns, 95)
        p5 = np.percentile(returns, 5)
        
        if p5 == 0:
            return 10.0 # Infinite ratio
            
        return float(abs(p95 / p5))

    def _calculate_win_rate(self, returns: pd.Series) -> float:
        if len(returns) == 0:
            return 0.0
        wins = returns[returns > 0]
        return len(wins) / len(returns)

    def generate_report(self):
        metrics = self.calculate_metrics()
        if not metrics:
            return "No trades or history."

            "Total Return": f"{metrics['total_return_pct']:.2f}%",
            "Sharpe Ratio": f"{metrics['sharpe_ratio']:.2f}",
            "Sortino Ratio": f"{metrics['sortino_ratio']:.2f}",
            "Tail Ratio": f"{metrics['tail_ratio']:.2f}",
            "Max Drawdown": f"{metrics['max_drawdown_pct']:.2f}%",
            "Win Rate": f"{metrics['win_rate']:.1%}",
        }
