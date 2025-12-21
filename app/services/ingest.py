import asyncio
import logging
import orjson
import os
import sys

# Add project root to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))

from alpaca.data.live import StockDataStream
from alpaca.data.models import Trade, Quote
from faststream.redis import RedisBroker
from app.core.config import settings
from app.services.scanner import MarketScanner

# --- Setup Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | SIPHON | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("ingest")

# --- Initialize Resources ---
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

    # Initialize Scanner
    scanner = MarketScanner()

    # 2. Callbacks for Incoming Data
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

        except Exception as e:
            logger.error(f"⚠️ Spill detected in trade extraction: {e}")

    async def handle_quote(data: Quote):
        """
        Handles incoming Quotes (Bid/Ask).
        Publishes to 'market.quote.{symbol}'.
        """
        try:
            payload = {
                "symbol": data.symbol,
                "bid_price": float(data.bid_price),
                "bid_size": float(data.bid_size),
                "ask_price": float(data.ask_price),
                "ask_size": float(data.ask_size),
                "timestamp": data.timestamp.isoformat(),
            }
            channel = f"market.quote.{data.symbol}"
            await broker.publish(orjson.dumps(payload), channel=channel)
        except Exception as e:
            logger.error(f"⚠️ Spill detected in quote extraction: {e}")

    # 3. Dynamic Subscription Task
    async def update_subscriptions(stream: StockDataStream):
        """
        Polls Scanner every 5 minutes and updates subscriptions.
        """
        while True:
            try:
                # 1. Fetch Universe (Core + Scanned)
                active_symbols = await scanner.get_active_universe()
                targets = list(set(settings.WATCHLIST + active_symbols))

                logger.info(f"🔄 Updating Subscriptions. Targets: {len(targets)}")

                # 2. Subscribe (Alpaca handles deduplication/updates usually, or we just re-sub)
                stream.subscribe_trades(handle_trade, *targets)
                stream.subscribe_quotes(handle_quote, *targets)

                logger.info(f"✅ Subscription Updated: {targets}")

            except Exception as e:
                logger.error(f"⚠️ Scanner Update Failed: {e}")

            # Wait 5 minutes
            await asyncio.sleep(300)

    # 4. Resilience Loop (The Pipeline)
    while True:
        scan_task = None
        try:
            logger.info("🔧 Constructing Pipeline...")

            # Initialize Stream
            stream = StockDataStream(
                settings.ALPACA_API_KEY,
                settings.ALPACA_API_SECRET,
                feed=settings.ALPACA_DATA_FEED,
            )

            # Start Scanner Loop
            scan_task = asyncio.create_task(update_subscriptions(stream))

            # Open Valve (Blocking)
            logger.info("🥤 MAIN VALVE OPEN. DRINKING MILKSHAKE...")
            await stream.run()

        except Exception as e:
            logger.error(f"❌ PIPELINE RUPTURE: {e}")
            logger.info("🛠️  Patching leak... Restarting in 5s.")

        finally:
            # Ensure we kill the background task if the stream dies
            if scan_task:
                scan_task.cancel()
                try:
                    await scan_task
                except asyncio.CancelledError:
                    pass
            await asyncio.sleep(5)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Access Rights Revoked. Shutting down.")
