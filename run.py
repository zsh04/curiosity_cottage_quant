import pprint
import sys
import os

# Ensure app is in path
sys.path.append(os.getcwd())

from app.agent.graph import app_graph
from app.agent.state import AgentState, TradingStatus

# --- Configuration ---
TEST_SYMBOL = "SPY"
INITIAL_NAV = 500.0


def main():
    print("🚀 CC-V2 IGNITION SEQUENCE START...")

    # Construct Initial State
    initial_state: AgentState = {
        "nav": INITIAL_NAV,
        "cash": INITIAL_NAV,
        "symbol": TEST_SYMBOL,
        "status": TradingStatus.ACTIVE,
        "messages": [],
        "historic_returns": [],
        "price": 0.0,
        "daily_pnl": 0.0,
        "max_drawdown": 0.0,
        # Initialize other required fields with defaults/empty
        "current_alpha": 2.0,  # Default neutral
        "regime": "Unknown",
        "signal_side": "FLAT",
        "signal_confidence": 0.0,
        "reasoning": "",
        "approved_size": 0.0,
        "risk_multiplier": 1.0,  # Legacy field
    }

    try:
        # Ignite Graph
        final_state = app_graph.invoke(initial_state)

        # --- The Autopsy ---
        print("\n" + "=" * 30)
        print("--- MISSION REPORT ---")
        print("=" * 30)

        # Extract Metrics
        symbol = final_state.get("symbol", "N/A")
        signal_side = final_state.get("signal_side", "N/A")
        signal_confidence = final_state.get("signal_confidence", 0.0)

        current_alpha = final_state.get("current_alpha", "N/A")
        regime = final_state.get("regime", "N/A")

        approved_size = final_state.get("approved_size", 0.0)
        cash = final_state.get("cash", 0.0)

        print(f"Symbol:         {symbol}")
        print(f"Analyst Signal: {signal_side} (Conf: {signal_confidence:.2f})")

        # Formatting Alpha if it's a number
        alpha_str = (
            f"{current_alpha:.2f}"
            if isinstance(current_alpha, (int, float))
            else str(current_alpha)
        )
        print(f"Physics Veto:   Alpha {alpha_str} | Regime {regime}")

        print(f"Risk Decision:  Approved Size ${approved_size:.2f}")
        print(f"Ending Cash:    ${cash:.2f}")

        print("\n--- SYSTEM LOGS ---")
        for msg in final_state.get("messages", []):
            # Message can be dict or string depending on where it came from
            if isinstance(msg, dict):
                content = msg.get("content", "")
                role = msg.get("role", "unknown")
                print(f"[{role.upper()}]: {content}")
            else:
                print(f"[LOG]: {msg}")

    except Exception as e:
        print(f"\n💥 SYSTEM ABORT: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
