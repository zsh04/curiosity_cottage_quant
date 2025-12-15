import numpy as np
from numpy import typing as npt
from app.agent.state import AgentState
from app.data.aggregator import DataAggregator


class PosteriorDistribution:
    """
    Wrapper for forecast samples to support BES calculation.
    """

    def __init__(self, samples: npt.NDArray):
        self.samples = samples

    def mean(self) -> float:
        return float(np.mean(self.samples))

    def calculate_tail_loss(
        self, percentile: float = 0.05, uncertainty: float = 0.0
    ) -> float:
        """
        Calculates tail loss (ES) with uncertainty adjustment.
        """
        # Widen distribution by uncertainty (Kalman P)
        std_dev = np.sqrt(uncertainty) if uncertainty > 0 else 0
        adjusted_samples = self.samples + np.random.normal(
            0, std_dev, size=self.samples.shape
        )

        sorted_samples = np.sort(adjusted_samples)
        cutoff_index = int(percentile * len(sorted_samples))
        tail_samples = sorted_samples[:cutoff_index]

        if len(tail_samples) == 0:
            return 0.0

        # Expected Shortfall is the negative mean of the tail (loss magnitude)
        # Assuming samples are returns/price changes where negative = loss
        return float(abs(np.mean(tail_samples)))


def calculate_bes_size(posterior_distribution, kalman_covariance_p, hill_alpha):
    """
    Calculates position size using Bayesian Expected Shortfall.
    Constraint: If hill_alpha <= 2.0, return 0.0 (Physics Veto).
    """
    if hill_alpha <= 2.0:
        return 0.0

    physics_scalar = min(
        1.0, max(0.0, hill_alpha - 2.0)
    )  # Scales 0 to 1 between alpha 2 and 3
    expected_return = posterior_distribution.mean()

    # Calculate Tail Loss (BES) at 95% confidence from the posterior
    # Widens if kalman_covariance_p (Uncertainty) is high
    bes_95 = posterior_distribution.calculate_tail_loss(
        percentile=0.05, uncertainty=kalman_covariance_p
    )

    if bes_95 == 0:
        return 0.0

    optimal_size = physics_scalar * (expected_return / bes_95)
    return optimal_size


def calculate_hill_alpha(returns: npt.NDArray, tail_cutoff: float = 0.05) -> float:
    """
    Calculates the Hill Estimator (Alpha) for the tail index.
    Formula: alpha = (1/k * sum(ln(x_i / x_min)))^-1
    """
    abs_returns = np.sort(np.abs(returns))
    n = len(abs_returns)
    k = int(tail_cutoff * n)

    if k < 2:
        return 2.0  # Default to boundary if insufficient samples

    tail_samples = abs_returns[-k:]
    x_min = abs_returns[-(k + 1)] if k < n else tail_samples[0]

    # Avoid log(0)
    tail_samples = tail_samples[tail_samples > 0]
    if len(tail_samples) == 0:
        return 3.0  # Gaussian

    logs = np.log(tail_samples / x_min)
    mean_log = np.mean(logs)

    alpha = 1.0 / mean_log
    return alpha


def get_account_data():
    """
    Fetches real account data via Alpaca.
    """
    aggregator = DataAggregator()
    return aggregator.get_account_data()


def get_physics_scalar(alpha: float) -> float:
    """
    Scales position size based on Constitution v2.1 Laws.
    """
    if alpha <= 2.0:
        return 0.0  # Veto: Infinite Variance
    elif alpha <= 2.1:
        return 0.0  # Safe Buffer near critical point
    elif alpha > 3.0:
        return 1.0  # Gaussian-like, full size
    else:
        # Linear scaling between 2.1 and 3.0
        # 2.1 -> 0.0, 3.0 -> 1.0
        return (alpha - 2.1) / (3.0 - 2.1)


def risk_agent(state: AgentState):
    """
    Risk Agent: Final sizing authority.
    Combines Chronos Forecast, Kalman Uncertainty, and Hill Tail Risk.
    """
    print("--- Risk Agent Reasoning ---")

    candidate_trades = state.get("candidate_trades", [])
    # Mock data for now - In production these come from the State populated by other agents
    # chronos_samples = state.get("market_data", {}).get("forecast_samples", np.random.normal(0, 0.01, 1000))
    # kalman_p = state.get("market_data", {}).get("kalman_p", 0.0001)
    # hill_alpha = state.get("market_data", {}).get("hill_alpha", 2.5)

    # MOCKING Data for the skeleton
    chronos_samples = np.random.normal(
        0.005, 0.02, 1000
    )  # Slight positive drift, 2% vol
    kalman_p = 0.0005
    hill_alpha = 2.2  # Moderately safe

    final_orders = []

    for trade in candidate_trades:
        symbol = trade.get("symbol")
        base_action = trade.get("action")

        # 1. Create Posterior Distribution
        posterior = PosteriorDistribution(chronos_samples)

        # 2. Calculate Sizing via BES
        # calculate_bes_size(posterior_distribution, kalman_covariance_p, hill_alpha)
        # Note: calculate_bes_size returns a 'size' factor (like Kelly fraction).
        # We need to interpret it. The formula is optimal_size = scalar * (ret / bes).
        # This is typically a leverage factor or fraction of equity.

        target_fraction = calculate_bes_size(posterior, kalman_p, hill_alpha)
        print(f"[{symbol}] BES Target Fraction: {target_fraction:.4f}")

        # 3. Sizing
        account_equity = 100000.0

        # Apply fraction to equity
        final_dollar_val = account_equity * target_fraction

        # Cap at 10% of account explicitly (Safety) - strictly enforced
        final_dollar_val = min(final_dollar_val, account_equity * 0.10)
        final_dollar_val = max(0.0, final_dollar_val)

        price = 150.0  # Mock price
        qty = int(final_dollar_val / price)

        if qty > 0:
            final_orders.append(
                {
                    "symbol": symbol,
                    "qty": qty,
                    "side": str(base_action or "").lower(),
                    "type": "market",
                    "reason": f"BES_Alloc:{target_fraction:.3f}, Alpha:{hill_alpha}",
                }
            )
            print(f"[{symbol}] Sized Order: {qty} shares (${final_dollar_val:.2f})")
        else:
            print(f"[{symbol}] Trade Rejected by Risk Agent.")

    return {"final_orders": final_orders, "next_step": "END"}
