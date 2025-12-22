import asyncio
import aiohttp
import logging
import json
import websockets
from datetime import datetime, timedelta

# Setup Logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger("ShannonTest")

API_URL = "http://localhost:8000/api"
WS_URL = "ws://localhost:8000/api"


async def test_flow():
    # 1. Spawn Run
    # We use a short range
    start = (datetime.utcnow() - timedelta(days=2)).strftime("%Y-%m-%d")
    end = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")

    logger.info(f"🚀 Spawning Backtest for {start} to {end}...")

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{API_URL}/backtest/spawn", json={"start_date": start, "end_date": end}
        ) as resp:
            if (
                resp.status != 201
            ):  # Litestar might return 201 created or 200? default is 201 for post?
                # Actually default is 201 for post usually or 200. Controller logic returned dict.
                # Let's check json.
                pass

            data = await resp.json()
            run_id = data.get("run_id")
            logger.info(f"✅ Spawned Run ID: {run_id}")

    if not run_id:
        logger.error("❌ Failed to get run_id")
        return

    # 2. Listen to Stream
    ws_endpoint = f"{WS_URL}/backtest/stream/{run_id}"
    logger.info(f"📡 Connecting to {ws_endpoint}...")

    try:
        async with websockets.connect(ws_endpoint) as ws:
            logger.info("✅ Connected to Stream.")

            message_count = 0
            while True:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=30.0)  # 30s timeout
                    payload = json.loads(msg)
                    typ = payload.get("type")

                    if typ == "progress":
                        message_count += 1
                        if message_count % 5 == 0:
                            logger.info(
                                f"Update: Equity=${payload.get('equity'):.2f}, Progress={(payload.get('progress', 0) * 100):.1f}%"
                            )

                    elif typ == "COMPLETED":
                        logger.info("🎉 COMPLETED RECEIVED!")
                        logger.info(f"Metrics: {payload.get('metrics', {})}")
                        break

                    elif typ == "FAILED":
                        logger.error(f"❌ FAILED RECEIVED: {payload.get('error')}")
                        break

                except asyncio.TimeoutError:
                    logger.warning("⚠️ Stream Timeout (No messages for 30s)")
                    break

    except Exception as e:
        logger.error(f"Stream Error: {e}")


if __name__ == "__main__":
    # Ensure server is running!
    # This script assumes 'uvicorn app.main:app' is running separately??
    # Ideally we should start it or assume user environment.
    # Given agent constraints, I cannot easily detach a server process and then run script in same step?
    # I can use `nohup` or `&` in run_command.

    asyncio.run(test_flow())
