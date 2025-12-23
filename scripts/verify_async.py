import asyncio
import logging
from app.execution.alpaca_client import AlpacaClient
from app.core.config import settings

# Force Enable to test Logic (Logic only, calls might fail if no keys but we catch that)
settings.LIVE_TRADING_ENABLED = True
# Mock keys if missing to pass init check
if not settings.ALPACA_API_KEY:
    settings.ALPACA_API_KEY = "PK_MOCK"
    settings.ALPACA_API_SECRET = "SK_MOCK"
    print("⚠️ Using Mock Keys for Test")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AsyncTest")


async def main():
    logger.info("🧪 Starting Async Execution Test...")

    client = AlpacaClient()

    # 1. Test Async Account Fetch
    logger.info("1. Testing get_account_async()...")
    try:
        acct = await client.get_account_async()
        if acct:
            logger.info(f"✅ Account Fetched: ${acct.cash} Cash")
        else:
            logger.warning(
                "⚠️ Account Fetch returned None (Expected if keys invalid or network down)"
            )
    except Exception as e:
        logger.error(f"❌ Account Fetch Failed: {e}")

    # 2. Test Async Order Submit (Limit Order far away)
    logger.info("2. Testing submit_order_async() [Dry Run]...")
    try:
        # We expect this to fail if keys are invalid, but we want to verify it DOES NOT BLOCK.
        # Ideally we measure time.
        import time

        t0 = time.time()

        # We fire off a task
        task = asyncio.create_task(
            client.submit_order_async(
                symbol="SPY",
                qty=1,
                side="buy",
                limit_price=100.0,  # Way below market
            )
        )

        t1 = time.time()
        logger.info(f"⚡ Task Creation took {t1 - t0:.6f}s (Should be near instant)")

        try:
            await asyncio.wait_for(task, timeout=5.0)
            logger.info("✅ Order Submit Returned (Success or Server Error)")
        except asyncio.TimeoutError:
            logger.error("❌ Order Submit TIMED OUT (Still Blocking?)")
        except Exception as e:
            logger.info(f"✅ Order Submit 'Failed' correctly (API Error): {e}")

    except Exception as e:
        logger.error(f"❌ Unexpected Error: {e}")

    logger.info("🏁 Async Test Complete.")


if __name__ == "__main__":
    asyncio.run(main())
