from app.agent.state import AgentState
import json


def calculate_position_size(
    confidence: float, regime: str, account_equity: float = 100000.0
) -> float:
    """
    Simple position sizing logic.
    """
    base_risk = 0.02  # Risk 2% per trade

    if regime == "BULLISH":
        base_risk *= 1.5
    elif regime == "BEARISH":
        base_risk *= 0.5
    elif regime == "VOLATILE":
        base_risk *= 0.25  # Reduce size in volatility

    # Scale by confidence (0-100)
    size_factor = confidence / 100.0
    risk_amount = account_equity * base_risk * size_factor

    return risk_amount


def execution_agent(state: AgentState):
    """
    Execution Agent: Sizes the trade and prepares the order.
    """
    print("--- Execution Agent Reasoning ---")

    candidates = state.get("candidate_trades", [])
    regime = state.get("market_regime", "NEUTRAL")

    final_orders = []

    for trade in candidates:
        symbol = trade.get("symbol")
        action = trade.get("action")
        confidence = trade.get("confidence", 50)
        price = 150.0  # TODO: Get real price

        # Sizing
        risk_amt = calculate_position_size(confidence, regime)
        qty = int(
            risk_amt / price
        )  # Simplified: Assuming risk_amt is total position value for now
        # Real Kelly uses prob of win/loss

        if qty > 0:
            order = {
                "symbol": symbol,
                "qty": qty,
                "side": action.lower(),
                "type": "market",
                "time_in_force": "day",
            }
            final_orders.append(order)
            print(f"Generated Order: {order}")
        else:
            print(f"Trade rejected: Size too small (Risk Amt: {risk_amt})")

    return {"final_orders": final_orders, "next_step": "END"}
