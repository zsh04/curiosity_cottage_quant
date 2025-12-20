import os
import logging
import orjson
import uuid
from datetime import datetime
from faststream import FastStream
from faststream.redis import RedisBroker
from app.core.models import TradeSignal, OrderPacket, Side

# Configure The Gatekeeper
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | TALEB | %(levelname)s | %(message)s"
)
logger = logging.getLogger("execution")

# Initialize The Nervous System
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
broker = RedisBroker(redis_url)
app = FastStream(broker)


class ExecutionService:
    """
    The Gatekeeper (Risk Engine).

    "To bankrupt a fool, give him information." - Nassim Taleb

    Role: Transforms Trade Signals -> Executable Orders.
    Philosophy: Paranoid. Enforces Ruin Constraints.
    """

    def __init__(self, starting_nav=500.0, daily_stop_percent=0.02):
        self.starting_nav = starting_nav
        self.daily_stop_threshold = starting_nav * daily_stop_percent  # $10.00
        self.daily_pnl = 0.0  # Reset daily
        self.orders_filled = 0

    def veto_and_size(self, signal: TradeSignal) -> OrderPacket | None:
        """
        The Hard Stop & Sizing Logic.
        """
        # Rule 3: Ignore HOLD
        if signal.side == Side.HOLD:
            return None

        # Rule 1: The Hard Stop (Ruin Constraint)
        # If we have lost more than 2% of NAV today, CEASE ALL ACTIVITY.
        # Note: daily_pnl is usually negative when losing.
        # So check if daily_pnl <= -threshold
        if self.daily_pnl <= -self.daily_stop_threshold:
            logger.error(
                f"REJECTED: RUIN CONSTRAINT ACTIVE. Daily Loss (${abs(self.daily_pnl):.2f}) > Limit (${self.daily_stop_threshold:.2f})."
            )
            return None

        # Rule 2: Position Sizing (1% Risk Per Trade)
        # Simplified: We risk 1% of NAV.
        # Ideally: Risk = (Entry - Stop) * Qty.
        # Here simplified: Allocate 1% Notionally? No, user said "Calculate quantity based on 1% Risk Per Trade".
        # Formula given: `qty = (nav * 0.01) / price`.
        # This implies a 1% Position Sizing (Notional), not 1% Risk at Stop.
        # (1% of 500 = $5.00 exposure). Very conservative. Good.

        target_exposure = self.starting_nav * 0.01  # $5.00
        qty = target_exposure / signal.price

        # Enforce Minimums? (Micro-account limitations).
        # For now, precise float.

        logger.info(
            f"Risk Check Passed. Exposure Granted: ${target_exposure:.2f} ({qty:.8f} {signal.symbol})."
        )

        # Simulate Fill? No, just Order Generation. (Simulation happens downstream or typically update PnL on separate feedback)
        # For Phase 3, we just emit valid orders.

        return OrderPacket(
            timestamp=datetime.now(),
            signal_id=str(uuid.uuid4()),  # New UUID for the order, or link to signal
            symbol=signal.symbol,
            side=signal.side.value,
            quantity=qty,
            order_type="MARKET",
            risk_check_passed=True,
        )


# Instantiate
taleb = ExecutionService()


@broker.subscriber("strategy.signals")
async def handle_signals(msg: bytes):
    """
    Consumes Trade Signals.
    Applies Risk Gates.
    Publishes Orders.
    """
    try:
        data = orjson.loads(msg)
        # Validate Logic
        # TradeSignal expects standard fields

        # Fix timestamp string to datetime conversion if needed
        # Or let Pydantic handle it if it's ISO formatted
        signal = TradeSignal(**data)

        order = taleb.veto_and_size(signal)

        if order:
            await broker.publish(order.model_dump_json(), channel="execution.orders")

    except Exception as e:
        logger.error(f"Execution Gate Failed: {e}", exc_info=True)
