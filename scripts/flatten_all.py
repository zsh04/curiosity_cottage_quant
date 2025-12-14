import os
import sys
import alpaca_trade_api as tradeapi
from loguru import logger


def flatten_all():
    """
    EMERGENCY PROCEDURE: Closes all positions immediately.
    """
    logger.warning("Initiating EMERGENCY FLATTEN ALL procedure...")

    api_key = os.getenv("ALPACA_API_KEY")
    api_secret = os.getenv("ALPACA_SECRET_KEY")
    base_url = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")

    if not api_key or not api_secret:
        logger.error("ALPACA_API_KEY or ALPACA_SECRET_KEY not found in environment.")
        sys.exit(1)

    try:
        api = tradeapi.REST(api_key, api_secret, base_url, api_version="v2")
        positions = api.list_positions()

        if not positions:
            logger.info("No open positions found. System is flat.")
            return

        logger.warning(f"Found {len(positions)} open positions. Closing ALL...")

        # Close all positions
        api.close_all_positions()

        # Cancel all open orders as well for safety
        api.cancel_all_orders()

        logger.success("All positions closed and orders cancelled.")

    except Exception as e:
        logger.critical(f"FAILED to flatten positions: {e}")
        sys.exit(1)


if __name__ == "__main__":
    flatten_all()
