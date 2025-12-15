from abc import ABC, abstractmethod
import queue
from datetime import timedelta
from app.backtest.events import OrderEvent, FillEvent
import random


class ExecutionHandler(ABC):
    @abstractmethod
    def execute_order(self, event: OrderEvent, event_queue: queue.Queue):
        pass


class SimulatedExecutionHandler(ExecutionHandler):
    """
    Simulates order execution with latency and slippage.
    """

    def __init__(self, latency_ms=100, slippage_std=0.01):
        self.latency_ms = latency_ms
        self.slippage_std = slippage_std

    def execute_order(self, event: OrderEvent, event_queue: queue.Queue):
        if event.type == "ORDER":
            # Simulate Fill
            # In a real event loop with time, we would schedule this fill in the future.
            # For this MVP, we fill essentially immediately but could timestamp it later.

            # Simple slippage model: Random walk around price (not implemented fully without current price)
            # Assuming LIMIT orders for now filled at price if available, or MARKET
            # For MVP, we need the *current price* to fill.
            # Ideally the ExecutionHandler has access to the DataFeed to know the current price.
            # OR the OrderEvent should optionally contain an estimated price.

            # For simplicity in this step, we will assume a "Fill at Market" logic
            # where we fill at a placeholder price, or we need to pass data access to this handler.
            # Let's assume we fill at the price arriving in the next MarketEvent? No, that complicates.

            # Better approach: The Strategy sends the Order, and we fill it based on the *next* market price
            # or the *last* market price. Let's use a standard assumption: Fill at last close + slippage.

            fill_price = 100.0  # PLACEHOLDER: In real impl, fetch from DataFeed.get_latest_bar(event.symbol)

            commission = max(1.0, event.quantity * 0.005)  # Simple comm model

            fill_event = FillEvent(
                timestamp=event.timestamp + timedelta(milliseconds=self.latency_ms),
                symbol=event.symbol,
                exchange="ALPACA_SIM",
                quantity=event.quantity,
                direction=event.direction,
                fill_cost=0.0,  # Calculated by Portfolio
                commission=commission,
                price=fill_price,
            )
            event_queue.put(fill_event)
