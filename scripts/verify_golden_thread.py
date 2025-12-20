import sys
import asyncio
import logging
import orjson
import os
from unittest.mock import MagicMock, patch
from datetime import datetime
from faststream.redis import RedisBroker, TestRedisBroker

# Add project root to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

# Setup Logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | WARGAMES | %(levelname)s | %(message)s"
)
logger = logging.getLogger("WarGames")

# --- 1. SETUP SHARED BUS ---
# We create a single Broker to rule them all.
master_broker = RedisBroker()


async def main():
    logger.info("⚔️  WAR GAMES: PATTON INITIATING FIELD TEST ⚔️")
    logger.info("Objective: Verify The Golden Thread (Tick -> Order)")

    # --- 2. PATCHING & IMPORTS ---
    # We patch RedisBroker globally so all services attach to 'master_broker'.
    with patch("faststream.redis.RedisBroker", return_value=master_broker):
        from app.services import feynman
        from app.services import soros
        from app.services import execution
        from app.services import chronos

    # --- 3. MOCKING DEPENDENCIES ---

    # Mock Alpaca (Execution)
    mock_alpaca = MagicMock()
    mock_order = MagicMock()
    mock_order.id = "GOLDEN-ORD-001"
    mock_order.symbol = "BTC-USD"
    mock_order.side.value = "buy"
    mock_order.status.value = "new"
    mock_order.qty = 0.01
    mock_order.filled_avg_price = 10500.0
    mock_alpaca.submit_order.return_value = mock_order
    execution.taleb.broker = mock_alpaca
    logger.info("✅ MOCK: Alpaca Client Intercepted.")

    # Mock LLM (Soros)
    async def mock_debate(*args, **kwargs):
        return {
            "bull_argument": "Momentum is accelerating. Nash distance is healthy.",
            "bear_argument": "None.",
            "judge_verdict": "BUY",
            "confidence": 0.95,
        }

    soros.soros.conduct_debate = mock_debate
    logger.info("✅ MOCK: Soros Investment Committee Intercepted.")

    # Mock Feynman Forces (Ensure Signals Pass Gates)
    mock_forces = {
        "mass": 100.0,
        "momentum": 1.0,
        "friction": 0.0,
        "entropy": 0.1,
        "nash_dist": 1.0,
        "alpha_coefficient": 3.0,
        "price": 10250.0,
        "regime": "TRENDING",
        "timestamp": datetime.now().timestamp() * 1000,
    }
    feynman.kernel.calculate_forces = MagicMock(return_value=mock_forces)
    logger.info("✅ MOCK: Physics Kernel Patched (Perfect Trend).")

    # Future for result
    future_order = asyncio.Future()

    @master_broker.subscriber("execution.orders")
    async def capture_order(msg):
        future_order.set_result(orjson.loads(msg))

    # --- 4. EXECUTION ---
    # Use TestRedisBroker to run the in-memory bus
    async with TestRedisBroker(master_broker) as br:
        # --- SCENARIO: THE PERFECT LONG ---
        logger.info("🚀 INJECTION: Starting Market Tick Stream (Uptrend)...")

        base_price = 10000.0
        # Send 25 ticks to fill feynman buffer slightly and establish trend
        for i in range(25):
            price = base_price + (i * 10)  # 10000, 10010, ...
            tick = {
                "symbol": "BTC-USD",
                "price": price,
                "size": 1.0,
                "timestamp": datetime.now().timestamp() * 1000,
                "updates": 1,
            }
            await br.publish(orjson.dumps(tick), channel="market.tick.BTC-USD")
            await asyncio.sleep(0.001)

        # Inject Forecast (Confluence)
        # Price is now approx 10240. P50 should be higher.
        forecast = {
            "timestamp": datetime.now().isoformat(),
            "symbol": "BTC-USD",
            "p10": 10300.0,
            "p50": 10500.0,
            "p90": 10800.0,
            "horizon": 10,
            "confidence": 0.9,
        }
        await br.publish(orjson.dumps(forecast), channel="forecast.signals")
        logger.info("🚀 INJECTION: Forecast Packet (Bullish) Sent.")

        # Trigger Tick to run Soros
        trigger_tick = {
            "symbol": "BTC-USD",
            "price": 10250.0,
            "size": 1.0,
            "timestamp": datetime.now().timestamp() * 1000,
            "updates": 1,
        }
        await br.publish(orjson.dumps(trigger_tick), channel="market.tick.BTC-USD")
        logger.info("🚀 INJECTION: Trigger Tick Sent.")

        # Wait for Order
        try:
            logger.info("⏳ WAITING for Execution Order...")
            order_data = await asyncio.wait_for(future_order, timeout=5.0)

            logger.info(f"🎯 TARGET ACQUIRED: {order_data}")

            # --- ASSERTIONS ---
            if order_data["side"] == "BUY" and order_data["symbol"] == "BTC-USD":
                logger.info("⭐⭐⭐ MISSION SUCCESS: GOLDEN THREAD VERIFIED ⭐⭐⭐")
                logger.info("Signal generated, debated, sized, and executed.")
            else:
                logger.error(
                    f"❌ MISSION FAILED: Incorrect Order Details: {order_data}"
                )
                exit(1)

        except asyncio.TimeoutError:
            logger.error("❌ MISSION FAILED: Time out. The thread is broken.")
            exit(1)


if __name__ == "__main__":
    asyncio.run(main())
