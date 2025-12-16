"""
Backtest Execution Handler with Realistic Market Microstructure Simulation

Features:
- Dynamic slippage based on volatility and order size
- Bid-ask spread modeling
- Commission/fee structures (Alpaca tier)
- Market impact modeling
- OpenTelemetry instrumentation
"""

from abc import ABC, abstractmethod
import queue
import logging
import random
from datetime import timedelta
from typing import Optional

import numpy as np
from opentelemetry import trace

from app.backtest.events import OrderEvent, FillEvent, MarketEvent


logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class ExecutionModel(ABC):
    """
    Abstract base class for execution simulation models.

    Subclasses define how orders are filled, including:
    - Slippage calculation
    - Spread modeling
    - Commission/fees
    - Market impact
    """

    @abstractmethod
    def simulate_fill(
        self, order: OrderEvent, market_data: MarketEvent, volatility: float = 0.01
    ) -> tuple[float, float]:
        """
        Simulate order execution and return fill price and commission.

        Args:
            order: The order to execute
            market_data: Current market state
            volatility: Recent volatility estimate (for slippage)

        Returns:
            (fill_price, commission): Tuple of fill price and commission cost
        """
        pass


class RealisticExecution(ExecutionModel):
    """
    Production-grade execution simulator with market microstructure.

    Features:
    1. Dynamic Slippage: Volatility-based + market impact
    2. Bid-Ask Spread: Model spread or use actual if available
    3. Commission: Alpaca-like fee structure ($0.005/share, $1 min)
    4. Partial Fills: 10% rejection rate for limit orders (simulated)

    Parameters:
        spread_bps: Default bid-ask spread in basis points (default: 5bps)
        commission_per_share: Commission per share (default: $0.005)
        min_commission: Minimum commission per order (default: $1.00)
        impact_factor: Market impact multiplier (default: 0.1)
        rejection_rate: Partial fill/rejection probability (default: 0.0)
    """

    def __init__(
        self,
        spread_bps: float = 5.0,  # 5 basis points = 0.05%
        commission_per_share: float = 0.005,  # $0.005/share (Alpaca tier)
        min_commission: float = 1.0,  # $1 minimum
        impact_factor: float = 0.1,  # Market impact coefficient
        rejection_rate: float = 0.0,  # 0% rejection (could be 0.1 for 10%)
    ):
        self.spread_bps = spread_bps
        self.commission_per_share = commission_per_share
        self.min_commission = min_commission
        self.impact_factor = impact_factor
        self.rejection_rate = rejection_rate

    @tracer.start_as_current_span("simulate_fill")
    def simulate_fill(
        self, order: OrderEvent, market_data: MarketEvent, volatility: float = 0.01
    ) -> tuple[float, float]:
        """
        Simulate realistic order execution.

        Process:
        1. Determine base price (mid, bid, or ask)
        2. Apply spread (Buys pay ask, Sells receive bid)
        3. Add slippage (volatility + market impact)
        4. Calculate commission

        Returns:
            (fill_price, commission)
        """
        span = trace.get_current_span()
        span.set_attribute("order.symbol", order.symbol)
        span.set_attribute("order.direction", order.direction)
        span.set_attribute("order.quantity", order.quantity)
        span.set_attribute("order.type", order.order_type)

        # Step 1: Get base price from market data
        mid_price = market_data.close  # Use close as mid price

        # Step 2: Apply Bid-Ask Spread
        spread = mid_price * (self.spread_bps / 10000.0)  # bps to decimal

        if order.direction == "BUY":
            # Buys pay the ask (mid + half spread)
            base_price = mid_price + (spread / 2.0)
        else:  # SELL
            # Sells receive the bid (mid - half spread)
            base_price = mid_price - (spread / 2.0)

        span.set_attribute("execution.spread", spread)
        span.set_attribute("execution.base_price", base_price)

        # Step 3: Apply Dynamic Slippage
        # Slippage = Volatility component + Market Impact component

        # Volatility slippage: Random noise scaled by volatility
        volatility_slippage = np.random.normal(0, volatility)

        # Market impact: Larger orders have more impact
        # Impact scales with sqrt(quantity) to model liquidity
        impact = self.impact_factor * np.sqrt(order.quantity / 100) * volatility

        # Total slippage (positive hurts buyer, negative hurts seller)
        if order.direction == "BUY":
            # Buyers pay more (positive slippage)
            total_slippage = abs(volatility_slippage) + impact
        else:  # SELL
            # Sellers receive less (negative slippage)
            total_slippage = -(abs(volatility_slippage) + impact)

        fill_price = base_price * (1 + total_slippage)

        span.set_attribute("execution.volatility_slippage", volatility_slippage)
        span.set_attribute("execution.market_impact", impact)
        span.set_attribute("execution.total_slippage_pct", total_slippage * 100)
        span.set_attribute("execution.fill_price", fill_price)

        # Step 4: Calculate Commission
        commission = max(
            self.min_commission, order.quantity * self.commission_per_share
        )

        span.set_attribute("execution.commission", commission)

        # Log execution details
        slippage_bps = total_slippage * 10000
        logger.debug(
            f"🎯 Fill: {order.direction} {order.quantity} {order.symbol} "
            f"@ ${fill_price:.2f} (slippage: {slippage_bps:.2f}bps, "
            f"commission: ${commission:.2f})"
        )

        return fill_price, commission


class SimulatedExecutionHandler:
    """
    Execution handler that uses pluggable execution models.

    Orchestrates order execution by:
    1. Receiving OrderEvents from the event queue
    2. Using an ExecutionModel to simulate fill
    3. Generating FillEvents with realistic prices/costs
    4. Adding execution latency

    Args:
        execution_model: The model to use for fill simulation
        latency_ms: Simulated execution latency (default: 100ms)
        data_feed: Reference to data feed for current prices
    """

    def __init__(
        self,
        execution_model: ExecutionModel = None,
        latency_ms: int = 100,
        data_feed=None,
    ):
        self.execution_model = execution_model or RealisticExecution()
        self.latency_ms = latency_ms
        self.data_feed = data_feed

        # Track execution metrics
        self.total_fills = 0
        self.total_commission = 0.0
        self.total_slippage = 0.0

        # Memory for execution (Price Cache)
        self.price_cache = {}

    def on_market_data(self, event: MarketEvent):
        """
        Update local price cache from market event.
        Called by Engine loop to ensure we have the latest price even if DataFeed is desynchronized.
        """
        self.price_cache[event.symbol] = event

    @tracer.start_as_current_span("execute_order")
    def execute_order(self, event: OrderEvent, event_queue: queue.Queue):
        """
        Execute an order and generate a fill event.

        Process:
        1. Get current market data for the symbol
        2. Use execution model to simulate fill
        3. Create FillEvent with realistic price/commission
        4. Add latency and post to event queue

        Args:
            event: OrderEvent to execute
            event_queue: Queue to post FillEvent to
        """
        if event.type != "ORDER":
            return

        span = trace.get_current_span()
        span.set_attribute("execution.latency_ms", self.latency_ms)

        # Get current market data
        market_data = self._get_current_market_data(event.symbol)

        # Fallback to cache if DataFeed returns None (Race Condition Fix)
        if market_data is None:
            market_data = self.price_cache.get(event.symbol)

        if market_data is None:
            logger.warning(
                f"⚠️ SKIPPING: No market data available for {event.symbol}, cannot execute order"
            )
            return

        # Simulate fill using execution model
        # TODO: Calculate volatility from recent price history
        # For now, use fixed 1% daily volatility
        volatility = 0.01

        fill_price, commission = self.execution_model.simulate_fill(
            order=event, market_data=market_data, volatility=volatility
        )

        # Calculate fill cost (total dollar value)
        fill_cost = fill_price * event.quantity

        # Create fill event
        fill_event = FillEvent(
            timestamp=event.timestamp + timedelta(milliseconds=self.latency_ms),
            symbol=event.symbol,
            exchange="BACKTEST_SIM",
            quantity=event.quantity,
            direction=event.direction,
            fill_cost=fill_cost,
            commission=commission,
            price=fill_price,
        )

        # Track metrics
        self.total_fills += 1
        self.total_commission += commission

        # Calculate slippage vs mid price
        mid_price = market_data.close
        slippage_dollars = abs(fill_price - mid_price) * event.quantity
        self.total_slippage += slippage_dollars

        span.set_attribute("execution.total_fills", self.total_fills)
        span.set_attribute("execution.cumulative_commission", self.total_commission)
        span.set_attribute("execution.cumulative_slippage", self.total_slippage)

        # Post fill event to queue
        event_queue.put(fill_event)

        logger.info(
            f"📈 {event.direction} {event.quantity} {event.symbol} "
            f"FILLED @ ${fill_price:.2f} "
            f"(commission: ${commission:.2f})"
        )

    def _get_current_market_data(self, symbol: str) -> Optional[MarketEvent]:
        """
        Get current market data for a symbol.

        In a real backtest, this would query the data feed.
        For now, we rely on the data feed being accessible.
        """
        if self.data_feed and hasattr(self.data_feed, "get_latest_bar"):
            return self.data_feed.get_latest_bar(symbol)

        # Fallback: Log warning
        logger.warning(
            f"⚠️  Data feed not available, using placeholder market data for {symbol}"
        )
        # Return a placeholder (this should be replaced with actual data feed integration)
        return None

    def get_execution_summary(self) -> dict:
        """
        Return summary of execution metrics.

        Returns:
            Dictionary with total fills, commission, and slippage
        """
        return {
            "total_fills": self.total_fills,
            "total_commission": self.total_commission,
            "total_slippage": self.total_slippage,
            "avg_commission_per_fill": (
                self.total_commission / self.total_fills
                if self.total_fills > 0
                else 0.0
            ),
        }


# Legacy compatibility
class ExecutionHandler(ABC):
    """Abstract base class for backward compatibility."""

    @abstractmethod
    def execute_order(self, event: OrderEvent, event_queue: queue.Queue):
        pass
