"""
Execution Agent Node.
Responsible for executing trades based on Risk-approved sizing.
"""

import time
import logging
import uuid
from app.agent.state import AgentState, TradingStatus
from app.services.global_state import get_global_state_service, get_current_snapshot_id
from app.execution.alpaca_client import AlpacaClient
from app.core.config import settings

logger = logging.getLogger(__name__)


class ExecutionAgent:
    """
    Manages order lifecycle, executing trades that have passed the Iron Gate (Risk).
    """

    def __init__(self):
        # Initialize Alpaca Client (will be None or inactive if keys/flag missing)
        self.alpaca = AlpacaClient()

    def execute(self, state: AgentState) -> AgentState:
        """
        Executes the trade if validated and approved.
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
            velocity = state.get("velocity", 0.0)  # NEW: Velocity for momentum scaling

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

            # Dynamic Slippage Buffer Logic
            # Base Buffer: 0.1% (Standard)
            # Alpha Penalty: If Alpha < 1.5 (Volatile), add 0.5%
            # Velocity Penalty: If Momentum is high, market moves fast. Add proportional buffer.
            # Formula: Buffer = 0.001 + (AlphaPenalty) + (VelocityFactor)

            base_buffer = 0.001
            alpha_penalty = 0.005 if alpha < 1.5 else 0.0
            velocity_penalty = min(
                0.005, abs(velocity) * 0.01
            )  # Cap at 0.5% extra for velocity

            buffer_pct = base_buffer + alpha_penalty + velocity_penalty

            limit_price = 0.0
            if signal_side == "BUY":
                limit_price = price * (1 + buffer_pct)
            elif signal_side == "SELL":
                limit_price = price * (1 - buffer_pct)

            # Round to 2 decimals
            limit_price = round(limit_price, 2)

            # 4. SAFETY SWITCH: Live/Paper vs Simulation
            if settings.LIVE_TRADING_ENABLED:
                # --- LIVE FIRE (or Paper API) ---
                try:
                    order = self.alpaca.submit_order(
                        symbol=symbol,
                        qty=round(qty, 4),  # Alpaca support fractional
                        side=signal_side,
                        limit_price=limit_price,  # USE LIMIT
                    )
                    log_msg = (
                        f"🚀 LIMIT ORDER SENT: {signal_side} {qty:.4f} {symbol} "
                        f"@ ${limit_price:.2f} (Buffer: {buffer_pct:.2%}) | ID: {order.id}"
                    )
                    logger.warning(log_msg)

                    state["execution_status"] = (
                        "FILLED"  # Optimistic assumption for state
                    )
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

                log_msg = (
                    f"🧪 PAPER TRADE (SIMULATED): Would {signal_side} {qty:.4f} {symbol} "
                    f"LIMIT @ ${limit_price:.2f} (Buffer: {buffer_pct:.2%} | α={alpha:.2f}, v={velocity:.4f})"
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


def execution_node(state: AgentState) -> AgentState:
    """
    LangGraph node for execution.
    """
    agent = ExecutionAgent()
    return agent.execute(state)
