import sys
import logging
from app.adapters.market import MarketAdapter

# Configure Logging to Console
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_adapter():
    print("--- DIAGNOSTIC: Testing MarketAdapter ---")
    try:
        adapter = MarketAdapter()
        print("✅ Adapter Initialized")
    except Exception as e:
        print(f"❌ Adapter Init Failed: {e}")
        return

    symbol = "SPY"

    print(f"\n--- Testing get_price('{symbol}') ---")
    try:
        price = adapter.get_price(symbol)
        print(f"👉 Price: {price}")
    except Exception as e:
        print(f"❌ get_price Failed: {e}")

    print(f"\n--- Testing get_price_history('{symbol}') ---")
    try:
        hist = adapter.get_price_history(symbol, limit=5)
        print(f"👉 History (Last 5): {hist}")
    except Exception as e:
        print(f"❌ get_price_history Failed: {e}")


if __name__ == "__main__":
    test_adapter()
