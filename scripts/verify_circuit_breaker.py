import sys
import os
import logging

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# --- AGGRESSIVE MOCKING ---
from unittest.mock import MagicMock
import sys

# Mock 3rd party
sys.modules["numpy"] = MagicMock()
sys.modules["pandas"] = MagicMock()
sys.modules["scipy"] = MagicMock()
sys.modules["scipy.stats"] = MagicMock()
sys.modules["langgraph"] = MagicMock()
sys.modules["langgraph.graph"] = MagicMock()

# Mock Internal Logic Components not under test
sys.modules["app.agent.graph"] = MagicMock()
sys.modules["app.agent.risk.bes"] = MagicMock()
sys.modules["app.services.global_state"] = MagicMock()

# Define Regime Mock for import
from enum import Enum


class Regime(str, Enum):
    GAUSSIAN = "Gaussian"
    LEVY_STABLE = "Lévy Stable"
    CRITICAL = "Critical"


# Patch physics module
physics_mock = MagicMock()
physics_mock.Regime = Regime
sys.modules["app.lib.physics"] = physics_mock

# Now import RiskManager - logic under test
# We might need to patch imports INSIDE risk.py if they are 'from x import y'
# But sys.modules injection should handle 'from app.lib.physics import Regime'

from app.agent.nodes.taleb import risk_node, RiskManager
from app.agent.state import AgentState, TradingStatus

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CircuitBreakerTest")


def test_circuit_breaker():
    manager = RiskManager()

    # CASE 1: Safe State (1% Drawdown)
    safe_state: AgentState = {
        "nav": 99000.0,
        "starting_capital": 100000.0,
        "max_drawdown": 0.0,
        "status": TradingStatus.ACTIVE,
        "messages": [],
        # Dummy fields
        "cash": 99000.0,
        "daily_pnl": -1000.0,
        "current_alpha": 3.5,
        "symbol": "SPY",
        "price": 500.0,
        "historic_returns": [],
        "regime": "Gaussian",
        "chronos_forecast": {},
        "signal_side": "BUY",
        "signal_confidence": 0.8,
        "reasoning": "Test",
        "approved_size": 100.0,
        "risk_multiplier": 1.0,
    }

    logger.info("🧪 TEST 1: Testing Safe State (1% Drawdown)...")
    result_safe = manager.check_circuit_breaker(safe_state)

    if result_safe["status"] == TradingStatus.ACTIVE:
        logger.info("✅ PASS: System remained ACTIVE under 1% drawdown.")
    else:
        logger.error(
            f"❌ FAIL: System halted incorrectly. Status: {result_safe['status']}"
        )

    # CASE 2: Breached State (2.5% Drawdown)
    breached_state: AgentState = {
        "nav": 97500.0,
        "starting_capital": 100000.0,
        "max_drawdown": 0.0,  # Should update
        "status": TradingStatus.ACTIVE,
        "messages": [],
        # Dummy fields
        "cash": 97500.0,
        "daily_pnl": -2500.0,
        "current_alpha": 3.5,
        "symbol": "SPY",
        "price": 500.0,
        "historic_returns": [],
        "regime": "Gaussian",
        "chronos_forecast": {},
        "signal_side": "BUY",
        "signal_confidence": 0.8,
        "reasoning": "Test",
        "approved_size": 100.0,
        "risk_multiplier": 1.0,
    }

    logger.info("\n🧪 TEST 2: Testing Breached State (2.5% Drawdown)...")
    result_breached = manager.check_circuit_breaker(breached_state)

    if result_breached["status"] == TradingStatus.HALTED_DRAWDOWN:
        logger.info("✅ PASS: System HALTED correctly under 2.5% drawdown.")
        if result_breached["approved_size"] == 0.0:
            logger.info("✅ PASS: Approved Size forced to 0.0.")
        else:
            logger.error(
                f"❌ FAIL: Size not zeroed out. Size: {result_breached['approved_size']}"
            )

        # Check max_drawdown updated
        expected_dd = (100000 - 97500) / 100000  # 0.025
        if abs(result_breached["max_drawdown"] - 0.025) < 0.0001:
            logger.info(
                f"✅ PASS: Max Drawdown updated correctly to {result_breached['max_drawdown']:.3f}"
            )
        else:
            logger.error(
                f"❌ FAIL: Max Drawdown calc error. Got {result_breached['max_drawdown']}"
            )

    else:
        logger.error(f"❌ FAIL: System NOT halted. Status: {result_breached['status']}")


if __name__ == "__main__":
    test_circuit_breaker()
