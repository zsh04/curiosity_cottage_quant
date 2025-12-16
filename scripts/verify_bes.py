import sys
import os
import numpy as np

# Add project root to path
sys.path.append(os.getcwd())

from app.agent.risk.bes import BesSizing


def test_bes():
    print("🧪 Verifying Bayesian Expected Shortfall (BES) Sizing...")

    bes = BesSizing()

    # 1. Test Lambda Calculation
    print("\n1. Testing Lambda (Conviction)...")
    alphas = [1.5, 2.0, 2.5, 3.0, 3.5]
    for a in alphas:
        lam = bes.calculate_lambda(a)
        print(f"   Alpha: {a} -> Lambda: {lam}")
        if a <= 2.0:
            assert lam == 0.0
        elif a > 3.0:
            assert lam == 1.0
        else:
            assert 0.0 < lam <= 1.0
    print("   ✅ Lambda logic confirmed.")

    # 2. Test Expected Shortfall Estimation
    print("\n2. Testing ES Estimation...")
    # Mock forecast: Price 100, forecast range 95-105 centered at 100
    # Sigma approx = (105 - 95) / 2.56 = 10 / 2.56 ~= 3.9
    forecast = {
        "median": np.array([100.0, 100.0]),
        "low": np.array([95.0, 95.0]),
        "high": np.array([105.0, 105.0]),
    }
    es = bes.estimate_es(forecast)
    print(f"   Forecast [95, 105] -> ES: {es:.4f}")
    assert es > 0, "ES should be positive"

    # 3. Test Position Sizing
    print("\n3. Testing Position Sizing...")
    current_price = 100.0
    capital = 100000.0

    # Scenario A: Good Alpha (3.5), Bullish Forecast (102), Safe ES
    print("   Scenario A: Alpha 3.5 (Gaussian), Bullish")
    forecast_bull = {
        "median": np.array([102.0]),  # +2%
        "low": np.array([100.0]),
        "high": np.array([104.0]),  # Narrow spread
    }
    size_a = bes.calculate_size(forecast_bull, 3.5, current_price, capital)
    print(f"   Size: {size_a:.4%}")
    assert size_a > 0, "Should take a position"
    assert size_a <= 0.20, "Should be capped at 20%"

    # Scenario B: Bad Alpha (1.5), Bullish Forecast
    print("   Scenario B: Alpha 1.5 (Levy), Bullish")
    size_b = bes.calculate_size(forecast_bull, 1.5, current_price, capital)
    print(f"   Size: {size_b:.4%}")
    assert size_b == 0.0, "Should be VETOED (0.0)"

    # Scenario C: Good Alpha, High Volatility (Wide spread)
    print("   Scenario C: Alpha 3.5, High Vol")
    forecast_vol = {
        "median": np.array([102.0]),
        "low": np.array([90.0]),
        "high": np.array([114.0]),  # Huge spread
    }
    size_c = bes.calculate_size(forecast_vol, 3.5, current_price, capital)
    print(f"   Size: {size_c:.4%}")
    assert size_c < size_a, "Should take smaller position due to higher risk"

    print("\n✅ All BES tests passed!")


if __name__ == "__main__":
    test_bes()
