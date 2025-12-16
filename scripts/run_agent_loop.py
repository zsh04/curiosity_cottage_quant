import asyncio
import os
from dotenv import load_dotenv
from app.agent.graph import app_graph


from pathlib import Path

# Explicitly load .env from project root
root_dir = Path(__file__).resolve().parent.parent
load_dotenv(root_dir / ".env")

# Debug Env Vars
key = os.getenv("ALPACA_API_KEY")
print(f"DEBUG: ALPACA_API_KEY present: {bool(key)}")
if key:
    print(f"DEBUG: ALPACA_API_KEY length: {len(key)}")
    print(f"DEBUG: ALPACA_API_KEY prefix: {key[:2]}")


async def run_agent_loop():
    print("--- Starting Cognitive Engine ---")

    # Initial State
    initial_state = {
        "messages": [],
        "market_data": {},  # In real app, this might be populated by a sensor
        "reasoning_trace": [],
        "market_regime": "",
        "target_sectors": [],
        "candidate_trades": [],
        "final_orders": [],
        "next_step": "macro",
    }

    # Run the graph
    # LangGraph's .invoke is synchronous or async depending on setup,
    # but app_graph.invoke() is usually sync. app_graph.ainvoke() is async.
    # Since we used standard ChatOpenAI (sync), let's try synchronous invoke first.

    try:
        final_state = await app_graph.ainvoke(initial_state)

        print("\n--- Final State ---")
        print(f"Market Regime: {final_state['market_regime']}")
        print(f"Target Sectors: {final_state['target_sectors']}")

        print("\n--- Reasoning Trace ---")
        for trace in final_state["reasoning_trace"]:
            print(f"- {trace}")

        print("\n--- Final Orders ---")
        for order in final_state["final_orders"]:
            print(order)

    except Exception as e:
        print(f"Error running graph: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(run_agent_loop())
