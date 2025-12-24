"""
Unit tests for Performance Metrics Calculator.

Tests all 27 metrics with known inputs/outputs.
"""

import numpy as np
import pytest
from app.services.metrics import MetricsCalculator


class TestTailMetrics:
    """Test tail risk metrics calculation."""

    def test_cvar_calculation(self):
        """Test CVaR 95% (Expected Shortfall)."""
        calc = MetricsCalculator()

        # Simple case: -10, -5, 0, 5, 10 (percentile 5 = -10)
        returns = np.array([-0.10, -0.05, 0.0, 0.05, 0.10])
        tail = calc.calculate_tail_metrics(returns)

        # CVaR should be mean of worst 5% (just -0.10 in this case)
        assert tail.cvar_95 == pytest.approx(-0.10, abs=0.01)
        assert tail.var_95 == pytest.approx(
            -0.10, abs=0.02
        )  # Percentile may interpolate

    def test_tail_ratio(self):
        """Test tail ratio (95th / 5th percentile)."""
        calc = MetricsCalculator()

        # Symmetric: -10 to +10
        returns = np.linspace(-0.10, 0.10, 100)
        tail = calc.calculate_tail_metrics(returns)

        # Should be ~1.0 for symmetric distribution
        assert tail.tail_ratio == pytest.approx(1.0, abs=0.1)

    def test_skewness(self):
        """Test skewness calculation."""
        calc = MetricsCalculator()

        # Positive skew: more small wins, few large wins
        returns = np.array([0.01] * 90 + [0.10] * 10)
        tail = calc.calculate_tail_metrics(returns)

        # Should have positive skew
        assert tail.skewness > 0

    def test_kurtosis(self):
        """Test kurtosis (fat-tailedness)."""
        calc = MetricsCalculator()

        # Fat tails: lots of outliers
        returns = np.concatenate(
            [
                np.random.normal(0, 0.01, 90),
                np.array([-0.10, 0.10] * 5),  # Fat tails
            ]
        )
        tail = calc.calculate_tail_metrics(returns)

        # Should have excess kurtosis (> 3)
        assert tail.kurtosis > 3.0


class TestMagnitudeMetrics:
    """Test magnitude-focused metrics."""

    def test_profit_factor(self):
        """Test profit factor calculation."""
        calc = MetricsCalculator()

        # wins = [100, 200] = 300, losses = [-50] = 50
        # PF = 300 / 50 = 6.0
        returns = np.array([0.10, 0.20, -0.05])
        magnitude = calc.calculate_magnitude_metrics(returns)

        assert magnitude.profit_factor == pytest.approx(6.0, abs=0.1)

    def test_expectancy(self):
        """Test expectancy (expected $ per trade)."""
        calc = MetricsCalculator()

        # 2 wins of 0.10, 1 loss of -0.05
        # Expectancy = (0.10 * 2/3) + (-0.05 * 1/3) = 0.05
        returns = np.array([0.10, 0.10, -0.05])
        magnitude = calc.calculate_magnitude_metrics(returns)

        assert magnitude.expectancy == pytest.approx(0.05, abs=0.01)

    def test_zero_losses(self):
        """Test profit factor with no losses (edge case)."""
        calc = MetricsCalculator()

        # All wins
        returns = np.array([0.10, 0.20, 0.05])
        magnitude = calc.calculate_magnitude_metrics(returns)

        # Should handle gracefully (return 0 or inf, we return 0)
        assert magnitude.profit_factor == 0.0


class TestRiskAdjustedMetrics:
    """Test risk-adjusted return metrics."""

    def test_sharpe_ratio(self):
        """Test Sharpe ratio calculation."""
        calc = MetricsCalculator(risk_free_rate=0.0)  # Simplify

        # Mean = 0.01, Std = 0.02
        returns = np.array([0.01] * 50 + [-0.01] * 50)  # Mean = 0
        returns[0] = 0.03  # Adjust to get mean = 0.01
        risk_adj = calc.calculate_risk_adjusted_metrics(returns)

        # Sharpe should be positive
        assert risk_adj.sharpe_ratio > 0

    def test_sortino_ratio(self):
        """Test Sortino ratio (downside-only risk)."""
        calc = MetricsCalculator(risk_free_rate=0.0)

        # Asymmetric: small losses, large wins
        # More wins than losses to ensure positive returns
        returns = np.array([-0.01] * 20 + [0.05] * 30)  # Positive mean, wins > losses
        risk_adj = calc.calculate_risk_adjusted_metrics(returns)

        # Sortino should be positive (using downside risk only)
        assert risk_adj.sortino_ratio > 0

    def test_omega_ratio(self):
        """Test Omega ratio (gains / losses at threshold)."""
        calc = MetricsCalculator()

        # 3 wins = 0.30, 1 loss = -0.10
        # Omega = 0.30 / 0.10 = 3.0
        returns = np.array([0.10, 0.10, 0.10, -0.10])
        risk_adj = calc.calculate_risk_adjusted_metrics(returns)

        assert risk_adj.omega_ratio == pytest.approx(3.0, abs=0.1)


class TestDrawdownMetrics:
    """Test drawdown calculation."""

    def test_max_drawdown(self):
        """Test maximum drawdown calculation."""
        calc = MetricsCalculator()

        # Equity: 100 -> 120 -> 90 -> 110
        # Max DD = (90 - 120) / 120 = -25%
        equity = np.array([100, 120, 90, 110])
        dd = calc.calculate_drawdown_metrics(equity)

        assert dd.max_drawdown == pytest.approx(-0.25, abs=0.01)

    def test_no_drawdown(self):
        """Test with monotonically increasing equity."""
        calc = MetricsCalculator()

        equity = np.array([100, 110, 120, 130])
        dd = calc.calculate_drawdown_metrics(equity)

        assert dd.max_drawdown == 0.0


class TestBESValidation:
    """Test BES-specific validation metrics."""

    def test_es_accuracy(self):
        """Test ES accuracy (realized vs predicted)."""
        calc = MetricsCalculator()

        returns = np.linspace(-0.10, 0.10, 100)
        predicted_es = [-0.095] * 100  # Slightly optimistic

        bes_val = calc.calculate_bes_validation(
            returns, predicted_es_values=predicted_es
        )

        # Accuracy = realized / predicted
        # Should be close to 1.0
        assert 0.8 < bes_val.es_accuracy < 1.2

    def test_kelly_efficiency(self):
        """Test Kelly efficiency calculation."""
        calc = MetricsCalculator()

        returns = np.array([0.01, -0.01, 0.02])
        position_sizes = np.array([2500, 2500, 2500])  # 2.5% of capital
        theoretical_kelly = np.array([0.05, 0.05, 0.05])  # 5% Kelly

        bes_val = calc.calculate_bes_validation(
            returns,
            position_sizes=position_sizes,
            theoretical_kelly=theoretical_kelly,
            capital=100000,
        )

        # Efficiency = 0.025 / 0.05 = 0.5 (50% of Kelly)
        assert bes_val.kelly_efficiency == pytest.approx(0.5, abs=0.1)

    def test_tail_event_frequency(self):
        """Test tail event frequency (should be ~5% for 95% confidence)."""
        calc = MetricsCalculator()

        # 100 returns, worst 5 should be in tail
        returns = np.linspace(-0.10, 0.10, 100)
        bes_val = calc.calculate_bes_validation(returns)

        # Should be close to 5%
        assert bes_val.tail_event_frequency == pytest.approx(0.05, abs=0.02)


class TestVanityMetrics:
    """Test vanity metrics (for VCs only)."""

    def test_win_rate(self):
        """Test win rate calculation."""
        calc = MetricsCalculator()

        # 7 wins, 3 losses = 70% win rate
        returns = np.array([0.01] * 7 + [-0.01] * 3)
        vanity = calc.calculate_vanity_metrics(returns)

        assert vanity.win_rate == pytest.approx(0.7, abs=0.01)

    def test_average_return(self):
        """Test average return."""
        calc = MetricsCalculator()

        returns = np.array([0.02, 0.04, -0.01])
        vanity = calc.calculate_vanity_metrics(returns)

        # Mean = (0.02 + 0.04 - 0.01) / 3 ~ 0.0167
        assert vanity.average_return == pytest.approx(0.0167, abs=0.001)


class TestFullSuite:
    """Test complete metrics calculation."""

    def test_calculate_all(self):
        """Test full suite calculation."""
        calc = MetricsCalculator()

        # Realistic returns
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.02, 252)  # 1 year
        equity = np.cumsum(returns) + 100000

        metrics = calc.calculate_all(
            returns=returns,
            equity_curve=equity,
            regime="Gaussian",
        )

        # Verify all dashboard metrics exist
        assert metrics.profit_factor >= 0
        assert metrics.sortino_ratio != 0
        assert metrics.cvar_95 < 0  # Should be negative
        assert metrics.max_drawdown <= 0  # Should be negative or zero
        assert metrics.tail_ratio >= 0
        assert metrics.total_trades == 252
        assert metrics.regime == "Gaussian"

        # Verify nested metrics
        assert metrics.tail is not None
        assert metrics.bes_validation is not None
        assert metrics.magnitude is not None
        assert metrics.risk_adjusted is not None
        assert metrics.drawdown is not None
        assert metrics.vanity is not None

    def test_to_dict_serialization(self):
        """Test JSON serialization."""
        calc = MetricsCalculator()

        returns = np.array([0.01, -0.01, 0.02])
        metrics = calc.calculate_all(returns)

        # Should serialize without errors
        metrics_dict = metrics.to_dict()

        assert "profit_factor" in metrics_dict
        assert "tail" in metrics_dict
        assert metrics_dict["total_trades"] == 3


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_returns(self):
        """Test with empty returns array."""
        calc = MetricsCalculator()

        metrics = calc.calculate_all(np.array([]))

        # Should return zeros, not crash
        assert metrics.profit_factor == 0.0
        assert metrics.total_trades == 0

    def test_single_return(self):
        """Test with single return."""
        calc = MetricsCalculator()

        metrics = calc.calculate_all(np.array([0.01]))

        # Should handle gracefully
        assert metrics.total_trades == 1

    def test_all_zeros(self):
        """Test with all zero returns."""
        calc = MetricsCalculator()

        metrics = calc.calculate_all(np.array([0.0] * 100))

        # Most metrics should be zero
        assert metrics.profit_factor == 0.0
        assert metrics.expectancy == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
