"""
Execution Agent Node.
Responsible for executing trades based on Risk-approved sizing.
"""

import time
from app.core.telemetry import tracer
import logging
import uuid
from app.agent.state import AgentState, TradingStatus
from app.services.global_state import get_global_state_service, get_current_snapshot_id
from app.execution.alpaca_client import AlpacaClient
from app.core.config import settings

logger = logging.getLogger(__name__)


class SimonsAgent:
    """Jim Simons - The Execution Quant with HFT-style limit order logic.

    Named after Jim Simons (Renaissance Technologies), this agent handles
    trade execution with dynamic slippage buffering and T+1 settlement awareness.

    **Core Mission:**
    Execute risk-approved trades via Alpaca (live/paper) or simulation,
    with velocity-adjusted limit pricing to minimize slippage.

    **Execution Logic:**
    1. **Validation**: Approved size > 0, status = ACTIVE, price valid
    2. **Dust Filter**: Skip trades < $5 (spread eats micro-orders)
    3. **Dynamic Buffering**: Slippage = 0.1% base + velocity penalty
    4. **Limit Orders**: Use limit price (not market) for control
    5. **Mode Switch**: Live/paper API vs simulation (cash tracking)

    **Slippage Formula:**
    ```
    buffer = 0.001 + abs(velocity) * 0.1
    limit_price = price * (1 ± buffer)
    ```

    **Safety Features:**
    - Minimum notional: $5 (dust protection)
    - Velocity fallback: 0.5% if missing
    - Day orders only (no GTC)
    - Simulation mode for testing

    Attributes:
        alpaca: AlpacaClient instance for API calls

    Example:
        >>> agent = SimonsAgent()
        >>> state = await agent.execute(state)  # Executes trade
        >>> print(state["execution_status"])  # FILLED or SIMULATED
    """

    def __init__(self):
        # Initialize Alpaca Client (will be None or inactive if keys/flag missing)
        self.alpaca = AlpacaClient()

    async def execute(self, state: AgentState) -> AgentState:
        """Execute risk-approved trade with velocity-adjusted limit pricing.

        Applies HFT-style dynamic slippage buffering based on velocity to
        minimize adverse selection while ensuring fills.

        **Execution Flow:**
        1. Extract approved_size, signal_side, price, velocity
        2. Apply validation guards (size, status, price)
        3. Calculate quantity and notional
        4. Apply dust filter ($5 minimum)
        5. Calculate dynamic limit price (velocity-dependent)
        6. Route to Alpaca (live/paper) OR simulate
        7. Record execution metrics (latency, success)

        Args:
            state: Agent state with approved trade parameters

        Returns:
            Updated state with execution_status and order_id

        Side Effects:
            - Submits order to Alpaca if LIVE_TRADING_ENABLED
            - Updates state['cash'] in simulation mode
            - Logs execution via state['messages']
            - Records metrics to global_state_service

        Example:
            >>> state = {"approved_size": 100, "signal_side": "BUY", "price": 50, "velocity": 0.01}
            >>> state = await agent.execute(state)
            >>> assert state["execution_status"] in ["FILLED", "SIMULATED"]
        """
        start_time = time.time()
        success = True
        error_msg = None
        trade_executed = False

        try:
            # 1. Inputs
            approved_size = state.get("approved_size", 0.0)
            signal_side = state.get("signal_side")
            price = state.get("price", 0.0)
            symbol = state.get("symbol")
            status = state.get("status")
            alpha = state.get("current_alpha", 2.0)
            velocity = state.get("velocity")  # Get raw value to check for missing

            # 2. Validation Guard (Risk Veto)
            if approved_size <= 0:
                logger.info(f"⛔ RISK VETO: Size is {approved_size}. No trade.")
                return state

            if status != TradingStatus.ACTIVE:
                logger.info("EXECUTION: BLOCKED (System Not Active)")
                return state

            if price <= 0:
                logger.error(f"EXECUTION: Error - Invalid Price {price}")
                return state

            # 3. Calculate Quantity & Limit Price
            qty = approved_size / price
            notional_value = qty * price

            # Phase 49: Micro-Account Filter (Dust Protection)
            # Avoid sending orders < $5.00 which get eaten by spread
            MIN_NOTIONAL = 5.0
            if notional_value < MIN_NOTIONAL:
                logger.warning(
                    f"EXECUTION: 📉 Trade Value (${notional_value:.2f}) < Min (${MIN_NOTIONAL}). Skipping to save spread."
                )
                return state

            # Dynamic Slippage Buffer Logic (HFT)
            # Base Buffer: 0.1% (Standard)
            # Velocity Penalty: "Scaled factor of abs(velocity)"
            # Safety: If velocity missing, use 0.5%

            base_buffer = 0.001

            if velocity is None:
                buffer_pct = 0.005  # Safety Fallback
                logger.warning(
                    "EXECUTION: ⚠️ Velocity missing. Using 0.5% safety buffer."
                )
            else:
                # Scaling Factor: 0.1 (e.g. Vel=0.01 -> +0.001 bracket)
                buffer_pct = base_buffer + (abs(float(velocity)) * 0.1)

            limit_price = 0.0
            if signal_side == "BUY":
                limit_price = price * (1 + buffer_pct)
            elif signal_side == "SELL":
                limit_price = price * (1 - buffer_pct)

            # Round to 2 decimals (Exchange Requirement)
            limit_price = round(limit_price, 2)

            # 4. SAFETY SWITCH: Live/Paper vs Simulation
            if settings.LIVE_TRADING_ENABLED:
                # --- LIVE FIRE (or Paper API) ---
                try:
                    order = await self.alpaca.submit_order_async(
                        symbol=symbol,
                        qty=round(qty, 4),  # Alpaca support fractional
                        side=signal_side,
                        time_in_force="day",  # Explicit Day order
                        limit_price=limit_price,  # USE LIMIT
                    )
                    log_msg = (
                        f"⚡ HFT EXECUTION: {signal_side} {qty:.4f} {symbol} "
                        f"@ ${limit_price:.2f} (Buffer: {buffer_pct:.2%}) | ID: {order.id}"
                    )
                    logger.warning(log_msg)

                    state["execution_status"] = "FILLED"  # Optimistic
                    state["order_id"] = str(order.id)
                    success = True
                    trade_executed = True

                    # Store message for UI
                    if "messages" not in state:
                        state["messages"] = []
                    state["messages"].append(log_msg)

                except Exception as e:
                    error_msg = f"❌ ALPACA EXECUTION ERROR: {e}"
                    logger.error(error_msg)
                    success = False
                    if "messages" not in state:
                        state["messages"] = []
                    state["messages"].append(error_msg)
            else:
                # --- DRY RUN / SIMULATION ---
                # Update simulation cash (Mocking fill)
                current_cash = state.get("cash", 0.0)
                state["cash"] = current_cash - approved_size

                vel_str = f"{velocity:.4f}" if velocity is not None else "N/A"
                log_msg = (
                    f"🧪 PAPER TRADE (SIMULATED): Would {signal_side} {qty:.4f} {symbol} "
                    f"LIMIT @ ${limit_price:.2f} (Buffer: {buffer_pct:.2%} | α={alpha:.2f}, v={vel_str})"
                )
                logger.info(log_msg)

                state["execution_status"] = "SIMULATED"
                state["order_id"] = "sim_" + str(uuid.uuid4())[:8]
                success = True
                trade_executed = True

                if "messages" not in state:
                    state["messages"] = []
                state["messages"].append(log_msg)

        except Exception as e:
            success = False
            error_msg = f"EXECUTION: 💥 CRASH: {e}"
            logger.exception(error_msg)
            if "messages" not in state:
                state["messages"] = []
            state["messages"].append(error_msg)

        finally:
            # TRACK EXECUTION PERFORMANCE
            latency = (time.time() - start_time) * 1000
            state_service = get_global_state_service()
            snapshot_id = get_current_snapshot_id()
            if state_service and snapshot_id:
                state_service.save_agent_metrics(
                    snapshot_id=snapshot_id,
                    agent_name="execution",
                    latency_ms=latency,
                    success=success,
                    output_data={
                        "trade_executed": trade_executed,
                        "approved_size": state.get("approved_size"),
                        "signal_side": state.get("signal_side"),
                        "limit_price": limit_price,
                        "buffer_pct": buffer_pct,
                    },
                    error=error_msg,
                )

        return state


@tracer.start_as_current_span("node_simons_execution")
async def simons_node(state: AgentState) -> AgentState:
    """
    Simons Node: Execution Logic.
    """
    logger.info("--- NODE: SIMONS (EXECUTION) ---")
    agent = SimonsAgent()
    return await agent.execute(state)
