import logging
import time
import sys
import os
import numpy as np
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.insert(0, os.getcwd())

from app.agent.nodes.risk import RiskManager, AgentState, TradingStatus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VERIFY_PORTFOLIO")

# Bypass Alpaca Logic (though we mock MarketAdapter anyway)
os.environ["ALPACA_API_KEY"] = "pk_dummy"
os.environ["ALPACA_API_SECRET"] = "sk_dummy"


def verify_portfolio_risk():
    print("🚀 Starting Portfolio Risk & Entanglement Verification...")

    # 1. Setup Mock State with Portfolio
    portfolio = [
        {"symbol": "SPY", "qty": 10},  # Existing Position
    ]

    state_correlated = {
        "status": TradingStatus.ACTIVE,
        "symbol": "IVV",  # Highly Correlated with SPY
        "price": 500.0,
        "current_alpha": 3.0,
        "chronos_forecast": {"median": [510.0], "low": [500.0], "high": [520.0]},
        "current_positions": portfolio,
        "nav": 100000.0,
        "max_drawdown": 0.0,
        "messages": [],
    }

    state_uncorrelated = {
        "status": TradingStatus.ACTIVE,
        "symbol": "GLD",  # Uncorrelated with SPY (Assume)
        "price": 200.0,
        "current_alpha": 3.0,
        "chronos_forecast": {
            "median": [210.0],  # 5% return
            "low": [195.0],
            "high": [215.0],
        },
        "current_positions": portfolio,
        "nav": 100000.0,
        "max_drawdown": 0.0,
        "messages": [],
    }

    # 2. Mock Market Adapter History
    # We need to simulate history for SPY, IVV (Correlated), GLD (Uncorrelated)
    dates = np.linspace(0, 100, 100)

    # SPY: Sine wave
    spy_hist = np.sin(dates) + 10

    # IVV: Same Sine wave (Corr ~ 1.0)
    ivv_hist = np.sin(dates) + 10.1

    # GLD: Cosine wave (Corr ~ 0)
    gld_hist = np.cos(dates) + 5

    def mock_get_history(symbol, limit=100):
        if symbol == "SPY":
            return list(spy_hist)
        if symbol == "IVV":
            return list(ivv_hist)
        if symbol == "GLD":
            return list(gld_hist)
        return []

    # 3. Patch MarketService inside RiskManager
    with patch("app.services.market.MarketAdapter") as MockAdapter:
        MockAdapter.return_value.get_price_history.side_effect = mock_get_history

        manager = RiskManager()

        # --- TEST 1: Correlated Asset (IVV vs SPY) ---
        print("\n🧪 Test 1: Correlated Asset (IVV vs SPY)")
        size_corr = manager.size_position(state_correlated)
        print(f"Size (IVV): ${size_corr:.2f}")

        if size_corr == 0.0:
            print("✅ SUCCESS: High Entanglement caused VETO/Zero Size.")
        elif size_corr < 1000:  # Assuming minimal size due to penalty
            print("✅ SUCCESS: Size heavily penalized.")
        else:
            print(f"❌ FAILURE: Size {size_corr} too high for correlated asset.")

        # --- TEST 2: Uncorrelated Asset (GLD vs SPY) ---
        print("\n🧪 Test 2: Uncorrelated Asset (GLD vs SPY)")
        size_uncorr = manager.size_position(state_uncorrelated)
        print(f"Size (GLD): ${size_uncorr:.2f}")

        if size_uncorr > size_corr:
            print("✅ SUCCESS: Uncorrelated asset received larger allocation.")
        else:
            print("❌ FAILURE: Uncorrelated asset did not get preference.")


if __name__ == "__main__":
    verify_portfolio_risk()
