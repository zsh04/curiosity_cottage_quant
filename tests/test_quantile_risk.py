"""
Unit Tests for QuantileRiskAnalyzer

Tests all risk metrics calculations from quantile distributions.
"""

import pytest
import numpy as np
from app.agent.risk.quantile_risk import QuantileRiskAnalyzer


class TestQuantileRiskAnalyzer:
    """Test suite for QuantileRiskAnalyzer"""

    @pytest.fixture
    def analyzer(self):
        """Create analyzer with standard 9 quantile levels"""
        return QuantileRiskAnalyzer([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9])

    @pytest.fixture
    def sample_quantiles(self):
        """Sample quantile values for a $100 asset"""
        # Symmetric distribution centered at $100
        return [90.0, 92.0, 94.0, 96.0, 100.0, 104.0, 106.0, 108.0, 110.0]

    @pytest.fixture
    def skewed_quantiles(self):
        """Skewed distribution (downside risk)"""
        # Fat left tail, thin right tail
        return [80.0, 88.0, 92.0, 96.0, 100.0, 103.0, 105.0, 107.0, 109.0]

    def test_var_calculation(self, analyzer, sample_quantiles):
        """Test VaR calculation at 90% confidence"""
        current_price = 100.0

        var_metrics = analyzer.calculate_var(
            sample_quantiles, current_price, confidence=0.10
        )

        # VaR should be p10 quantile (90.0)
        assert var_metrics["var_quantile"] == 90.0
        # Loss = 100 - 90 = 10
        assert var_metrics["var_absolute"] == 10.0
        # Loss pct = 10/100 = 10%
        assert abs(var_metrics["var_pct"] - 0.10) < 0.01
        assert var_metrics["confidence_level"] == 0.1

    def test_expected_shortfall_calculation(self, analyzer, sample_quantiles):
        """Test ES calculation (average of tail)"""
        current_price = 100.0

        es_metrics = analyzer.calculate_expected_shortfall(
            sample_quantiles, current_price, confidence=0.10
        )

        # ES should be average of p10 (90.0)
        # Since we only have p10 in the 10% tail
        assert es_metrics["es_value"] == 90.0
        assert es_metrics["es_absolute"] == 10.0
        assert abs(es_metrics["es_pct"] - 0.10) < 0.01
        assert es_metrics["tail_quantiles_count"] == 1

    def test_distributional_confidence_tight(self, analyzer):
        """Test confidence with tight distribution (high confidence)"""
        # Very tight distribution
        tight_quantiles = [99.0, 99.2, 99.4, 99.6, 100.0, 100.4, 100.6, 100.8, 101.0]

        conf_metrics = analyzer.calculate_distributional_confidence(tight_quantiles)

        # IQR should be small (p80 - p20)
        iqr = 100.8 - 99.2
        assert abs(conf_metrics["iqr"] - iqr) < 0.01

        # CV should be low
        assert conf_metrics["cv"] <= 0.02

        # Confidence should be high (inverse of CV)
        assert conf_metrics["confidence_score"] > 0.98
        assert conf_metrics["median"] == 100.0

    def test_distributional_confidence_wide(self, analyzer):
        """Test confidence with wide distribution (low confidence)"""
        # Very wide distribution
        wide_quantiles = [50.0, 60.0, 70.0, 80.0, 100.0, 120.0, 130.0, 140.0, 150.0]

        conf_metrics = analyzer.calculate_distributional_confidence(wide_quantiles)

        # IQR should be large
        iqr = 140.0 - 60.0
        assert abs(conf_metrics["iqr"] - iqr) < 0.01

        # CV should be high
        assert conf_metrics["cv"] > 0.5

        # Confidence should be low
        assert conf_metrics["confidence_score"] < 0.7

    def test_scenario_analysis(self, analyzer, sample_quantiles):
        """Test scenario generation"""
        current_price = 100.0

        scenarios = analyzer.build_scenario_analysis(sample_quantiles, current_price)

        # Check scenarios exist
        assert "bear_case" in scenarios
        assert "conservative" in scenarios
        assert "base_case" in scenarios
        assert "bull_case" in scenarios
        assert "summary" in scenarios

        # Bear case should be p10
        assert scenarios["bear_case"]["quantile"] == 90.0
        assert scenarios["bear_case"]["return_pct"] == -0.10

        # Base case should be p50
        assert scenarios["base_case"]["quantile"] == 100.0
        assert scenarios["base_case"]["return_pct"] == 0.0

        # Bull case should be p90
        assert scenarios["bull_case"]["quantile"] == 110.0
        assert abs(scenarios["bull_case"]["return_pct"] - 0.10) < 0.01

        # Risk/Reward should be symmetric (1.0)
        summary = scenarios["summary"]
        assert abs(summary["risk_reward_ratio"] - 1.0) < 0.1
        assert abs(summary["skewness_indicator"]) < 0.01  # Symmetric

    def test_scenario_analysis_skewed(self, analyzer, skewed_quantiles):
        """Test scenarios with skewed distribution"""
        current_price = 100.0

        scenarios = analyzer.build_scenario_analysis(skewed_quantiles, current_price)

        # Bear case worse than bull case (fat left tail)
        bear_return = abs(scenarios["bear_case"]["return_pct"])
        bull_return = scenarios["bull_case"]["return_pct"]

        assert bear_return > bull_return  # Downside > Upside

        # Risk/Reward should be < 1.0 (more downside risk)
        summary = scenarios["summary"]
        assert summary["risk_reward_ratio"] < 1.0

        # Skewness should be negative (downside bias)
        assert summary["skewness_indicator"] < 0.0

    def test_tail_risk_multiplier(self, analyzer, sample_quantiles):
        """Test tail risk penalty calculation"""
        current_price = 100.0

        multiplier = analyzer.get_tail_risk_multiplier(sample_quantiles, current_price)

        # For Normal-like distribution, ES/VaR ≈ 1.15
        # Multiplier should be close to 1.0 (no penalty)
        assert 0.9 < multiplier <= 1.0

    def test_tail_risk_multiplier_fat_tails(self, analyzer, skewed_quantiles):
        """Test tail risk penalty with fat tails"""
        current_price = 100.0

        multiplier = analyzer.get_tail_risk_multiplier(skewed_quantiles, current_price)

        # Fat tails → ES >> VaR → Higher penalty → Lower multiplier
        # Note: Skewed ≠ fat tails necessarily
        assert multiplier <= 1.0
        assert multiplier >= 0.5  # Shouldn't be too aggressive

    def test_var_at_different_confidence_levels(self, analyzer, sample_quantiles):
        """Test VaR at various confidence levels"""
        current_price = 100.0

        # 90% confidence (p10)
        var_90 = analyzer.calculate_var(
            sample_quantiles, current_price, confidence=0.10
        )
        assert var_90["var_quantile"] == 90.0

        # 80% confidence (p20)
        var_80 = analyzer.calculate_var(
            sample_quantiles, current_price, confidence=0.20
        )
        assert abs(var_80["var_quantile"] - 92.0) < 0.01

        # 50% confidence (p50) - median
        var_50 = analyzer.calculate_var(
            sample_quantiles, current_price, confidence=0.50
        )
        assert var_50["var_quantile"] == 100.0

    def test_empty_quantiles(self, analyzer):
        """Test handling of empty quantiles"""
        with pytest.raises((IndexError, ValueError)):
            analyzer.calculate_var([], 100.0)

    def test_zero_price(self, analyzer, sample_quantiles):
        """Test handling of zero current price"""
        var_metrics = analyzer.calculate_var(sample_quantiles, 0.0)

        # Should return 0 loss pct (avoid division by zero)
        assert var_metrics["var_pct"] == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
