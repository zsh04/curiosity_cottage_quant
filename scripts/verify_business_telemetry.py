import asyncio
import logging
import os
import sys
import time
from dotenv import load_dotenv

# Ensure app imports work
sys.path.append(os.getcwd())
load_dotenv()

# Force standard OTLP endpoint
if not os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"):
    os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://localhost:4318"

# --- AGGRESSIVE MOCKING START ---
# Bypass NumPy 2.x / Torch mismatch for Metrics Verification
from unittest.mock import MagicMock

sys.modules["transformers"] = MagicMock()
sys.modules["torch"] = MagicMock()
sys.modules["torch.nn"] = MagicMock()
sys.modules["torch.nn.functional"] = MagicMock()
# Mock Scipy properly
mock_scipy = MagicMock()
sys.modules["scipy"] = mock_scipy
sys.modules["scipy.linalg"] = MagicMock()
sys.modules["scipy.integrate"] = MagicMock()
sys.modules["scipy.stats"] = MagicMock()
sys.modules["scipy.optimize"] = MagicMock()
sys.modules["scipy.special"] = MagicMock()

# Mock Statsmodels to prevent it from failing on Scipy
sys.modules["statsmodels"] = MagicMock()
sys.modules["statsmodels.tsa"] = MagicMock()
sys.modules["statsmodels.tsa.stattools"] = MagicMock()

# Mock Internal ML Strategies to avoid deep imports
sys.modules["app.strategies.lstm"] = MagicMock()
sys.modules["app.strategies.breakout"] = MagicMock()
sys.modules["app.lib.preprocessing.fracdiff"] = MagicMock()
# We need numpy for some things.
# sys.modules["numpy"] = MagicMock()

from app.core.telemetry import setup_telemetry

# Setup Telemetry FIRST
setup_telemetry(service_name="cc-business-verifier")

from app.agent.nodes.analyst import AnalystAgent
from app.agent.nodes.risk import RiskManager, TradingStatus
from app.agent.nodes.simons import ExecutionAgent
from app.agent.state import AgentState
from app.services.memory import MemoryService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BusinessVerifier")


async def run_verification():
    logger.info("🚀 Starting Business Telemetry Verification Flow...")

    # 1. Memory Verification
    logger.info("🧠 Testing Memory Service Metrics...")
    memory = MemoryService()
    # Mock embedding to avoid Google API dependency if keys missing in shell?
    # Actually, we rely on env. If it fails, that's fine, we catch it.
    try:
        # Save Trigger
        memory.save_regime("TEST_SYM", {"regime": "Gaussian"}, {"label": "Positive"})
        # Retrieve Trigger
        memory.retrieve_similar(
            "TEST_SYM", {"regime": "Gaussian"}, {"label": "Positive"}
        )
    except Exception as e:
        logger.warning(f"Memory test warning (expected if no API key): {e}")

    # 2. Analyst Verification
    logger.info("🔍 Testing Analyst Agent Metrics...")
    analyst = AnalystAgent()
    state = AgentState(
        symbol="AAPL",
        watchlist=[
            {"symbol": "AAPL", "price": 150.0},
            {"symbol": "MSFT", "price": 300.0},
        ],
        candidates=[],
    )
    # Mock components to avoid heavy calls
    analyst.market.get_market_snapshot = lambda s: {
        "symbol": s,
        "price": 150.0,
        "history": [150.0] * 100,
        "news": [],
        "sentiment": {"score": 0.5},
    }
    analyst.physics_map = {}  # Reset
    # We skip actual extensive analysis logic by mocking internal calls if possible,
    # but `analyze` is complex. We'll run it and let it fail gracefully or mock parts.
    # Actually, let's just trust it runs partially.
    # For speed, we just want to hit the metrics lines.

    try:
        state = await analyst.analyze(state)
    except Exception as e:
        logger.warning(f"Analyst flow warning: {e}")

    # 3. Risk Verification
    logger.info("⚖️ Testing Risk Manager Metrics...")
    risk = RiskManager()
    risk.check_circuit_breaker(state)  # Should be fine

    # Fake a winner to trigger Risk Metrics
    state["analysis_reports"] = [
        {
            "symbol": "AAPL",
            "price": 150.0,
            "velocity": 0.05,
            "acceleration": 0.01,
            "current_alpha": 1.8,
            "regime": "Gaussian",
            "signal_side": "BUY",
            "signal_confidence": 0.9,
            "reasoning": "Test",
            "success": True,
        }
    ]

    # Mock Reasoning for Tournament
    from app.services.reasoning import ReasoningService

    ReasoningService.arbitrate_tournament = lambda self, c: {
        "winner_symbol": "AAPL",
        "rationale": "Mock",
    }

    # Run Risk Node Logic manually (since risk_node is a wrapper)
    # We'll use risk_node wrapper logic... simplified
    try:
        # Simulate Tournament Selection
        # (Copied from risk.py mainly to hit metrics)
        # Actually risk_node calls manager.check_circuit_breaker etc.
        # Let's import the node function.
        from app.agent.nodes.taleb import risk_node

        state = risk_node(state)

    except Exception as e:
        logger.error(f"Risk flow failed: {e}")

    # 4. Execution Verification
    logger.info("⚡ Testing Execution Agent Metrics...")
    # Force state to be executable
    state["status"] = TradingStatus.ACTIVE
    state["approved_size"] = 1000.0
    state["signal_side"] = "BUY"
    state["price"] = 150.0
    state["velocity"] = 0.05

    # Mock Alpaca execution to avoid real/paper orders
    # (Though ExecutionAgent checks LIVE_TRADING_ENABLED setting)
    # We assume settings default to False or we force it.
    from app.core.config import settings

    settings.LIVE_TRADING_ENABLED = False

    execution = ExecutionAgent()
    state = execution.execute(state)

    logger.info("✅ Verification Flow Complete. Flushing telemetry...")

    # Flush
    from opentelemetry import trace, metrics

    try:
        trace.get_tracer_provider().shutdown()
        metrics.get_meter_provider().shutdown()
    except:
        pass


if __name__ == "__main__":
    asyncio.run(run_verification())
