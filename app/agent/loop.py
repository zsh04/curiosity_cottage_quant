import asyncio
import logging
import traceback
from app.agent.graph import app_graph
from app.services.state_stream import get_state_broadcaster
from app.services.global_state import is_system_halted

logger = logging.getLogger(__name__)

SLEEP_INTERVAL = 5  # seconds (Real-time Physics)


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

    # Initialize Execution Client for Portfolio Awareness
    from app.execution.alpaca_client import AlpacaClient

    alpaca = AlpacaClient()

    # Initial inputs
    inputs = {
        "messages": [],
    }

    logger.info("🧠 Cognitive Engine: Online")

    while True:
        # --- EMERGENCY HALT CHECK ---
        if is_system_halted():
            logger.warning("🛑 System HALTED by Emergency Kill Switch. Pausing...")
            await asyncio.sleep(10)
            continue

        try:
            logger.info("🧠 Cognitive Engine: Heartbeat...")

            # Phase 13: Fetch Current Portfolio for Risk Node
            try:
                positions = alpaca.get_positions()
                # Format for AgentState check if needed, Alpaca returns list of Position objects
                # We convert to dict for State
                inputs["current_positions"] = [p.dict() for p in positions]
                logger.info(
                    f"💼 Portfolio: {len(inputs['current_positions'])} positions loaded."
                )
            except Exception as e:
                logger.error(f"Failed to fetch portfolio: {e}")
                inputs["current_positions"] = []

            logger.info("--- 🧠 Agent Loop: Thinking ---")

            # Run the Graph - Streaming Mode for "Consciousness Stream"
            # We iterate through the graph execution step-by-step
            current_state = inputs.copy()

            async for event in app_graph.astream(inputs, stream_mode="updates"):
                for node_name, update in event.items():
                    logger.info(f"🧠 Graph Update from [{node_name}]")

                    # Merge update into current state for final telemetry
                    current_state.update(update)

                    # Broadcast NODE_UPDATE event
                    node_packet = {
                        "type": "NODE_UPDATE",
                        "node": node_name,
                        "timestamp": "now",  # Helper or real isoformat
                        "symbol": current_state.get("symbol", "UNKNOWN"),
                        "payload": update,  # Raw update from the node
                    }

                    # Special logic for Risk Verdict
                    if node_name == "risk" and "approved_size" in update:
                        node_packet["type"] = "TOURNAMENT_VERDICT"
                        node_packet["payload"]["rationale"] = current_state.get(
                            "reasoning", ""
                        )

                    await broadcaster.broadcast(node_packet)

            # Final State Construction for Legacy Telemetry (Pulse)
            final_state = current_state

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
                    "price": final_state.get("price", 0.0),
                    "alpha": final_state.get("current_alpha", 0.0),  # From heavy tail
                    "regime": final_state.get("regime", "Unknown"),
                    "velocity": final_state.get("velocity", 0.0),  # From Kalman
                    "acceleration": final_state.get("acceleration", 0.0),  # From Kalman
                    "history": final_state.get(
                        "history", []
                    ),  # OHLC history for charts
                },
                "forecast": final_state.get(
                    "chronos_forecast", {}
                ),  # Chronos predictions
                "scanner": final_state.get(
                    "watchlist", []
                ),  # Quantum Scanner Candidates
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

            # DEBUG: Log Telemetry Price
            current_price = telemetry_packet["market"]["price"]
            current_symbol = telemetry_packet["market"]["symbol"]
            current_vel = telemetry_packet["market"]["velocity"]
            logger.info(
                f"📡 BROADCAST: {current_symbol} Price={current_price} Vel={current_vel}"
            )

            logger.info("📡 Broadcasting Final State...")
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
