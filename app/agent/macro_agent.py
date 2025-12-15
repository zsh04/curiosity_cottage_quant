from app.agent.state import AgentState
from app.agent.models import model_factory
from app.data.aggregator import DataAggregator


import numpy as np


def get_market_context():
    """
    Mock function to get market context.
    Fetches real market data via DataAggregator.
    """
    aggregator = DataAggregator()
    return aggregator.get_macro_context()


def calculate_hurst_exponent(price_series: list) -> float:
    """
    Calculates the Hurst Exponent (H) via RS Analysis.
    Reference: Constitution v2.1
    """
    prices = np.array(price_series)
    if len(prices) < 32:
        return 0.5  # Insufficient data

    # Use log returns
    returns = np.diff(np.log(prices))

    # Range of lag scales
    min_lag = 10
    max_lag = len(returns) // 2
    lags = range(min_lag, max_lag, 5)

    rs_values = []

    for lag in lags:
        # Split into chunks
        # Simplified: Calculate R/S for single window of size 'lag'?
        # Better: Average R/S over all non-overlapping chunks of size 'lag'

        daily_rs = []
        for i in range(0, len(returns) - lag, lag):
            chunk = returns[i : i + lag]
            if len(chunk) < lag:
                continue

            mean = np.mean(chunk)
            centered = chunk - mean
            cumulative = np.cumsum(centered)
            range_val = np.max(cumulative) - np.min(cumulative)
            std_val = np.std(chunk)

            if std_val == 0:
                continue
            daily_rs.append(range_val / std_val)

        if daily_rs:
            rs_values.append(np.mean(daily_rs))
        else:
            rs_values.append(np.nan)

    # Clean data for regression
    valid_lags = [
        lag for lag, rs in zip(lags, rs_values) if not np.isnan(rs) and rs > 0
    ]
    valid_rs = [rs for rs in rs_values if not np.isnan(rs) and rs > 0]

    if len(valid_lags) < 3:
        return 0.5

    # Log-Log Regression
    log_lags = np.log(valid_lags)
    log_rs = np.log(valid_rs)

    h_val, _ = np.polyfit(log_lags, log_rs, 1)
    return h_val


def macro_agent(state: AgentState):
    """
    Macro Agent: Determines Market Regime and Target Sectors.
    Uses Chronos for forecasting and Gemma 2 for synthesis.
    Integrates Fractal Memory (Hurst) for Regime State.
    """
    print("--- Macro Agent Reasoning ---")

    # 1. Fetch Data
    context = get_market_context()

    # 2. Physics Layer: Fractal Memory (Hurst)
    hurst = calculate_hurst_exponent(context.get("SPY_History", []))

    physics_regime = "RANDOM WALK (Cash)"
    if hurst > 0.55:
        physics_regime = "PERSISTENT (Trend Following)"
    elif hurst < 0.45:
        physics_regime = "ANTI-PERSISTENT (Mean Reversion)"

    print(f"Fractal Memory (H): {hurst:.3f} -> {physics_regime}")

    # 3. Get Forecast (Chronos)
    chronos_forecast = model_factory.forecast_series(context)  # Passing ctx for now
    print(f"Chronos Forecast: {chronos_forecast}")

    # 4. Construct Prompt for Gemma
    prompt = f"""You are a Macro Strategist.
    Analyze the market data, Fractal Physics, and Forecast:

    Market Data: {context["Sector_Performance"]}
    Fractal State (Hurst={hurst:.2f}): {physics_regime}
    Forecast Model Output: {chronos_forecast}

    Determine:
    1. Market Regime (BULLISH, BEARISH, NEUTRAL, VOLATILE)
    2. Top 2 Target Sectors.

    Output concise reasoning and then the classification.
    Formulate your answer as JSON-like structure if possible.
    """

    # 5. Call Gemma 2 via ModelFactory
    response_content = model_factory.generate_thought(prompt)
    print(f"Macro Analysis (Gemma): {response_content}")

    # Simple heuristic parsing (Gemma 2 is good at following instruction)
    regime = "NEUTRAL"
    if "BULLISH" in response_content.upper():
        regime = "BULLISH"
    elif "BEARISH" in response_content.upper():
        regime = "BEARISH"

    sectors = []
    if "TECH" in response_content.upper() or "XLK" in response_content.upper():
        sectors.append("Technology")
    if "ENERGY" in response_content.upper() or "XLE" in response_content.upper():
        sectors.append("Energy")

    if not sectors:
        sectors = ["Technology", "Healthcare"]

    return {
        "market_regime": regime,
        "target_sectors": sectors,
        "reasoning_trace": [
            f"Macro (Gemma): {response_content}",
            f"Physics (Hurst): {hurst:.2f}",
        ],
        "next_step": "analyst",
    }
