from typing import TypedDict, List, Optional, Any, Dict
from typing_extensions import Annotated
import operator


# Define reducer for messages (append behavior)
def add_messages(left: List[Any], right: List[Any]) -> List[Any]:
    return left + right


class AgentState(TypedDict):
    """
    Shared state for the autonomous trading agent graph.
    """

    # Messaging history for LLM context
    messages: Annotated[List[Any], add_messages]

    # Financial Data Snapshot
    market_data: Dict[str, Any]

    # Analysis Outputs
    alpha: float
    regime: str  # 'GAUSSIAN', 'LEVY', 'CAUCHY'

    # Kinematic State
    velocity: float
    acceleration: float

    # Decision Outputs
    risk_score: float
    trade_decision: str  # 'BUY', 'SELL', 'HOLD', 'VETO_PHYSICS'
