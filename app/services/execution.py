import os
import logging
import orjson
import uuid
from datetime import datetime
from typing import Union, Dict, Any
from faststream import FastStream
from faststream.redis import RedisBroker
from app.core.models import TradeSignal, OrderPacket, Side, ExecutionReport
from app.execution.alpaca_client import AlpacaClient

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
    The Gatekeeper (Risk Engine) & The Liquidator (Execution).

    "To bankrupt a fool, give him information." - Nassim Taleb

    Role: Transforms Trade Signals -> Executable Orders -> Broker.
    Philosophy: Paranoid. Enforces Ruin Constraints.
    """

    def __init__(self, starting_nav=500.0, daily_stop_percent=0.02, broker_client=None):
        self.starting_nav = starting_nav
        self.daily_stop_threshold = starting_nav * daily_stop_percent  # $10.00
        self.daily_pnl = 0.0  # Reset daily
        self.orders_filled = 0
        self.broker = broker_client or AlpacaClient()

    def veto_and_size(self, signal: TradeSignal) -> OrderPacket | None:
        """
        The Hard Stop & Sizing Logic.
        """
        # Rule 3: Ignore HOLD
        if signal.side == Side.HOLD:
            logger.info("HOLD received. Idling.")
            return None

        # Rule 1: The Hard Stop (Ruin Constraint)
        # If we have lost more than 2% of NAV today, CEASE ALL ACTIVITY.
        if self.daily_pnl <= -self.daily_stop_threshold:
            logger.error(
                f"REJECTED: RUIN CONSTRAINT ACTIVE. Daily Loss (${abs(self.daily_pnl):.2f}) > Limit (${self.daily_stop_threshold:.2f})."
            )
            return None

        # Rule 2: Position Sizing (1% Risk Per Trade)
        # Check if signal has quantity override
        if signal.quantity and signal.quantity > 0:
            qty = signal.quantity
            target_exposure = qty * signal.price
            logger.info(f"Signal Specified Quantity: {qty}")
        else:
            # Default Sizing
            target_exposure = self.starting_nav * 0.01  # $5.00
            qty = target_exposure / signal.price

        logger.info(
            f"Risk Check Passed. Exposure Granted: ${target_exposure:.2f} ({qty:.8f} {signal.symbol})."
        )

        return OrderPacket(
            timestamp=datetime.now(),
            signal_id=str(uuid.uuid4()),
            symbol=signal.symbol,
            side=signal.side.value,
            quantity=qty,
            order_type="MARKET",
            risk_check_passed=True,
        )

    def execute_order(self, order: OrderPacket) -> ExecutionReport:
        """
        The Grim Trigger. Executes the order via Broker.
        """
        try:
            logger.info(
                f"⚡ SENDING ORDER: {order.side} {order.quantity} {order.symbol}"
            )

            # Call Alpaca
            # Note: submit_order returns an Order object from Alpaca SDK
            broker_order = self.broker.submit_order(
                symbol=order.symbol,
                qty=order.quantity,
                side=order.side,  # "BUY" or "SELL"
                time_in_force="day",  # default
            )

            # Map response to ExecutionReport
            # Depending on Alpaca SDK, broker_order might contain ID, status, etc.
            # Assuming immediate acceptance (NEW or FILLED if lucky)

            report = ExecutionReport(
                timestamp=datetime.now(),
                order_id=str(broker_order.id),
                symbol=broker_order.symbol,
                side=broker_order.side.value.upper(),  # 'buy' -> 'BUY'
                status=broker_order.status.value.upper(),  # 'new', 'filled'
                price=float(broker_order.filled_avg_price)
                if broker_order.filled_avg_price
                else order.quantity * 0.0,  # Approximate or None
                quantity=float(broker_order.qty)
                if broker_order.qty
                else order.quantity,
            )

            logger.info(f"✅ ORDER SUBMITTED: {report.order_id} [{report.status}]")
            return report

        except Exception as e:
            logger.error(f"Execution Failed: {e}")
            raise e


# Instantiate
taleb = ExecutionService()


from typing import Union, Dict, Any


@broker.subscriber("strategy.signals")
async def handle_signals(msg: Union[bytes, Dict[str, Any]]):
    """
    Consumes Trade Signals.
    Applies Risk Gates.
    Publishes Orders.
    Executes Live.
    """
    try:
        data = orjson.loads(msg) if isinstance(msg, bytes) else msg
        # Validate Logic
        signal = TradeSignal(**data)

        # 1. Risk Check
        order = taleb.veto_and_size(signal)

        if order:
            # 2. Publish Approved Order (Sim/Log)
            await broker.publish(order.model_dump_json(), channel="execution.orders")

            # 3. LIVE EXECUTION
            try:
                report = taleb.execute_order(order)
                await broker.publish(
                    report.model_dump_json(), channel="execution.updates"
                )
            except Exception as exec_err:
                logger.error(f"Live Execution Error: {exec_err}")
                # We could emit a REJECTED report here

    except Exception as e:
        logger.error(f"Execution Gate Failed: {e}", exc_info=True)
