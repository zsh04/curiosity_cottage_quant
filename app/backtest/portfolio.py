from app.backtest.events import SignalEvent, OrderEvent, FillEvent, MarketEvent
from app.backtest.reporting import PerformanceReporter
import queue


class Portfolio:
    """
    Handles positions, cash, and order generation from signals.
    """

    def __init__(self, initial_capital=100000.0, start_date=None):
        self.initial_capital = initial_capital
        self.current_cash = initial_capital
        self.positions = {}  # { 'AAPL': 100 }
        self.holdings = {}  # { 'AAPL': { 'quantity': 100, 'market_value': ... } }
        self.start_date = start_date

        # History for Reporting
        self.history = []  # List of {'timestamp': t, 'total_equity': v}
        self.performance_reporter = PerformanceReporter(self.history)

        # Current Value Snapshot
        self.current_holdings = {"CASH": initial_capital, "TOTAL_HOLDINGS_VALUE": 0.0}

    def update_on_market_event(self, event: MarketEvent):
        """
        Update market value of positions based on new prices.
        """
        sym = event.symbol
        if sym in self.positions:
            qty = self.positions[sym]
            market_val = qty * event.close

            self.holdings[sym] = {
                "quantity": qty,
                "market_value": market_val,
                "last_price": event.close,
            }

        # Calculate Total Equity
        total_holdings_val = sum(h["market_value"] for h in self.holdings.values())
        total_equity = self.current_cash + total_holdings_val

        self.current_holdings["CASH"] = self.current_cash
        self.current_holdings["TOTAL_HOLDINGS_VALUE"] = total_holdings_val

        # Record History
        self.history.append(
            {"timestamp": event.timestamp, "total_equity": total_equity}
        )

    def update_signal(self, event: SignalEvent, event_queue: queue.Queue):
        """
        Acts on a SignalEvent to generate an OrderEvent.
        Naive implementation: Buy 100 shares on Long, Sell all on Close.
        """
        target_qty = 100  # Fixed size for MVP
        # Physics strategy might want dynamic sizing later

        if event.direction == "LONG":
            # Only buy if we have cash? Naive check
            if self.current_cash >= (
                target_qty * 100
            ):  # Approx check, using 100 as dummy price if needed
                order = OrderEvent(
                    timestamp=event.timestamp,
                    symbol=event.symbol,
                    order_type="MARKET",
                    quantity=target_qty,
                    direction="BUY",
                )
                event_queue.put(order)

        elif event.direction == "EXIT":
            curr_qty = self.positions.get(event.symbol, 0)
            if curr_qty > 0:
                order = OrderEvent(
                    timestamp=event.timestamp,
                    symbol=event.symbol,
                    order_type="MARKET",
                    quantity=curr_qty,
                    direction="SELL",
                )
                event_queue.put(order)

    def update_fill(self, event: FillEvent):
        """
        Updates portfolio positions and cash from a FillEvent.
        """
        fill_dir = 1 if event.direction == "BUY" else -1
        qty = event.quantity * fill_dir
        cost = (
            event.quantity * event.price * fill_dir
        )  # Negative cash impact for buy # Wait.
        # If BUY: qty > 0. Cost > 0. Cash = Cash - Cost.
        # If SELL: qty < 0 (if logic implies). But here usually qty is abs.
        # Code says: fill_dir = 1 (BUY) or -1 (SELL).
        # Cost = qty * price * 1 (BUY) -> Positive Cost -> Cash -= Cost -> Cash decreases. Correct.
        # Cost = qty * price * -1 (SELL) -> Negative Cost -> Cash -= (-Cost) -> Cash Increases. Correct.
        cost = event.quantity * event.price * fill_dir

        commission = getattr(event, "commission", 0.0)
        self.current_cash -= cost + commission

        if event.symbol not in self.positions:
            self.positions[event.symbol] = 0

        self.positions[event.symbol] += qty

        # Clean up if 0
        if self.positions[event.symbol] == 0:
            if event.symbol in self.holdings:
                self.holdings[event.symbol]["market_value"] = 0

        print(
            f"Filled: {event.direction} {event.quantity} {event.symbol} @ {event.price}. Cash: {self.current_cash:.2f}"
        )
