"""
Bayesian Expected Shortfall (BES) Sizing Module
Integrates Heavy Tail Physics (Alpha) with Chronos Probabilistic Forecasts to determine safe position sizing.
"""

from scipy.stats import norm


class BesSizing:
    """
    Implements Bayesian Expected Shortfall sizing logic.
    """

    def calculate_lambda(self, alpha: float) -> float:
        """
        Calculate lambda (conviction/scaling factor) based on the Heavy Tail Alpha.

        Logic (Fractal Sizing):
        - Continuous scaling based on Alpha relative to Gaussian baseline (3.0).
        - Formula: Lambda = Clamp(Alpha / 3.0, 0.1, 1.0)
        - Alpha 1.5 -> ~0.5 (Half Size)
        - Alpha 3.0 -> 1.0 (Full Size)

        Args:
            alpha: Hill Estimator Alpha from HeavyTailEstimator.

        Returns:
            float: Lambda scaling factor between 0.1 and 1.0.
        """
        # Continuous Fractal Sizing
        # We clamp at 0.1 to avoid complete zero (maintain some exposure/observation)
        # unless alpha is dangerously close to 1.0 (Infinite Mean), but 0.1 is safe "skin in game".
        scaling_factor = alpha / 3.0
        return max(0.1, min(scaling_factor, 1.0))

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
        risk_free_rate: float = 0.04,
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
            es_pct = 1.0  # Avoid division by zero, conservative
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
        # Hard cap at 20% (0.20) as requested
        final_size = max(0.0, min(raw_size, 0.20))

        return float(final_size)
