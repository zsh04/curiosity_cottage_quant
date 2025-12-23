import asyncio
import logging
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from app.agent.pipeline import TradingPipeline
from app.services.state_stream import get_state_broadcaster
from app.agent.state import AgentState

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VERIFY_SHANNON")


async def test_shannon_bridge():
    logger.info("📡 Testing Shannon Bridge...")

    # 1. Get Broadcaster and Subscribe
    broadcaster = get_state_broadcaster()
    queue = broadcaster.subscribe()
    logger.info("✅ Subscribed to StateBroadcaster")

    # 2. Instantiate Pipeline
    pipeline = TradingPipeline()

    # 3. Create Dummy State
    test_state: AgentState = {
        "cycle_id": "TEST_CYCLE_001",
        "symbol": "BTC/USD",
        "status": "ACTIVE",
        "signal_side": "BUY",
    }

    # 4. Trigger Finalize Cycle (The Push)
    logger.info("🚀 Triggering _finalize_cycle...")
    pipeline._finalize_cycle(test_state)

    # 5. Wait for message on queue
    try:
        # Give it a moment to process the async task created in _finalize_cycle
        # Since _finalize_cycle uses asyncio.create_task, we need to yield control
        await asyncio.sleep(0.1)

        received_state = await asyncio.wait_for(queue.get(), timeout=2.0)

        logger.info(f"📬 Received State: {received_state}")

        assert received_state["cycle_id"] == "TEST_CYCLE_001"
        assert received_state["signal_side"] == "BUY"

        logger.info("✅ Shannon Bridge Verified: Telemetry is Flowing.")

    except asyncio.TimeoutError:
        logger.error("❌ Shannon Bridge Failed: Timeout waiting for state.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Shannon Bridge Failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(test_shannon_bridge())
