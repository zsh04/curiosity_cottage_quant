import logging
from app.agent.state import AgentState, TradingStatus
from app.agent.nodes.macro import macro_node
from app.agent.nodes.analyst import analyst_node
from app.agent.nodes.risk import risk_node
from app.services.simons import ExecutionAgent

logger = logging.getLogger(__name__)


class TradingPipeline:
    """
    The Linear Trading Pipeline.
    Architecture: Phase 17 (Linear Flow)
    Flow: Macro -> Analyst -> Risk -> Execution
    """

    def __init__(self):
        self.execution_agent = ExecutionAgent()
        logger.info("🚂 TradingPipeline Initialized (Linear Architecture)")

    async def run(self, initial_state: AgentState) -> AgentState:
        """
        Executes the full cognitive cycle for one tick/cycle.
        """
        state = initial_state
        cycle_id = state.get("cycle_id", "unknown")

        try:
            # --- 1. MACRO NODE (The Scanner) ---
            # Determine universe context, broad market regime.
            # In V2, this might select the symbol if not provided, or just add context.
            # For now, we assume it enhances state.
            state = macro_node(state)

            # --- 2. ANALYST NODE (The Brain) ---
            # Deep analysis, Reason + Council Strategies.
            # Output: signal_side, signal_confidence, reasoning
            state = await analyst_node(state)

            # --- 3. RISK NODE (The Gate) ---
            # Physics Veto, Portfolio Constraints, Sizing.
            # Output: approved_size, status (ACTIVE/HALTED)
            state = risk_node(state)

            # --- 4. VETO CHECK ---
            # --- 4. VETO CHECK ---
            if state.get("status") in [
                TradingStatus.HALTED_PHYSICS,
                TradingStatus.HALTED_DRAWDOWN,
                TradingStatus.HALTED_SYSTEM,
            ]:
                logger.info(f"🛑 Cycle {cycle_id} HALTED by Risk Gate.")
                return state

            # --- 5. EXECUTION NODE (The Hands) ---
            # If size validated, route to broker.
            approved_size = state.get("approved_size", 0.0)
            if approved_size > 0:
                logger.info(
                    f"⚡ Executing Trade for Cycle {cycle_id} | Size: ${approved_size}"
                )
                state = self.execution_agent.execute(state)
            else:
                logger.info(f"💤 No Execution for Cycle {cycle_id} (Size 0)")

        except Exception as e:
            logger.error(f"💥 Pipeline Crash in Cycle {cycle_id}: {e}", exc_info=True)
            state["status"] = TradingStatus.HALTED_SYSTEM
            state["error"] = str(e)

        finally:
            self._finalize_cycle(state)

        return state

    def _finalize_cycle(self, state: AgentState):
        """
        Persist state and emit final metrics.
        """
        # (Optional) Deep persistence/logging here if not handled by nodes.
        pass


# Global Pipeline Instance
app_pipeline = TradingPipeline()
