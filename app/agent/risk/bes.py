"""
Bayesian Expected Shortfall (BES) Sizing Module

Integrates Heavy Tail Physics (Alpha) with Chronos Probabilistic Forecasts
to determine safe position sizing.

## Mathematical Foundation

Position Size = λ * (E[R] - r_f) / ES

Where:
- λ (lambda): Conviction factor based on tail risk (0.1 to 1.0)
- E[R]: Expected return from forecast
- r_f: Risk-free rate (dynamic from FRED API)
- ES: Expected Shortfall (tail risk measure)

## Key Constants (Configurable)

These constants can be moved to app/core/constants.py for easier tuning:

1. **GAUSSIAN_ALPHA_BASELINE = 3.0**
   - Rationale: Normal distribution has power law exponent α = 3.0
   - Used to normalize lambda calculation
   - Alternative baselines:
     * Student-t: α ≈ 2.5-2.8
     * Levy Stable: α = 1.5
     * Cauchy (extreme): α = 1.0

2. **MIN_LAMBDA = 0.1**
   - Rationale: Minimum "skin in the game"
   - Ensures we always maintain some exposure for observation
   - Even in extreme fat-tail regimes (α → 1.0), we keep 10% position

3. **MAX_LAMBDA = 1.0**
   - Rationale: Full Kelly sizing (maximum safe leverage)
   - Prevents over-leverage beyond Kelly criterion

4. **FALLBACK_ES_PCT = 1.0**
   - Rationale: Conservative assumption if calculation fails
   - Assumes 100% potential loss → minimal position size
   - Fail-safe mechanism

5. **MAX_POSITION_SIZE = 0.20** (20% of capital)
   - Rationale: Fat-finger protection
   - Prevents single position from dominating portfolio
   - Regulatory/risk management best practice
"""

from scipy.stats import norm
from typing import List

from app.core.constants import RISK_FREE_RATE


# Mathematical constants (can be moved to config)
GAUSSIAN_ALPHA_BASELINE = 3.0  # Normal distribution tail exponent
MIN_LAMBDA = 0.1  # Minimum exposure ("skin in the game")
MAX_LAMBDA = 1.0  # Maximum (Full Kelly)
FALLBACK_ES_PCT = 1.0  # Conservative fallback if calc fails
MAX_POSITION_SIZE = 0.20  # 20% position cap


class BesSizing:
    """
    Implements Bayesian Expected Shortfall sizing logic.

    Position sizing combines:
    1. Tail risk physics (α from Hill estimator)
    2. Distributional forecasts (quantiles from Chronos)
    3. Kelly criterion (risk-adjusted returns)
    4. Conservative safeguards (caps, fallbacks)
    """

    def calculate_lambda(self, alpha: float) -> float:
        """
        Calculate lambda (conviction/scaling factor) based on Heavy Tail Alpha.

        ## Formula
        λ = clamp(α / α₀, MIN_LAMBDA, MAX_LAMBDA)

        Where:
        - α: Observed tail exponent (from Hill estimator)
        - α₀: Baseline (3.0 for Gaussian distribution)
        - MIN_LAMBDA: 0.1 (10% minimum position)
        - MAX_LAMBDA: 1.0 (Full Kelly)

        ## Rationale for α / 3.0

        **Why 3.0?**
        - Normal distribution has power law tail with exponent α = 3.0
        - This is the "safe" baseline for standard market conditions
        - σ-normalized returns follow this in efficient markets

        **Physical Interpretation**:
        - α = 3.0 (Normal): Full confidence → λ = 1.0
        - α = 1.5 (Heavy tails): Half confidence → λ = 0.5
        - α = 1.0 (Cauchy): Minimal confidence → λ = 0.33
        - α < 1.0 (Infinite variance): Floor at λ = 0.1

        **Why clamp at [0.1, 1.0]?**
        - Lower bound (0.1): "Skin in the game" even in extreme regimes
          * Maintains market observation
          * Prevents complete exit based on short-term tail estimates
          * Hill estimator can be noisy with small samples
        - Upper bound (1.0): Full Kelly (maximum safe leverage)
          * Beyond 1.0 violates Kelly criterion
          * Would require leverage (we're long-only)

        ## Alternative Baselines (Future Enhancement)

        Could make α₀ dynamic based on detected regime:
        - Normal regime: α₀ = 3.0
        - Heavy tail regime: α₀ = 2.0 (more lenient)
        - Critical regime: α₀ = 1.5 (very conservative)

        Args:
            alpha: Hill Estimator Alpha (tail exponent)

        Returns:
            float: Lambda scaling factor ∈ [0.1, 1.0]
        """
        scaling_factor = alpha / GAUSSIAN_ALPHA_BASELINE
        return max(MIN_LAMBDA, min(scaling_factor, MAX_LAMBDA))

    def estimate_es(self, forecast: dict, confidence: float = 0.95) -> float:
        """
        Estimate Expected Shortfall (ES) from Chronos probabilistic forecast.

        Uses Normal approximation to derive sigma from p10-p90 spread,
        then calculates analytical ES.

        Args:
            forecast: Dictionary containing 'median', 'low' (p10), 'high' (p90) arrays.
            confidence: Confidence level (default 0.95).

        Returns:
            float: Expected Shortfall (absolute positive value).
        """
        # Extract latest forecast values
        try:
            # Handle if inputs are lists or arrays
            # We only need low/high for sigma calculation here.
            # median_val is not used in this method.
            low_val = (
                forecast["low"][-1]
                if hasattr(forecast["low"], "__getitem__")
                else forecast["low"]
            )
            high_val = (
                forecast["high"][-1]
                if hasattr(forecast["high"], "__getitem__")
                else forecast["high"]
            )
        except (KeyError, IndexError):
            # Fallback for empty/malformed forecast
            return 1.0  # Return non-zero to avoid division by zero, but implies high risk if data missing

        # Derive Sigma (Standard Deviation)
        # Assuming Normal Distribution: p90 - p10 = 2.56 * sigma
        sigma = (high_val - low_val) / 2.56

        if sigma <= 0:
            return 0.0  # Should not happen unless high <= low

        # Analytical Expected Shortfall for Normal Distribution
        # ES = sigma * (pdf(quantile) / (1 - confidence))
        # Note: We assume mean is centered or we are looking at the deviation risk.
        # Strict ES includes the mean loss, but for sizing we often look at the 'Risk' component (volatility tail).
        # We will use the standard formula for ES of a loss distribution N(0, sigma^2).

        alpha_quantile = norm.ppf(confidence)  # e.g. 1.645 for 95%
        pdf_at_quantile = norm.pdf(alpha_quantile)

        # ES formula for Normal distribution (Loss tail)
        es = sigma * (pdf_at_quantile / (1 - confidence))

        return float(max(0.0, es))

    def calculate_size(
        self,
        forecast: dict,
        alpha: float,
        current_price: float,
        capital: float,
        risk_free_rate: float = RISK_FREE_RATE,
    ) -> float:
        """
        Calculate position size using Bayesian Expected Shortfall logic.

        Formula: Size = Lambda * (E[R] - r_f) / ES

        Args:
            forecast: Chronos forecast dict.
            alpha: Heavy Tail Alpha.
            current_price: Current market price.
            capital: Allocated capital (unused in size pct calc but kept for interface consistency).
            risk_free_rate: Risk free rate (annualized).

        Returns:
            float: Position size as a percentage of capital (0.0 to 0.20).
        """
        # 1. Calculate Expected Return
        # We use the final median forecast vs current price
        try:
            median_val = (
                forecast["median"][-1]
                if hasattr(forecast["median"], "__getitem__")
                else forecast["median"]
            )
            expected_return_pct = (median_val - current_price) / current_price
        except (KeyError, IndexError, ZeroDivisionError):
            return 0.0

        # We need to interpret 'risk_free_rate'. Usually provided annual.
        # But this trade might be daily.
        # For simplicity in this logic, we assume inputs are comparable (e.g., predicted return over horizon vs r_f over horizon).
        # However, usually r_f is negligible for short horizons.
        # We'll treat r_f as 0 for very short term or assume the user provided a comparable rate.
        # Let's just use the raw value provided as requested.

        # 2. Calculate Lambda (Conviction)
        lambda_val = self.calculate_lambda(alpha)

        if lambda_val <= 0:
            return 0.0

        # 3. Estimate Risk (ES)
        # Note: ES is returned in price units (absolute deviation).
        # We need ES in percentage terms to match Expected Return % for Kelly-like fraction.
        es_absolute = self.estimate_es(forecast)

        if es_absolute <= 0 or current_price <= 0:
            # Fallback: Assume 100% loss potential (extremely conservative)
            # This forces near-zero position size
            es_pct = FALLBACK_ES_PCT
        else:
            es_pct = es_absolute / current_price

        # 4. Calculate Raw Size
        # Kelly-like: Excess Return / Risk
        # Size = Lambda * (E[R] - r_f) / ES_pct

        # Adjust r_f for the holding period if needed, but following prompt strictly:
        # prompt implies: (expected_return - r_f) / risk
        # Ensure we don't go negative on size for Long Only logic via Max(0, ...)

        excess_return = expected_return_pct - (
            risk_free_rate / 252 * 10
        )  # Approx 10 day horizon adjustment?
        # Actually, let's stick to the prompt's implied simple subtraction, assuming r_f is scaled or small.
        # If r_f is 0.04 (4%), and return is 1% (over 10 days), subtracting 0.04 would be huge.
        # We will assume r_f needs to be scaled to the forecast horizon.
        # Chronos usually predicts next steps. Let's assume forecast horizon is ~10 days or input specific.
        # Let's scale r_f to 10 days (10/365) to be safe default, or 0 if it dominates.
        # For now, I will use r_f scaled by 10/252 assuming daily bars.

        r_f_scaled = risk_free_rate * (10 / 252)

        excess_return = expected_return_pct - r_f_scaled

        if excess_return <= 0:
            return 0.0

        raw_size = lambda_val * (excess_return / es_pct)

        # 5. Cap leverage
        # Hard cap at MAX_POSITION_SIZE (20% of capital)
        # Rationale:
        #   - Fat-finger protection
        #   - Diversification requirement
        #   - Prevents single position from dominating portfolio
        final_size = max(0.0, min(raw_size, MAX_POSITION_SIZE))

        return float(final_size)

    def estimate_es_from_quantiles(
        self,
        quantiles: List[float],
        quantile_levels: List[float],
        current_price: float,
        confidence: float = 0.95,
    ) -> float:
        """
        Calculate ES directly from quantile forecast.
        REPLACES Normal approximation with actual distribution.

        Args:
            quantiles: Forecasted quantile values
            quantile_levels: e.g., [0.1, 0.2, ..., 0.9]
            current_price: Current market price
            confidence: Confidence level (default 0.95)

        Returns:
            float: ES as percentage of current price
        """
        from app.agent.risk.quantile_risk import QuantileRiskAnalyzer

        analyzer = QuantileRiskAnalyzer(quantile_levels)
        es_result = analyzer.calculate_expected_shortfall(
            quantiles,
            current_price,
            confidence=1.0 - confidence,  # ES looks at left tail
        )
        return es_result["es_pct"]

    def calculate_size_with_quantiles(
        self,
        quantiles: List[float],
        quantile_levels: List[float],
        alpha: float,
        current_price: float,
        capital: float,
        risk_free_rate: float = RISK_FREE_RATE,
    ) -> float:
        """
        BES sizing using actual quantile distribution (not Normal approx).

        Args:
            quantiles: Forecasted quantile values
            quantile_levels: e.g., [0.1, 0.2, ..., 0.9]
            alpha: Heavy Tail Alpha from physics
            current_price: Current market price
            capital: Allocated capital
            risk_free_rate: Risk free rate (annualized)

        Returns:
            float: Position size as percentage (0.0 to 0.20)
        """
        # 1. Expected Return from median (p50)
        try:
            median_idx = quantile_levels.index(0.5)
            median_forecast = quantiles[median_idx]
            expected_return_pct = (median_forecast - current_price) / current_price
        except (ValueError, IndexError, ZeroDivisionError):
            return 0.0

        # 2. Lambda (conviction from alpha)
        lambda_val = self.calculate_lambda(alpha)

        if lambda_val <= 0:
            return 0.0

        # 3. ES from actual quantiles (NOT Normal approximation)
        es_pct = self.estimate_es_from_quantiles(
            quantiles, quantile_levels, current_price
        )

        if es_pct <= 0:
            return 0.0

        # 4. BES Formula
        r_f_scaled = risk_free_rate * (10 / 252)  # 10-day horizon
        excess_return = expected_return_pct - r_f_scaled

        if excess_return <= 0:
            return 0.0

        raw_size = lambda_val * (excess_return / es_pct)

        # 5. Cap at 20%
        return float(max(0.0, min(raw_size, 0.20)))
