import asyncio
import logging
import traceback
from app.agent.pipeline import app_pipeline
from app.services.state_stream import get_state_broadcaster
from app.services.global_state import is_system_halted

logger = logging.getLogger(__name__)

SLEEP_INTERVAL = 5  # seconds (Real-time Physics)


async def run_agent_service():
    """Main agent service loop - orchestrates The Cognitive Engine indefinitely.

    This is the central coordinator that runs the complete trading pipeline in real-time.
    It fetches market data, runs the agent pipeline (Scanner → Analyst → Risk → Execution),
    and broadcasts telemetry to connected frontends via WebSocket.

    **Pipeline Flow:**
    1. **Halt Check**: Verify emergency kill switch not engaged
    2. **Portfolio Fetch**: Get current positions from Alpaca
    3. **Account Fetch**: Get buying power, cash, PDT status
    4. **Pipeline Execute**: Run app_pipeline (LangGraph)
    5. **Telemetry Broadcast**: Push state to WebSocket clients
    6. **Sleep**: Wait SLEEP_INTERVAL (5s) before next cycle

    **Responsibilities:**
    - Portfolio awareness (feed current positions to Risk node)
    - T+1 settlement tracking (buying_power, pdt_exempt)
    - Crash recovery (try/except with 5s retry)
    - Real-time telemetry broadcasting

    **State Management:**
    - Maintains inputs dict with portfolio, wallet, messages
    - Executes pipeline with fresh state each cycle
    - Broadcasts final_state as TELEMETRY packet

    Raises:
        Never exits - catches all exceptions and retries

    Note:
        Designed to run forever as background asyncio task.
        Uses SLEEP_INTERVAL global for cycle timing (default: 5s).

    Example:
        >>> # In main.py
        >>> asyncio.create_task(run_agent_service())
    """
    logger.info("🚀 Agent Service Started")
    broadcaster = get_state_broadcaster()

    # Initialize Execution Client for Portfolio Awareness
    from app.execution.alpaca_client import AlpacaClient

    alpaca = AlpacaClient()

    # Initial inputs
    inputs = {
        "messages": [],
    }

    logger.info("🧠 Cognitive Engine: Online (Linear Pipeline)")

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
                inputs["current_positions"] = [p.dict() for p in positions]
                logger.info(
                    f"💼 Portfolio: {len(inputs['current_positions'])} positions loaded."
                )
            except Exception as e:
                logger.error(f"Failed to fetch portfolio: {e}")
                inputs["current_positions"] = []

            # Phase 48: Fetch Account (Wallet) for T+1 Logic
            try:
                account = await alpaca.get_account_async()
                if account:
                    # Map Alpaca Account attributes to Agent State
                    inputs["cash"] = float(account.cash)
                    inputs["buying_power"] = float(account.buying_power)

                    # Phase 49: Dynamic PDT Threshold
                    # If Equity >= 25,000, we are exempt from PDT / T+1 Locks
                    equity = (
                        float(account.equity)
                        if hasattr(account, "equity")
                        else float(account.portfolio_value)
                    )
                    inputs["pdt_exempt"] = equity >= 25000.0

                    inputs["unsettled_cash"] = (
                        0.0  # Placeholder if not explicitly available, reliant on BP
                    )
                else:
                    inputs["buying_power"] = 0.0
                    inputs["cash"] = 0.0
                    inputs["pdt_exempt"] = False

                logger.info(f"💰 Wallet: BP=${inputs.get('buying_power', 0):.2f}")
            except Exception as e:
                logger.error(f"Failed to fetch account wallet: {e}")
                inputs["buying_power"] = 0.0

            logger.info("--- 🧠 Agent Loop: Thinking ---")

            # Run the Pipeline (Linear Mode)
            current_state = inputs.copy()
            current_state["timestamp"] = "now"  # Or proper ISO

            # Execute Pipeline
            final_state = await app_pipeline.run(current_state)

            # Update inputs for next iteration if needed (memory)
            # inputs = final_state # Optional: Persist state between ticks?

            # Broadcast Updates (Simplified for Linear)
            # We can construct node packets if pipeline emits them?
            # For now, just broadcast the final telemetry.

            # Generate Telemetry Packet

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
