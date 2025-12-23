"""
Quantile-Based Risk Analytics

Leverages full quantile distribution from Chronos forecasts for:
- Value at Risk (VaR)
- Expected Shortfall (ES/CVaR)
- Distributional confidence calibration
- Scenario-based stress testing

No parametric assumptions - uses actual forecasted quantiles.
"""

import numpy as np
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class QuantileRiskAnalyzer:
    """
    Risk analytics using full quantile distribution from Chronos.
    No parametric assumptions - uses actual forecasted quantiles.
    """

    # Chronos-bolt default quantile levels
    DEFAULT_QUANTILE_LEVELS = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]

    def __init__(self, quantile_levels: Optional[List[float]] = None):
        """
        Args:
            quantile_levels: e.g., [0.1, 0.2, ..., 0.9]
                            Defaults to Chronos-bolt's 9 quantiles
        """
        self.quantile_levels = quantile_levels or self.DEFAULT_QUANTILE_LEVELS

    def calculate_var(
        self,
        quantiles: List[float],
        current_price: float,
        confidence: float = 0.10,
    ) -> Dict[str, float]:
        """
        Value at Risk from quantile forecast.

        Args:
            quantiles: Forecasted quantile values
            current_price: Current asset price
            confidence: Confidence level (default 0.10 = 90% VaR)

        Returns:
            {
                "var_absolute": Loss amount at confidence level,
                "var_pct": Loss as % of current price,
                "var_quantile": The quantile value itself,
                "confidence_level": Actual confidence used
            }
        """
        # Find closest quantile to confidence level
        idx = np.argmin(np.abs(np.array(self.quantile_levels) - confidence))
        var_value = quantiles[idx]

        loss_absolute = current_price - var_value
        loss_pct = loss_absolute / current_price if current_price > 0 else 0.0

        return {
            "var_absolute": max(0.0, loss_absolute),
            "var_pct": max(0.0, loss_pct),
            "var_quantile": var_value,
            "confidence_level": self.quantile_levels[idx],
        }

    def calculate_expected_shortfall(
        self, quantiles: List[float], current_price: float, confidence: float = 0.10
    ) -> Dict[str, float]:
        """
        Expected Shortfall (CVaR) from quantile forecast.
        DIRECT from quantiles - no parametric assumptions!

        ES = Average of quantiles below confidence level

        Args:
            quantiles: Forecasted quantile values
            current_price: Current asset price
            confidence: Confidence level (default 0.10 = tail risk below 10%)

        Returns:
            {
                "es_absolute": Expected loss in tail,
                "es_pct": Expected loss as % of price,
                "es_value": Average quantile value in tail,
                "tail_quantiles_count": Number of quantiles averaged
            }
        """
        # Get all quantiles below confidence threshold
        tail_mask = np.array(self.quantile_levels) <= confidence

        if not np.any(tail_mask):
            # Fallback: use lowest quantile
            tail_quantiles = [quantiles[0]]
        else:
            tail_quantiles = np.array(quantiles)[tail_mask]

        es_value = np.mean(tail_quantiles)
        loss_absolute = current_price - es_value
        loss_pct = loss_absolute / current_price if current_price > 0 else 0.0

        return {
            "es_absolute": max(0.0, loss_absolute),
            "es_pct": max(0.0, loss_pct),
            "es_value": es_value,
            "tail_quantiles_count": len(tail_quantiles),
        }

    def calculate_distributional_confidence(
        self, quantiles: List[float]
    ) -> Dict[str, float]:
        """
        Measure forecast uncertainty from quantile spread.
        Tight distribution = High confidence in forecast.

        Args:
            quantiles: Forecasted quantile values

        Returns:
            {
                "iqr": Interquartile range,
                "full_range": p90 - p10,
                "cv": Coefficient of variation (spread/median),
                "confidence_score": 0-1 score (higher = more confident),
                "median": Median forecast
            }
        """
        q_array = np.array(quantiles)

        # For 9 quantiles: [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
        # p25 ≈ index 1 (0.2), p75 ≈ index 7 (0.8)
        iqr = q_array[7] - q_array[1] if len(q_array) >= 8 else q_array[-1] - q_array[0]

        # Full range (p90 - p10)
        full_range = q_array[-1] - q_array[0]

        # Median for normalization
        median_idx = len(q_array) // 2
        median = q_array[median_idx]

        # Coefficient of variation (normalized spread)
        cv = full_range / median if median > 0 else float("inf")

        # Confidence score (inverse of spread)
        # Lower CV = Higher confidence
        confidence_score = 1.0 / (1.0 + cv)

        return {
            "iqr": iqr,
            "full_range": full_range,
            "cv": cv,
            "confidence_score": confidence_score,  # 0-1
            "median": median,
        }

    def build_scenario_analysis(
        self, quantiles: List[float], current_price: float
    ) -> Dict[str, Dict[str, Any]]:
        """
        Build scenario-based stress test from quantiles.

        Args:
            quantiles: Forecasted quantile values
            current_price: Current asset price

        Returns:
            Dictionary of scenarios with returns and labels
        """
        scenarios = {
            "bear_case": {
                "quantile": quantiles[0],  # p10
                "return_pct": (
                    (quantiles[0] - current_price) / current_price
                    if current_price > 0
                    else 0.0
                ),
                "label": "Worst 10%",
            },
            "conservative": {
                "quantile": quantiles[1],  # p20
                "return_pct": (
                    (quantiles[1] - current_price) / current_price
                    if current_price > 0
                    else 0.0
                ),
                "label": "Worst 20%",
            },
            "base_case": {
                "quantile": quantiles[4],  # p50
                "return_pct": (
                    (quantiles[4] - current_price) / current_price
                    if current_price > 0
                    else 0.0
                ),
                "label": "Median",
            },
            "bull_case": {
                "quantile": quantiles[8],  # p90
                "return_pct": (
                    (quantiles[8] - current_price) / current_price
                    if current_price > 0
                    else 0.0
                ),
                "label": "Best 10%",
            },
        }

        # Risk/reward asymmetry
        downside_p10 = abs(scenarios["bear_case"]["return_pct"])
        upside_p90 = max(0, scenarios["bull_case"]["return_pct"])

        risk_reward_ratio = upside_p90 / downside_p10 if downside_p10 > 0 else 0.0

        scenarios["summary"] = {
            "risk_reward_ratio": risk_reward_ratio,
            "skewness_indicator": upside_p90 - downside_p10,  # Positive = upside bias
        }

        return scenarios

    def get_tail_risk_multiplier(
        self, quantiles: List[float], current_price: float
    ) -> float:
        """
        Calculate tail risk penalty for position sizing.
        Higher tail risk = Lower position size.

        Returns:
            float: Multiplier between 0.0 and 1.0
        """
        es_metrics = self.calculate_expected_shortfall(quantiles, current_price)
        var_metrics = self.calculate_var(quantiles, current_price)

        # If ES >> VaR, we have fat tails
        if var_metrics["var_pct"] > 0:
            tail_fatness = es_metrics["es_pct"] / var_metrics["var_pct"]
            # Penalize if ES is much larger than VaR (fat tails)
            # Normal distribution: ES/VaR ≈ 1.15
            # Fat tails: ES/VaR > 1.5
            penalty = max(0.5, min(1.0, 1.15 / tail_fatness))
        else:
            penalty = 1.0

        return penalty
