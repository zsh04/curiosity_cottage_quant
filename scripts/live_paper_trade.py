import asyncio
import logging
import os
from dotenv import load_dotenv

# Configure basic logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("live_trade")


async def run_trade():
    """
    Triggers a full cycle of the Agent Graph to perform a Live Paper Trade.
    """
    logger.info("🔌 initializing environment...")
    load_dotenv()

    # Import AFTER dotenv to ensure config is loaded
    from app.dal.database import init_db
    from app.agent.graph import app_graph as graph

    logger.info("💾 connecting to database...")
    init_db()

    logger.info("🚀 Triggering Live Paper Trade Cycle...")

    # Initial seed state (Macro node will override symbol)
    initial_state = {
        "messages": [],
        "symbol": "SPY",  # Seed, but Macro will select best
        "status": "active",
    }

    try:
        # Invoke Graph (Async)
        # Verify if graph is configured for async invoke
        logger.info("🌊 Invoking Agent Graph...")
        result = await graph.ainvoke(initial_state)

        logger.info("✅ Trade Cycle Complete.")

        # Extract Results
        symbol = result.get("symbol", "Unknown")
        signal = result.get("signal_side", "FLAT")
        price = float(result.get("price", 0.0))
        regime = result.get("regime", "Unknown")
        confidence = float(result.get("signal_confidence", 0.0))
        reasoning = result.get("reasoning", "No reasoning provided.")

        # Execution Details
        # Execution node typically logs but doesn't always return a structured report in state top-level
        # Logic: check logs or state['cash'] change?
        # But we print what we have.

        print("\n" + "=" * 50)
        print("          🧪 LIVE PAPER TRADE REPORT 🧪")
        print("=" * 50)
        print(f"🔹 TICKER       : {symbol}")
        print(f"🔹 PRICE        : ${price:,.2f}")
        print(f"🔹 REGIME       : {regime}")
        print(f"🔹 SIGNAL       : {signal} ({confidence:.1%})")
        print("-" * 50)
        print(f"🔸 REASONING    : {reasoning}")
        print("-" * 50)

        if result.get("risk_approved"):
            size = result.get("approved_size", 0.0)
            print(f"✅ RISK ACTION  : APPROVED (Size: ${size:,.2f})")
        else:
            print(f"❌ RISK ACTION  : BLOCKED/VETOED")

        print("=" * 50 + "\n")

    except Exception as e:
        logger.exception(f"❌ Trade Cycle Failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(run_trade())
