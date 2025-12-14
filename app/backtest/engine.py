import queue
import time
from typing import Optional
from app.backtest.events import Event, MarketEvent, SignalEvent, OrderEvent, FillEvent


class BacktestEngine:
    """
    The core event-driven backtesting engine.
    It manages the event queue and orchestrates the flow of data between components.
    """

    def __init__(self, data_feed, portfolio, execution_handler, strategy=None):
        self.events: queue.Queue = queue.Queue()
        self.data_feed = data_feed
        self.portfolio = portfolio
        self.execution_handler = execution_handler
        self.strategy = strategy
        self.continue_backtest = True

    def run(self):
        """
        Main Event Loop.
        """
        print("Starting Backtest execution...")
        while self.continue_backtest:
            try:
                # Update the data feed (push new market events to queue)
                if self.data_feed.continue_backtest:
                    self.data_feed.update_bars(self.events)
                else:
                    self.continue_backtest = False
            except StopIteration:
                self.continue_backtest = False

            # Process the Event Queue
            while True:
                try:
                    event = self.events.get(False)
                except queue.Empty:
                    break

                if event is not None:
                    if event.type == "MARKET":
                        self.portfolio.update_on_market_event(event)
                        if self.strategy:
                            self.strategy.calculate_signals(event, self.events)

                    elif event.type == "SIGNAL":
                        self.portfolio.update_signal(event, self.events)

                    elif event.type == "ORDER":
                        self.execution_handler.execute_order(event, self.events)

                    elif event.type == "FILL":
                        self.portfolio.update_fill(event)

            # Sleep to prevent CPU spinning if running in psuedo-realtime mode (optional)
            # time.sleep(0.0)

        print("Backtest finished.")
