"""
Performance Metrics Type Definitions.

Dataclasses for all 27 trading performance metrics.
Aligned with BES position sizing and fat-tailed distributions.
"""

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class TailMetrics:
    """Tail risk metrics for fat-tailed distributions."""

    cvar_95: float  # Expected Shortfall (95% confidence)
    tail_ratio: float  # 95th percentile gain / 5th percentile loss
    skewness: float  # Distribution skew (> 0 = positive skew)
    kurtosis: float  # Fat-tailedness (> 3 = fat tails)
    var_95: float  # Value at Risk (95% threshold)


@dataclass
class BESValidationMetrics:
    """Metrics specific to BES position sizing validation."""

    realized_es: float  # Actual CVaR from trades
    predicted_es: float  # BES predicted CVaR
    es_accuracy: float  # realized / predicted (target: 0.8-1.2)
    kelly_efficiency: float  # actual_size / theoretical_kelly (target: 0.25-0.5)
    tail_event_frequency: float  # % of trades in tail (target: ~5%)
    leverage_utilization: float  # total_exposure / capital


@dataclass
class MagnitudeMetrics:
    """Metrics focusing on magnitude over frequency."""

    profit_factor: float  # gross_profit / gross_loss
    expectancy: float  # expected $ per trade
    gain_to_pain_ratio: float  # sum(returns) / sum(abs(drawdowns))
    recovery_factor: float  # net_profit / max_drawdown


@dataclass
class RiskAdjustedMetrics:
    """Risk-adjusted return metrics."""

    sortino_ratio: float  # Downside-focused Sharpe
    omega_ratio: float  # Probability-weighted gains/losses
    calmar_ratio: float  # annual_return / max_drawdown
    sharpe_ratio: float  # Industry standard (for comparison)
    ulcer_index: float  # Sqrt of mean squared drawdowns


@dataclass
class DrawdownMetrics:
    """Drawdown and recovery metrics."""

    max_drawdown: float  # Maximum peak-to-trough decline (%)
    avg_drawdown: float  # Average drawdown (%)
    max_drawdown_duration: int  # Days in max drawdown
    avg_recovery_time: float  # Average days to recover from DD


@dataclass
class StrategyAttributionMetrics:
    """Per-strategy performance attribution."""

    strategy_contributions: Dict[str, float]  # % of total PnL
    strategy_sharpe: Dict[str, float]  # Per-strategy Sharpe (ranking)
    strategy_correlation_matrix: Dict[
        str, Dict[str, float]
    ]  # Correlation between strategies
    concentration_risk: float  # Herfindahl index (< 0.25 = diversified)


@dataclass
class ExecutionQualityMetrics:
    """Execution and trading quality metrics."""

    realized_slippage_vs_expected: float  # Accuracy of slippage model
    fill_quality_score: float  # executed_price / expected_price
    cost_adjusted_return: float  # Net after commissions & slippage
    turnover_rate: float  # sum(abs(position_changes)) / equity


@dataclass
class ConsistencyMetrics:
    """Consistency and time-based performance."""

    monthly_win_rate: float  # % of winning months
    consecutive_losses_max: int  # Longest losing streak
    information_coefficient: float  # Correlation(signal, forward_returns)
    regime_specific_sharpe: Dict[str, float]  # Sharpe by regime


@dataclass
class VanityMetrics:
    """Vanity metrics for VC/investor reporting only.

    DO NOT OPTIMIZE FOR THESE. They have known flaws:
    - Win rate ignores magnitude (Pareto problem)
    - Average return unstable with fat tails
    - Sharpe assumes Gaussian distributions
    """

    win_rate: float  # Trade-level win rate (misleading!)
    average_return: float  # Mean return (unstable with fat tails)
    # Sharpe already in RiskAdjustedMetrics


@dataclass
class PerformanceMetrics:
    """Complete performance metrics suite (27 total).

    Organized by category for clarity.
    All metrics aligned with BES position sizing philosophy.
    """

    # === DASHBOARD METRICS (Top 10) ===
    # These appear in all dashboards and reports
    profit_factor: float  # ⭐⭐⭐
    sortino_ratio: float  # ⭐⭐⭐
    cvar_95: float  # ⭐⭐⭐
    max_drawdown: float  # ⭐⭐⭐
    tail_ratio: float  # ⭐⭐⭐
    expectancy: float  # ⭐⭐
    es_accuracy: float  # ⭐⭐⭐
    omega_ratio: float  # ⭐⭐
    monthly_win_rate: float  # ⭐
    calmar_ratio: float  # ⭐⭐

    # === FULL SUITE (Grouped) ===
    tail: TailMetrics
    bes_validation: BESValidationMetrics
    magnitude: MagnitudeMetrics
    risk_adjusted: RiskAdjustedMetrics
    drawdown: DrawdownMetrics
    strategy_attribution: Optional[StrategyAttributionMetrics] = None
    execution_quality: Optional[ExecutionQualityMetrics] = None
    consistency: Optional[ConsistencyMetrics] = None
    vanity: Optional[VanityMetrics] = None

    # === METADATA ===
    total_trades: int = 0
    total_days: int = 0
    regime: str = "UNKNOWN"

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            # Dashboard
            "profit_factor": self.profit_factor,
            "sortino_ratio": self.sortino_ratio,
            "cvar_95": self.cvar_95,
            "max_drawdown": self.max_drawdown,
            "tail_ratio": self.tail_ratio,
            "expectancy": self.expectancy,
            "es_accuracy": self.es_accuracy,
            "omega_ratio": self.omega_ratio,
            "monthly_win_rate": self.monthly_win_rate,
            "calmar_ratio": self.calmar_ratio,
            # Full suite
            "tail": self.tail.__dict__ if self.tail else None,
            "bes_validation": self.bes_validation.__dict__
            if self.bes_validation
            else None,
            "magnitude": self.magnitude.__dict__ if self.magnitude else None,
            "risk_adjusted": self.risk_adjusted.__dict__
            if self.risk_adjusted
            else None,
            "drawdown": self.drawdown.__dict__ if self.drawdown else None,
            "strategy_attribution": (
                {
                    "contributions": self.strategy_attribution.strategy_contributions,
                    "sharpe": self.strategy_attribution.strategy_sharpe,
                    "correlation": self.strategy_attribution.strategy_correlation_matrix,
                    "concentration": self.strategy_attribution.concentration_risk,
                }
                if self.strategy_attribution
                else None
            ),
            "execution_quality": self.execution_quality.__dict__
            if self.execution_quality
            else None,
            "consistency": self.consistency.__dict__ if self.consistency else None,
            "vanity": self.vanity.__dict__ if self.vanity else None,
            # Metadata
            "total_trades": self.total_trades,
            "total_days": self.total_days,
            "regime": self.regime,
        }
