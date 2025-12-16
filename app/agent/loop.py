import asyncio
import logging
import traceback
from app.agent.graph import app_graph
from app.services.state_stream import get_state_broadcaster

logger = logging.getLogger(__name__)

SLEEP_INTERVAL = 60  # seconds


async def run_agent_service():
    """
    Background service that runs the Cognitive Engine Agent Loop indefinitely.
    Broadcasts state updates to the StateBroadcaster.
    """
    logger.info("🚀 Agent Service Started")
    broadcaster = get_state_broadcaster()

    # Initial inputs could be empty or have some configuration
    # In a persistent loop, we might pass the previous state back in,
    # but LangGraph usually manages state persistence if configured.
    # For now, we mimic the script and start fresh or pass minimal context.
    # If the graph has checkpointers, it will resume.
    # If not, we are re-running the pipeline "From Scratch" each tick (common for polling agents).

    inputs = {
        "messages": [],
        # Add other initial keys if needed, e.g. "symbol": "SPY"
        # Assuming the graph defaults or the user configures it elsewhere.
        # Ideally, we should fetch active symbols from DB.
        # For MVP, defaulting to what the graph expects.
    }

    logger.info("🧠 Cognitive Engine: Online")

    while True:
        try:
            logger.info("🧠 Cognitive Engine: Heartbeat...")
            logger.info("--- 🧠 Agent Loop: Thinking ---")

            # Run the Graph
            # We assume a single turn of the graph (Macro -> Analyst -> Risk -> Execution -> End)
            final_state = await app_graph.ainvoke(inputs)

            # Construct Telemetry Packet
            # This should match what the Frontend App.tsx expects
            telemetry_packet = {
                "type": "TELEMETRY",
                "timestamp": final_state.get(
                    "timestamp", "now"
                ),  # Graph should ideally add this
                "status": "active",
                "market": {
                    "symbol": final_state.get("symbol", "SPY"),
                    "price": final_state.get("current_price", 0.0),
                    "alpha": final_state.get("current_alpha", 0.0),  # From heavy tail
                    "regime": final_state.get("regime", "Unknown"),
                    "velocity": final_state.get("velocity", 0.0),  # From Kalman
                    "acceleration": final_state.get("acceleration", 0.0),  # From Kalman
                },
                "signal": {
                    "side": final_state.get("signal_side", "FLAT"),
                    "confidence": final_state.get("signal_confidence", 0.0),
                    "reasoning": final_state.get("reasoning", ""),
                    "strategy": final_state.get("active_strategy", "None"),
                    "score": final_state.get("strategy_score", 0.0),
                },
                "sentiment": {
                    "label": "Neutral",  # Extract from state if available
                    "score": 0.5,
                },
                # Flatten logs from messages or specific log key
                "logs": final_state.get("messages", []),
            }

            logger.info("📡 Broadcasting State...")
            await broadcaster.broadcast(telemetry_packet)

        except Exception as e:
            logger.error(f"💥 Agent Loop Crash: {e}")
            traceback.print_exc()
            logger.info("🔄 Retrying in 5 seconds...")
            await asyncio.sleep(5)
            continue

        # Sleep
        logger.info(f"Adding sleep for {SLEEP_INTERVAL}s")
        await asyncio.sleep(SLEEP_INTERVAL)
