import asyncio
import logging
import sys
import os

# Ensure paths
sys.path.append(os.getcwd())

from app.services.scanner import MarketScanner
from dotenv import load_dotenv

# Setup Logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("test_scanner")


async def main():
    logger.info("🧪 Testing MarketScanner...")
    load_dotenv()

    scanner = MarketScanner()
    if not scanner.trading_client:
        logger.error("❌ Credentials missing.")
        return

    logger.info("🚀 Triggering Universe Discovery (Limit=10)...")
    try:
        start = asyncio.get_event_loop().time()
        universe = await scanner.get_active_universe(limit=10)
        duration = asyncio.get_event_loop().time() - start

        logger.info(f"✅ Scan Complete in {duration:.2f}s")
        logger.info(f"📦 Discovered Universe ({len(universe)}): {universe}")

        if len(universe) > 0 and universe[0] not in ["SPY", "QQQ"]:
            logger.info("🎉 SUCCESS: Dynamic assets found!")
            sys.exit(0)
        elif universe == ["SPY", "QQQ"]:
            logger.warning("⚠️ Warning: Returned Fallback List.")
            sys.exit(1)
        else:
            logger.info("❓ Result ambiguous.")

    except Exception as e:
        logger.exception(f"💥 Scan Failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
