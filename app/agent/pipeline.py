import logging
from app.agent.state import AgentState, TradingStatus
from app.agent.nodes.soros import soros_node
from app.agent.boyd import boyd_node
from app.agent.nodes.taleb import taleb_node
from app.agent.nodes.simons import SimonsAgent, simons_node

logger = logging.getLogger(__name__)


class TradingPipeline:
    """
    The Linear Trading Pipeline.
    Architecture: Phase 17 (Linear Flow)
    Flow: Macro -> Analyst -> Risk -> Execution
    """

    def __init__(self):
        self.simons_agent = SimonsAgent()
        logger.info("🚂 TradingPipeline Initialized (Linear Architecture)")

    async def run(self, initial_state: AgentState) -> AgentState:
        """
        Executes the full cognitive cycle for one tick/cycle.
        """
        state = initial_state
        cycle_id = state.get("cycle_id", "unknown")

        try:
            # --- 1. SOROS (The Philosopher) ---
            # Global Regime Scan
            state = soros_node(state)

            # --- 2. BOYD (The Strategist) ---
            # OODA Loop & Analysis
            state = await boyd_node(state)

            # --- 3. TALEB (The Skeptic) ---
            # Risk Veto & Sizing
            state = taleb_node(state)

            # --- 4. SIMONS (The Quant) ---
            # Execution
            state = simons_node(state)

            # --- 4. VETO CHECK ---
            if state.get("status") in [
                TradingStatus.HALTED_PHYSICS,
                TradingStatus.HALTED_DRAWDOWN,
                TradingStatus.HALTED_SYSTEM,
            ]:
                logger.info(f"🛑 Cycle {cycle_id} HALTED by Risk Gate.")
                return state

            # --- 5. EXECUTION NODE (The Hands) ---
            # Execution logic is handled by simons_node (Line 44).
            # We just log if needed, or rely on state updates.
            if state.get("approved_size", 0.0) > 0:
                logger.info(f"⚡ Cycle {cycle_id} Execution Processed by Simons.")
            else:
                logger.info(f"💤 Cycle {cycle_id} No Execution (Size 0 or Veto).")

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
