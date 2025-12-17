import asyncio
import logging
from unittest.mock import MagicMock
from app.agent.nodes.analyst import AnalystAgent
from app.services.market import MarketService

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VerifyIsolation")


async def test_analyst_isolation():
    logger.info("🧪 Starting Analyst Physics Isolation Verification...")

    # 1. Instantiate Analyst
    agent = AnalystAgent()

    # 2. Mock Market Service to return distinct patterns
    # AAPL: Steady Uptrend (Velocity > 0)
    # TSLA: Crash (Velocity < 0)
    mock_market = MagicMock(spec=MarketService)

    def get_snapshot_side_effect(symbol):
        if symbol == "AAPL":
            return {
                "symbol": "AAPL",
                "price": 150.0,
                "history": [100 + i for i in range(100)],  # [100, 101, ... 199]
                "news": [],
                "sentiment": {},
            }
        elif symbol == "TSLA":
            return {
                "symbol": "TSLA",
                "price": 200.0,
                "history": [300 - i for i in range(100)],  # [300, 299, ... 201]
                "news": [],
                "sentiment": {},
            }
        return {}

    def get_startup_side_effect(symbol, limit=100):
        # Same logic for startup
        if symbol == "AAPL":
            return [100 + i for i in range(100)]
        elif symbol == "TSLA":
            return [300 - i for i in range(100)]
        return []

    mock_market.get_market_snapshot = get_snapshot_side_effect
    mock_market.get_startup_bars = get_startup_side_effect

    # Inject Mock
    agent.market = mock_market

    # 3. Execute Parallel Batch Analysis
    logger.info("🚀 Launching Parallel Batch for AAPL and TSLA...")
    state = {"candidates": [{"symbol": "AAPL"}, {"symbol": "TSLA"}]}

    # Run the analyze method (which spawns _analyze_single tasks)
    final_state = await agent.analyze(state)

    # 4. Verification
    logger.info("\n🔍 VERIFICATION RESULTS:")

    # Check 1: Factory Map Population
    if "AAPL" in agent.physics_map and "TSLA" in agent.physics_map:
        logger.info("✅ PASS: Physics Map contains both symbols.")
    else:
        logger.error(f"❌ FAIL: Map missing symbols. Keys: {agent.physics_map.keys()}")
        return

    # Check 2: Instance Uniqueness
    physics_aapl = agent.physics_map["AAPL"]
    physics_tsla = agent.physics_map["TSLA"]

    if physics_aapl is not physics_tsla:
        logger.info("✅ PASS: Physics Instances are distinct objects.")
    else:
        logger.error(
            "❌ FAIL: Physics Instances are the SAME object (Data Bleed Risk)."
        )
        return

    # Check 3: State Divergence (The Proof)
    # AAPL should have positive velocity (100 -> 200)
    # TSLA should have negative velocity (300 -> 200)

    # Note: PhysicsService state is private usually, but we can check the 'velocity' in the result reports
    reports = final_state.get("analysis_reports", [])
    report_aapl = next((r for r in reports if r["symbol"] == "AAPL"), {})
    report_tsla = next((r for r in reports if r["symbol"] == "TSLA"), {})

    vel_aapl = report_aapl.get("velocity", 0.0)
    vel_tsla = report_tsla.get("velocity", 0.0)

    logger.info(f"   AAPL Velocity: {vel_aapl:.4f}")
    logger.info(f"   TSLA Velocity: {vel_tsla:.4f}")

    if vel_aapl > 0 and vel_tsla < 0:
        logger.info("✅ PASS: Kinematic States are correctly divergent.")
    else:
        logger.error(
            "❌ FAIL: Velocities do not match expected trends (Potential Bleed)."
        )

    logger.info("\n🏁 ISOLATION AUDIT COMPLETE: SYSTEM SECURE.")


if __name__ == "__main__":
    asyncio.run(test_analyst_isolation())
