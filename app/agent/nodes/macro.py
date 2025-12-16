"""
Macro Agent Node - Protocol #3: Macro Tide
"""

import logging
from app.agent.state import AgentState
from app.agent.macro.agent import MacroAgent

logger = logging.getLogger(__name__)


def macro_node(state: AgentState) -> AgentState:
    """
    Node function for macro regime analysis.

    Responsibilities:
        1. Calculate tail risk (alpha) via Hill Estimator
        2. Measure correlation with US10Y (macro tide)
        3. Set trading status based on physics thresholds

    Returns:
        Updated state with alpha, regime, macro_correlation, and status
    """
    logger.info("🌊 ====== MACRO NODE: Protocol #3 Activated ======")

    # Ensure symbol is in state (for database queries)
    if "symbol" not in state:
        state["symbol"] = "SPY"  # Default symbol

    # Initialize agent and run analysis
    agent = MacroAgent(lookback_days=30)
    state = agent.analyze_regime(state)

    # Enhanced logging with physics metrics
    alpha = state.get("alpha", 0.0)
    correlation = state.get("macro_correlation", 0.0)
    regime = state.get("regime", "Unknown")
    status = state.get("status", "UNKNOWN")

    logger.info(f"📐 Tail Risk (α): {alpha:.3f} | Regime: {regime}")
    logger.info(f"🔗 Macro Tide (ρ): {correlation:.3f} | US10Y Correlation")
    logger.info(f"🚦 Trading Status: {status}")

    # Add audit message
    state["messages"].append(
        {
            "role": "system",
            "content": f"MACRO: α={alpha:.2f}, ρ={correlation:.2f}, Status={status}",
        }
    )

    logger.info("🌊 ====== MACRO NODE: Complete ======\n")
    return state
