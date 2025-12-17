import asyncio
import logging
import sys
from unittest.mock import MagicMock

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VERIFY_TOURNAMENT")

# Import Agent Structures (Must import Risk after mocking if possible, or patch it)
from app.agent.state import AgentState, TradingStatus


# Mock Reasoning Service (To bypass LLM)
def mock_arbitrate(reports):
    logger.info(f"MOCK ARBITER: Received {len(reports)} reports.")
    sorted_reps = sorted(
        reports, key=lambda x: x.get("signal_confidence", 0), reverse=True
    )
    winner = sorted_reps[0]
    return {
        "winner_symbol": winner["symbol"],
        "rationale": f"Mock Arbitration chose {winner['symbol']} (Conf {winner.get('signal_confidence')})",
    }


async def run_verification():
    logger.info("--- 🧪 STARTING TOURNAMENT VERIFICATION 🧪 ---")

    # 1. Patch Reasoning Service BEFORE importing risk node
    # This ensures that when risk_node imports ReasoningService, it gets our mock
    mock_class = MagicMock()
    mock_class.arbitrate_tournament = mock_arbitrate

    # We need to mock the MODULE 'app.services.reasoning'
    mock_reasoning_module = MagicMock()
    mock_reasoning_module.ReasoningService = (
        lambda: mock_class
    )  # Return instance with method
    sys.modules["app.services.reasoning"] = mock_reasoning_module

    # Also mock MarketService/Config since RiskManager instantiates them and they might fail without keys
    mock_market_module = MagicMock()
    sys.modules["app.services.market"] = mock_market_module

    # NOW import risk
    from app.agent.nodes.risk import risk_node

    # 2. PROMPT: Multi-Candidate State (Superposition)
    state = AgentState(
        status=TradingStatus.ACTIVE,
        analysis_reports=[
            {
                "symbol": "AAPL",
                "signal_side": "BUY",
                "signal_confidence": 0.85,
                "price": 150.0,
                "velocity": 0.05,
                "current_alpha": 1.9,  # Volatile
                "regime": "Fractional",
                "success": True,
            },
            {
                "symbol": "TSLA",
                "signal_side": "SELL",
                "signal_confidence": 0.92,
                "price": 250.0,
                "velocity": -0.10,
                "current_alpha": 1.4,  # Critical-ish
                "regime": "Lévy Stable",
                "success": True,
            },
        ],
        nav=100000.0,
        cash=100000.0,
        current_positions=[],
    )

    logger.info("Step 1: Running Risk Node with Multi-Candidate State...")
    try:
        new_state = risk_node(state)
    except Exception as e:
        logger.exception("Risk Node Crashed during verification")
        exit(1)

    # 3. Validation
    winner = new_state.get("symbol")
    side = new_state.get("signal_side")
    reasoning = new_state.get("reasoning")

    logger.info(f"Resulting State Symbol: {winner}")
    logger.info(f"Resulting State Side: {side}")
    logger.info(f"Resulting State Reasoning: {reasoning}")

    if winner == "TSLA":
        logger.info(
            "✅ PASS: Risk Node correctly selected the higher confidence winner (TSLA)."
        )
    else:
        logger.error(f"❌ FAIL: Expected TSLA, got {winner}")
        exit(1)

    if "[TOURNAMENT WINNER]" in reasoning or "[TOURNAMENT WINNER]" in reasoning.upper():
        logger.info("✅ PASS: Reasoning reflects Tournament source.")
    else:
        logger.warning(f"⚠️ Check Reasoning format: {reasoning}")

    logger.info("--- VERIFICATION COMPLETE ---")


if __name__ == "__main__":
    asyncio.run(run_verification())
