"""
Performance Metrics Calculator Service.

Calculates all 27 trading performance metrics aligned with BES sizing.
Handles fat-tailed distributions and power-law assumptions.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from scipy import stats

from app.core.metrics_types import (
    PerformanceMetrics,
    TailMetrics,
    BESValidationMetrics,
    MagnitudeMetrics,
    RiskAdjustedMetrics,
    DrawdownMetrics,
    StrategyAttributionMetrics,
    ExecutionQualityMetrics,
    ConsistencyMetrics,
    VanityMetrics,
)


class MetricsCalculator:
    """
    Calculate comprehensive performance metrics.

    All methods assume returns are in decimal form (0.01 = 1%).
    Annualization assumes 252 trading days.
    """

    TRADING_DAYS_PER_YEAR = 252
    RISK_FREE_RATE = 0.0416  # 4.16% from FRED API (updated dynamically elsewhere)

    def __init__(self, risk_free_rate: Optional[float] = None):
        """Initialize calculator with optional risk-free rate override."""
        if risk_free_rate is not None:
            self.RISK_FREE_RATE = risk_free_rate

    # ========================================================================
    # TAIL METRICS (Fat-Tailed Distributions)
    # ========================================================================

    def calculate_tail_metrics(self, returns: np.ndarray) -> TailMetrics:
        """Calculate tail risk metrics for fat-tailed distributions."""
        if len(returns) == 0:
            return TailMetrics(0.0, 0.0, 0.0, 0.0, 0.0)

        # CVaR 95% (Expected Shortfall)
        var_95 = np.percentile(returns, 5)
        cvar_95 = returns[returns <= var_95].mean()

        # Tail Ratio (95th / 5th percentile)
        p95 = np.percentile(returns, 95)
        p5 = np.percentile(returns, 5)
        tail_ratio = p95 / abs(p5) if p5 != 0 else 0.0

        # Skewness & Kurtosis
        skewness = float(stats.skew(returns))
        kurtosis = float(stats.kurtosis(returns, fisher=False))  # Pearson (not excess)

        return TailMetrics(
            cvar_95=float(cvar_95),
            tail_ratio=tail_ratio,
            skewness=skewness,
            kurtosis=kurtosis,
            var_95=float(var_95),
        )

    # ========================================================================
    # BES VALIDATION METRICS
    # ========================================================================

    def calculate_bes_validation(
        self,
        returns: np.ndarray,
        predicted_es_values: Optional[List[float]] = None,
        position_sizes: Optional[np.ndarray] = None,
        theoretical_kelly: Optional[np.ndarray] = None,
        capital: float = 100000.0,
    ) -> BESValidationMetrics:
        """Calculate BES-specific validation metrics."""
        if len(returns) == 0:
            return BESValidationMetrics(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

        # Realized ES
        var_95 = np.percentile(returns, 5)
        realized_es = returns[returns <= var_95].mean()

        # Predicted ES (average of BES predictions)
        predicted_es = (
            np.mean(predicted_es_values) if predicted_es_values else realized_es
        )

        # ES Accuracy
        es_accuracy = realized_es / predicted_es if predicted_es != 0 else 1.0

        # Kelly Efficiency
        kelly_efficiency = 0.0
        if position_sizes is not None and theoretical_kelly is not None:
            actual_fractions = position_sizes / capital
            kelly_efficiency = float(np.mean(actual_fractions / theoretical_kelly))

        # Tail Event Frequency
        p5_threshold = np.percentile(returns, 5)
        tail_event_frequency = (returns <= p5_threshold).sum() / len(returns)

        # Leverage Utilization
        leverage = 0.0
        if position_sizes is not None:
            leverage = float(np.mean(position_sizes) / capital)

        return BESValidationMetrics(
            realized_es=float(realized_es),
            predicted_es=float(predicted_es),
            es_accuracy=float(es_accuracy),
            kelly_efficiency=kelly_efficiency,
            tail_event_frequency=float(tail_event_frequency),
            leverage_utilization=leverage,
        )

    # ========================================================================
    # MAGNITUDE METRICS (Magnitude > Frequency)
    # ========================================================================

    def calculate_magnitude_metrics(
        self, returns: np.ndarray, equity_curve: Optional[np.ndarray] = None
    ) -> MagnitudeMetrics:
        """Calculate magnitude-focused metrics (not frequency)."""
        if len(returns) == 0:
            return MagnitudeMetrics(0.0, 0.0, 0.0, 0.0)

        # Profit Factor
        gains = returns[returns > 0].sum()
        losses = abs(returns[returns < 0].sum())
        profit_factor = gains / losses if losses != 0 else 0.0

        # Expectancy
        wins = returns[returns > 0]
        losses_arr = returns[returns < 0]
        win_prob = len(wins) / len(returns) if len(returns) > 0 else 0
        loss_prob = len(losses_arr) / len(returns) if len(returns) > 0 else 0
        avg_win = wins.mean() if len(wins) > 0 else 0
        avg_loss = losses_arr.mean() if len(losses_arr) > 0 else 0
        expectancy = (avg_win * win_prob) + (
            avg_loss * loss_prob
        )  # avg_loss is negative

        # Gain-to-Pain Ratio
        gtp = 0.0
        if equity_curve is not None and len(equity_curve) > 0:
            drawdowns = self._calculate_drowdown_series(equity_curve)
            total_pain = np.sum(np.abs(drawdowns))
            gtp = returns.sum() / total_pain if total_pain != 0 else 0.0

        # Recovery Factor
        recovery_factor = 0.0
        if equity_curve is not None and len(equity_curve) > 0:
            max_dd = self._calculate_max_drawdown(equity_curve)
            net_profit = equity_curve[-1] - equity_curve[0]
            recovery_factor = net_profit / abs(max_dd) if max_dd != 0 else 0.0

        return MagnitudeMetrics(
            profit_factor=float(profit_factor),
            expectancy=float(expectancy),
            gain_to_pain_ratio=float(gtp),
            recovery_factor=float(recovery_factor),
        )

    # ========================================================================
    # RISK-ADJUSTED METRICS
    # ========================================================================

    def calculate_risk_adjusted_metrics(
        self, returns: np.ndarray
    ) -> RiskAdjustedMetrics:
        """Calculate risk-adjusted return metrics."""
        if len(returns) == 0:
            return RiskAdjustedMetrics(0.0, 0.0, 0.0, 0.0, 0.0)

        mean_return = returns.mean()
        std_dev = returns.std()

        # Sharpe Ratio (annualized)
        excess_return = mean_return - (self.RISK_FREE_RATE / self.TRADING_DAYS_PER_YEAR)
        sharpe = (
            (excess_return * np.sqrt(self.TRADING_DAYS_PER_YEAR)) / std_dev
            if std_dev != 0
            else 0.0
        )

        # Sortino Ratio (downside deviation)
        downside_returns = returns[returns < 0]
        downside_std = downside_returns.std() if len(downside_returns) > 0 else std_dev
        sortino = (
            (excess_return * np.sqrt(self.TRADING_DAYS_PER_YEAR)) / downside_std
            if downside_std != 0
            else 0.0
        )

        # Omega Ratio (threshold = 0%)
        gains = returns[returns > 0].sum()
        losses = abs(returns[returns < 0].sum())
        omega = gains / losses if losses != 0 else 0.0

        # Calmar Ratio (requires equity curve, placeholder)
        calmar = 0.0  # Calculated separately with equity curve

        # Ulcer Index (requires equity curve, placeholder)
        ulcer = 0.0  # Calculated separately

        return RiskAdjustedMetrics(
            sortino_ratio=float(sortino),
            omega_ratio=float(omega),
            calmar_ratio=calmar,
            sharpe_ratio=float(sharpe),
            ulcer_index=ulcer,
        )

    # ========================================================================
    # DRAWDOWN METRICS
    # ========================================================================

    def calculate_drawdown_metrics(self, equity_curve: np.ndarray) -> DrawdownMetrics:
        """Calculate drawdown and recovery metrics."""
        if len(equity_curve) == 0:
            return DrawdownMetrics(0.0, 0.0, 0, 0.0)

        # Max Drawdown
        max_dd = self._calculate_max_drawdown(equity_curve)

        # Drawdown series
        dd_series = self._calculate_drowdown_series(equity_curve)

        # Average Drawdown
        avg_dd = dd_series[dd_series < 0].mean() if (dd_series < 0).any() else 0.0

        # Max DD Duration
        max_dd_duration = self._calculate_max_dd_duration(dd_series)

        # Average Recovery Time
        avg_recovery = self._calculate_avg_recovery_time(dd_series)

        return DrawdownMetrics(
            max_drawdown=float(max_dd),
            avg_drawdown=float(avg_dd),
            max_drawdown_duration=max_dd_duration,
            avg_recovery_time=avg_recovery,
        )

    # ========================================================================
    # VANITY METRICS (For VCs Only)
    # ========================================================================

    def calculate_vanity_metrics(self, returns: np.ndarray) -> VanityMetrics:
        """Calculate vanity metrics for investor reporting.

        WARNING: These metrics have known flaws. Do NOT optimize for them.
        """
        if len(returns) == 0:
            return VanityMetrics(0.0, 0.0)

        # Win Rate (trade-level)
        wins = (returns > 0).sum()
        win_rate = wins / len(returns) if len(returns) > 0 else 0.0

        # Average Return
        avg_return = returns.mean()

        return VanityMetrics(win_rate=float(win_rate), average_return=float(avg_return))

    # ========================================================================
    # MASTER CALCULATOR
    # ========================================================================

    def calculate_all(
        self,
        returns: np.ndarray,
        equity_curve: Optional[np.ndarray] = None,
        predicted_es_values: Optional[List[float]] = None,
        position_sizes: Optional[np.ndarray] = None,
        theoretical_kelly: Optional[np.ndarray] = None,
        capital: float = 100000.0,
        regime: str = "UNKNOWN",
    ) -> PerformanceMetrics:
        """
        Calculate all 27 metrics.

        Args:
            returns: Array of returns (decimal, e.g., 0.01 = 1%)
            equity_curve: Optional equity curve for DD metrics
            predicted_es_values: BES predicted ES values (for validation)
            position_sizes: Actual position sizes taken
            theoretical_kelly: Theoretical Kelly fractions
            capital: Starting capital
            regime: Current market regime

        Returns:
            PerformanceMetrics with all 27 metrics populated
        """
        if equity_curve is None:
            equity_curve = np.cumsum(returns) + capital

        # Calculate all categories
        tail = self.calculate_tail_metrics(returns)
        bes_val = self.calculate_bes_validation(
            returns, predicted_es_values, position_sizes, theoretical_kelly, capital
        )
        magnitude = self.calculate_magnitude_metrics(returns, equity_curve)
        risk_adj = self.calculate_risk_adjusted_metrics(returns)
        drawdown = self.calculate_drawdown_metrics(equity_curve)
        vanity = self.calculate_vanity_metrics(returns)

        # Update Calmar & Ulcer in risk_adjusted
        if len(equity_curve) > 0:
            annual_return = (equity_curve[-1] / equity_curve[0]) ** (
                self.TRADING_DAYS_PER_YEAR / len(returns)
            ) - 1
            risk_adj.calmar_ratio = (
                annual_return / abs(drawdown.max_drawdown)
                if drawdown.max_drawdown != 0
                else 0.0
            )
            risk_adj.ulcer_index = float(
                np.sqrt(np.mean(self._calculate_drowdown_series(equity_curve) ** 2))
            )

        # Top 10 dashboard metrics
        return PerformanceMetrics(
            profit_factor=magnitude.profit_factor,
            sortino_ratio=risk_adj.sortino_ratio,
            cvar_95=tail.cvar_95,
            max_drawdown=drawdown.max_drawdown,
            tail_ratio=tail.tail_ratio,
            expectancy=magnitude.expectancy,
            es_accuracy=bes_val.es_accuracy,
            omega_ratio=risk_adj.omega_ratio,
            monthly_win_rate=0.0,  # Requires monthly grouping, calculated separately
            calmar_ratio=risk_adj.calmar_ratio,
            # Full suite
            tail=tail,
            bes_validation=bes_val,
            magnitude=magnitude,
            risk_adjusted=risk_adj,
            drawdown=drawdown,
            vanity=vanity,
            # Metadata
            total_trades=len(returns),
            total_days=len(equity_curve),
            regime=regime,
        )

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    def _calculate_max_drawdown(self, equity_curve: np.ndarray) -> float:
        """Calculate maximum drawdown as percentage."""
        running_max = np.maximum.accumulate(equity_curve)
        drawdown = (equity_curve - running_max) / running_max
        return float(drawdown.min())

    def _calculate_drowdown_series(self, equity_curve: np.ndarray) -> np.ndarray:
        """Calculate drawdown series."""
        running_max = np.maximum.accumulate(equity_curve)
        return (equity_curve - running_max) / running_max

    def _calculate_max_dd_duration(self, dd_series: np.ndarray) -> int:
        """Calculate maximum drawdown duration in periods."""
        in_dd = dd_series < 0
        if not in_dd.any():
            return 0

        # Find consecutive DD periods
        dd_groups = np.split(
            np.arange(len(dd_series)), np.where(np.diff(in_dd.astype(int)) != 0)[0] + 1
        )
        dd_durations = [len(group) for group in dd_groups if in_dd[group[0]]]

        return max(dd_durations) if dd_durations else 0

    def _calculate_avg_recovery_time(self, dd_series: np.ndarray) -> float:
        """Calculate average recovery time from drawdowns."""
        recovery_times = []
        in_dd = False
        dd_start = 0

        for i, dd in enumerate(dd_series):
            if dd < 0 and not in_dd:
                in_dd = True
                dd_start = i
            elif dd >= 0 and in_dd:
                in_dd = False
                recovery_times.append(i - dd_start)

        return float(np.mean(recovery_times)) if recovery_times else 0.0
