import sys
import os
import asyncio
import logging
import time

# Ensure app is in path
sys.path.append(os.getcwd())

from app.adapters.market import MarketAdapter
from app.services.reasoning import get_reasoning_service
from app.core.config import settings

try:
    from app.agent.models import LegacyModel

    print("❌ CRITICAL: Legacy 'models.py' is still importable! Cleanup failed.")
    sys.exit(1)
except ImportError:
    print("✅ Legacy Models module correctly removed/renamed.")

# Setup logging
logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)


async def verify():
    print("\n🔍 STARTING LIVE DATA VERIFICATION 🔍\n")

    # 1. Market Data (Price)
    print("--- 1. MARKET DATA (Realtime) ---")
    market = MarketAdapter()
    symbol = "SPY"

    start = time.time()
    try:
        price = market.get_price(symbol)
        latency = (time.time() - start) * 1000
        print(f"✅ {symbol} Price: ${price:.2f} (Latency: {latency:.0f}ms)")

        if price <= 0:
            print(f"❌ ERROR: Invalid price for {symbol} (Returned 0.0)")
            sys.exit(1)

        if price == 100.0 or price == 123.45:
            print(
                f"⚠️ WARNING: Suspicious 'Round' Price: ${price}. Might be a hardcoded mock?"
            )
    except Exception as e:
        print(f"❌ ERROR: Market fetch failed: {e}")
        sys.exit(1)

    # 2. Market Data (News/Snapshot)
    print("\n--- 2. NEWS/SNAPSHOT (Realtime) ---")
    try:
        # We need to test the service or adapter directly
        # Tiingo is primary for news.
        news = market.get_news(symbol, limit=1)
        if news:
            print(f"✅ News Found for {symbol}: {len(news)} items")
            print(f"   Sample: {str(news[0])[:100]}...")
        else:
            print(f"⚠️ No News found for {symbol} (Tiingo might be restricted/empty).")
            # Not a failure condition for 'System Online', just data availability.
    except Exception as e:
        print(f"⚠️ News fetch exception: {e}")

    # 3. Intelligence (LLM)
    print("\n--- 3. INTELLIGENCE (Ollama Local) ---")
    reasoning = get_reasoning_service()

    try:
        print("🧠 Invoking Local LLM for Signal Generation...")
        start_llm = time.time()
        # We use a direct call to test the pipeline
        signal = reasoning.generate_signal(
            {
                "market": {
                    "price": price,
                    "symbol": symbol,
                    "news_context": "Deepmind AI breakthrough announced.",
                },
                "physics": {
                    "velocity": 0.05,
                    "acceleration": 0.01,
                    "regime": "Gaussian",
                },
                "forecast": {"trend": "UP", "confidence": 0.8},
                "sentiment": {"label": "Positive", "score": 0.9},
            }
        )
        llm_latency = (time.time() - start_llm) * 1000

        print(f"✅ LLM Response: {signal}")
        print(f"   Reasoning: {signal.get('reasoning')}")
        print(f"   Latency: {llm_latency:.0f}ms")

        if signal.get("signal_side") not in ["BUY", "SELL", "FLAT"]:
            print("❌ ERROR: Invalid signal format from LLM")
            sys.exit(1)

        if "Mock" in signal.get("reasoning", ""):
            print("❌ CRITICAL: LLM returned 'Mock' in reasoning!")
            sys.exit(1)

    except Exception as e:
        print(f"❌ ERROR: LLM Inference Failed: {e}")
        # Identify if it is connection error
        if "Connection" in str(e) or "Refused" in str(e):
            print("👉 SUGGESTION: Check if 'ollama serve' is running.")
        sys.exit(1)

    # 4. Config Check
    print("\n--- 4. CONFIG ---")
    print(f"LIVE_TRADING_ENABLED: {settings.LIVE_TRADING_ENABLED}")
    if settings.LIVE_TRADING_ENABLED:
        print("⚠️ WARNING: REAL MONEY TRADING IS ENABLED!")
    else:
        print("✅ SAFE: Paper Trading Mode Active (Real Data -> Simulated Execution)")

    print("\n✨ VERIFICATION COMPLETE: SYSTEM IS USING REAL DATA ✨")


if __name__ == "__main__":
    asyncio.run(verify())
