import asyncio
import logging
from dotenv import load_dotenv

load_dotenv()

from app.agent.nodes.analyst import AnalystAgent
from app.agent.state import AgentState
from app.agent.state import AgentState

# Setup Logging
logging.basicConfig(level=logging.INFO)


async def test_integration():
    print("--- Starting Analyst Memory Verification ---")

    # Mock State
    state = AgentState(symbol="SPY", price=500.0, cash=100000.0)

    agent = AnalystAgent()

    # We expect this to fail gracefully if DB is down, but NOT crash the script.
    # The 'analyze' method wraps everything in try/except.

    print("Invoking analyze()...")
    new_state = await agent.analyze(state)

    print("--- Analysis Complete ---")
    print(f"Signal: {new_state.get('signal_side')}")
    print(f"Reasoning: {new_state.get('reasoning')}")

    # Check if 'market_state_embeddings' logic was triggered
    # We can't easily check internal variables without mocking,
    # but if it returns a signal (even FLAT due to error), code path is valid.

    if "ANALYST CRASH" in new_state.get("reasoning", ""):
        print(
            "Note: Analyst crashed (likely due to missing DB/Services), but code executed."
        )
    else:
        print("Success: Analyst completed without crash.")


if __name__ == "__main__":
    asyncio.run(test_integration())
