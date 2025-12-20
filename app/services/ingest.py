import asyncio
import logging
import orjson
import os
import sys

# Add project root to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))

from alpaca.data.live import StockDataStream
from alpaca.data.models import Trade
from faststream.redis import RedisBroker
from app.core.config import settings

# --- Setup Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | SIPHON | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("ingest")

# --- Initialize Resources ---
broker = RedisBroker(
    url=settings.DATABASE_URL.replace("postgresql+asyncpg", "redis").replace(
        "5432/cc_quant", "6379/0"
    )
)
# Use explicitly defined Redis URL if available or derive from DB (assuming standard setup)
# Actually, FastStream RedisBroker default is redis://localhost:6379 if not provided, usually provided via env REDIS_URL
# Let's check if we have REDIS_URL in config.
# Config doesn't have REDIS_URL explicitly, usually typical setup.
# Let's use a standard default or check os.getenv.
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
broker = RedisBroker(REDIS_URL)


async def main():
    """
    The Main Valve.
    Opens connection to Alpaca and pumps data to Redis.
    """
    logger.info("🛢️  THE SIPHON: DANIEL PLAINVIEW INITIATING DRAINAGE 🛢️")
    logger.info(f"Targeting: {settings.WATCHLIST}")
    logger.info(f"Feed: {settings.ALPACA_DATA_FEED.upper()}")

    # 1. Connect to Redis Bus
    await broker.connect()
    logger.info("✅ Connected to Redis Bus.")

    # 2. Callback for Incoming Trades
    async def handle_trade(data: Trade):
        """
        Normalizes Alpaca Trade -> Ezekiel Tick.
        Publishes to Redis.
        """
        try:
            # Normalize
            payload = {
                "symbol": data.symbol,
                "price": float(data.price),
                "size": float(data.size),
                "timestamp": data.timestamp.isoformat(),
                "updates": 1,
                "exchange": data.exchange,
            }

            # Publish
            channel = f"market.tick.{data.symbol}"
            await broker.publish(orjson.dumps(payload), channel=channel)

            # Log periodic drill status (optional, maybe too noisy for every tick)
            # logger.debug(f"💧 Flow: {data.symbol} @ {data.price}")

        except Exception as e:
            logger.error(f"⚠️ Spill detected in extraction: {e}")

    # 3. Resilience Loop (The Pipeline)
    while True:
        try:
            logger.info("🔧 Constructing Pipeline...")

            # Initialize Stream
            stream = StockDataStream(
                settings.ALPACA_API_KEY,
                settings.ALPACA_API_SECRET,
                feed=settings.ALPACA_DATA_FEED,
            )

            # Subscribe
            stream.subscribe_trades(handle_trade, *settings.WATCHLIST)
            logger.info("✅ Subscribed to Watchlist.")

            # Open Valve (Blocking)
            logger.info("🥤 MAIN VALVE OPEN. DRINKING MILKSHAKE...")
            await stream.run()

        except Exception as e:
            logger.error(f"❌ PIPELINE RUPTURE: {e}")
            logger.info("🛠️  Patching leak... Restarting in 5s.")
            await asyncio.sleep(5)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Access Rights Revoked. Shutting down.")
