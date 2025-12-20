import asyncio
import websockets
import json
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("ws_test")


async def listen():
    uri = "ws://localhost:8000/api/ws/brain"
    logger.info(f"🔌 Connecting to {uri}...")

    try:
        # Add Origin header to satisfy CORS
        headers = {"Origin": "http://localhost:3000"}
        async with websockets.connect(uri, additional_headers=headers) as websocket:
            logger.info("✅ Connected! Waiting for thoughts...")

            # Wait for at least one NODE_UPDATE or TOURNAMENT_VERDICT
            timeout = 60  # wait 60 seconds for a full cycle (scan + analysis)

            try:
                while True:
                    message = await asyncio.wait_for(websocket.recv(), timeout)
                    data = json.loads(message)

                    msg_type = data.get("type", "UNKNOWN")
                    node = data.get("node", "UNKNOWN")
                    sym = data.get("symbol", "UNKNOWN")

                    logger.info(f"🧠 RECEIVED: [{msg_type}] from {node} for {sym}")

                    if msg_type == "NODE_UPDATE":
                        # Inspect payload slightly
                        payload = data.get("payload", {})
                        keys = list(payload.keys())[:3]
                        logger.info(f"   Payload Keys: {keys}...")

                    if msg_type == "TOURNAMENT_VERDICT":
                        logger.info("🏆 VERDICT RECEIVED! Verification Passed.")
                        return

            except asyncio.TimeoutError:
                logger.error("❌ Timeout waiting for events.")
                sys.exit(1)

    except Exception as e:
        logger.error(f"❌ Connection Failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Ensure websockets is installed
    try:
        import websockets
    except ImportError:
        logger.error("Please install websockets: pip install websockets")
        sys.exit(1)

    asyncio.run(listen())
