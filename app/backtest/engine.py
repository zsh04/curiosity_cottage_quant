import queue
import time
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Tuple
from dataclasses import dataclass

from opentelemetry import trace

from app.backtest.events import Event, MarketEvent, SignalEvent, OrderEvent, FillEvent


logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


@dataclass
class LatencyBufferItem:
    """
    Represents an event waiting in the latency buffer.

    Simulates agent "thinking time" before signals are processed.
    """

    event: Event
    trigger_time: datetime  # Time when this event should be processed


class BacktestEngine:
    """
    Event-driven backtesting engine with Agent Latency Simulation.

    Features:
    - Simulates realistic agent processing delays (e.g., LLM inference time)
    - Clock management based on market event timestamps
    - Latency buffer for delayed signal processing
    - OpenTelemetry instrumentation for performance analysis

    Example:
        engine = BacktestEngine(
            data_feed=feed,
            portfolio=portfolio,
            execution_handler=handler,
            strategy=strategy,
            agent_latency_ms=2000  # 2 seconds thinking time
        )
        engine.run()
    """

    def __init__(
        self,
        data_feed,
        portfolio,
        execution_handler,
        strategy=None,
        agent_latency_ms: int = 2000,  # Default: 2 second agent latency
    ):
        """
        Initialize backtest engine.

        Args:
            data_feed: Provides historical market data
            portfolio: Manages positions and P&L
            execution_handler: Simulates order execution
            strategy: Trading strategy/agent
            agent_latency_ms: Simulated agent processing time in milliseconds
        """
        self.events: queue.Queue = queue.Queue()
        self.data_feed = data_feed
        self.portfolio = portfolio
        self.execution_handler = execution_handler
        self.strategy = strategy
        self.continue_backtest = True

        # Clock Management
        self.current_time: Optional[datetime] = None
        self.agent_latency_ms = agent_latency_ms

        # Latency Buffer: (event, trigger_time)
        self.latency_buffer: List[LatencyBufferItem] = []

        # Telemetry Metrics
        self.total_market_events = 0
        self.total_signals = 0
        self.total_orders = 0
        self.total_fills = 0
        self.signals_delayed = 0
        self.max_buffer_size = 0

    @tracer.start_as_current_span("backtest_run")
    def run(self):
        """
        Main Event Loop with Latency Simulation.

        Process Flow:
        1. Update market data (sets current_time)
        2. Process latency buffer (delayed signals)
        3. Process immediate events (market, order, fill)
        4. Signals go into latency buffer with delay
        """
        span = trace.get_current_span()
        span.set_attribute("backtest.agent_latency_ms", self.agent_latency_ms)

        logger.info(
            f"🚀 Starting Backtest with {self.agent_latency_ms}ms agent latency..."
        )
        start_time = time.time()

        while self.continue_backtest:
            try:
                # Step 1: Fetch new market data
                if self.data_feed.continue_backtest:
                    self.data_feed.update_bars(self.events)
                else:
                    self.continue_backtest = False
            except StopIteration:
                self.continue_backtest = False

            # Step 2: Process the Event Queue
            while True:
                try:
                    event = self.events.get(False)
                except queue.Empty:
                    break

                if event is not None:
                    self._process_event(event)

            # Step 3: Process Latency Buffer (check for ready signals)
            self._process_latency_buffer()

            # Track max buffer size for telemetry
            self.max_buffer_size = max(self.max_buffer_size, len(self.latency_buffer))

        # Final flush of latency buffer
        self._flush_latency_buffer()

        elapsed = time.time() - start_time
        logger.info(f"✅ Backtest finished in {elapsed:.2f}s")

        # Log telemetry summary
        self._log_telemetry_summary(span)

    def _process_event(self, event: Event):
        """
        Route event to appropriate handler.

        MARKET events update clock and trigger portfolio/strategy.
        SIGNAL events go to latency buffer (simulated agent delay).
        ORDER and FILL events process immediately.
        """
        if event.type == "MARKET":
            self._handle_market_event(event)

        elif event.type == "SIGNAL":
            self._handle_signal_event(event)

        elif event.type == "ORDER":
            self._handle_order_event(event)

        elif event.type == "FILL":
            self._handle_fill_event(event)

    @tracer.start_as_current_span("handle_market_event")
    def _handle_market_event(self, event: MarketEvent):
        """
        Process market data event.

        1. Update backtest clock to market timestamp
        2. Update portfolio with latest prices
        3. Trigger strategy signal generation
        """
        span = trace.get_current_span()

        # Update clock
        self.current_time = event.timestamp
        span.set_attribute("backtest.current_time", self.current_time.isoformat())

        # Update portfolio with latest market data
        self.portfolio.update_on_market_event(event)

        # Update Execution Handler Cache (Fix for Race Condition)
        if hasattr(self.execution_handler, "on_market_data"):
            self.execution_handler.on_market_data(event)

        # Generate signals from strategy/agent
        if self.strategy:
            self.strategy.calculate_signals(event, self.events)

        self.total_market_events += 1

    @tracer.start_as_current_span("handle_signal_event")
    def _handle_signal_event(self, event: SignalEvent):
        """
        Handle signal by adding to latency buffer.

        Simulates agent "thinking time" before signal is actionable.
        Signal will be processed after agent_latency_ms delay.
        """
        span = trace.get_current_span()
        span.set_attribute("signal.symbol", event.symbol)
        span.set_attribute("signal.direction", event.direction)
        span.set_attribute("signal.strength", event.strength)

        # Calculate trigger time (current_time + latency)
        if self.current_time is None:
            logger.warning(
                "⚠️  Signal received before any market data. Using signal timestamp."
            )
            trigger_time = event.timestamp + timedelta(
                milliseconds=self.agent_latency_ms
            )
        else:
            trigger_time = self.current_time + timedelta(
                milliseconds=self.agent_latency_ms
            )

        # Add to latency buffer
        buffer_item = LatencyBufferItem(event=event, trigger_time=trigger_time)
        self.latency_buffer.append(buffer_item)

        self.total_signals += 1
        self.signals_delayed += 1

        span.set_attribute("signal.trigger_time", trigger_time.isoformat())
        span.set_attribute("backtest.buffer_size", len(self.latency_buffer))

        logger.debug(
            f"📥 Signal buffered: {event.direction} {event.symbol} "
            f"(trigger at {trigger_time.strftime('%H:%M:%S')})"
        )

    def _handle_order_event(self, event: OrderEvent):
        """Process order event immediately."""
        self.execution_handler.execute_order(event, self.events)
        self.total_orders += 1

    def _handle_fill_event(self, event: FillEvent):
        """Process fill event immediately."""
        self.portfolio.update_fill(event)
        self.total_fills += 1

    @tracer.start_as_current_span("process_latency_buffer")
    def _process_latency_buffer(self):
        """
        Check latency buffer for signals ready to process.

        Processes all signals where trigger_time <= current_time.
        Maintains chronological order by processing oldest first.
        """
        if not self.latency_buffer or self.current_time is None:
            return

        span = trace.get_current_span()
        span.set_attribute("buffer.size_before", len(self.latency_buffer))

        # Sort by trigger time (oldest first)
        self.latency_buffer.sort(key=lambda item: item.trigger_time)

        # Process ready signals
        ready_signals = []
        remaining_signals = []

        for item in self.latency_buffer:
            if item.trigger_time <= self.current_time:
                ready_signals.append(item)
            else:
                remaining_signals.append(item)

        # Update buffer
        self.latency_buffer = remaining_signals

        # Process ready signals
        for item in ready_signals:
            logger.debug(
                f"⚡ Processing delayed signal: {item.event.direction} {item.event.symbol} "
                f"(delayed by {(self.current_time - item.event.timestamp).total_seconds():.2f}s)"
            )
            self.portfolio.update_signal(item.event, self.events)

        span.set_attribute("buffer.signals_processed", len(ready_signals))
        span.set_attribute("buffer.size_after", len(self.latency_buffer))

    def _flush_latency_buffer(self):
        """
        Process all remaining signals in buffer at end of backtest.

        Called when backtest finishes to ensure no signals are lost.
        """
        if not self.latency_buffer:
            return

        logger.warning(
            f"⚠️  Flushing {len(self.latency_buffer)} remaining signals from latency buffer"
        )

        for item in self.latency_buffer:
            self.portfolio.update_signal(item.event, self.events)

        self.latency_buffer.clear()

    def _log_telemetry_summary(self, span):
        """Log comprehensive telemetry metrics."""
        span.set_attribute("backtest.total_market_events", self.total_market_events)
        span.set_attribute("backtest.total_signals", self.total_signals)
        span.set_attribute("backtest.total_orders", self.total_orders)
        span.set_attribute("backtest.total_fills", self.total_fills)
        span.set_attribute("backtest.signals_delayed", self.signals_delayed)
        span.set_attribute("backtest.max_buffer_size", self.max_buffer_size)

        logger.info("\n" + "=" * 60)
        logger.info("📊 BACKTEST TELEMETRY SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Market Events:     {self.total_market_events}")
        logger.info(f"Signals Generated: {self.total_signals}")
        logger.info(f"Signals Delayed:   {self.signals_delayed}")
        logger.info(f"Orders Executed:   {self.total_orders}")
        logger.info(f"Fills Processed:   {self.total_fills}")
        logger.info(f"Max Buffer Size:   {self.max_buffer_size}")
        logger.info(f"Agent Latency:     {self.agent_latency_ms}ms")
        logger.info("=" * 60 + "\n")
