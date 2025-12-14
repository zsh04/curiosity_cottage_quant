from app.backtest.events import SignalEvent, OrderEvent, FillEvent, MarketEvent
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

    def update_on_market_event(self, event: MarketEvent):
        """
        Update market value of positions based on new prices.
        """
        sym = event.symbol
        if sym in self.positions:
            qty = self.positions[sym]
            params = self.holdings.get(sym, {})
            params["market_value"] = qty * event.close
            params["last_price"] = event.close
            self.holdings[sym] = params

    def update_signal(self, event: SignalEvent, event_queue: queue.Queue):
        """
        Acts on a SignalEvent to generate an OrderEvent.
        Naive implementation: Buy 100 shares on Long, Sell all on Close.
        """
        target_qty = 100  # Fixed size for MVP

        if event.direction == "LONG":
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
        cost = event.quantity * event.price * fill_dir  # Negative cash impact for buy

        self.current_cash -= cost + event.commission

        if event.symbol not in self.positions:
            self.positions[event.symbol] = 0

        self.positions[event.symbol] += qty

        print(
            f"Filled: {event.direction} {event.quantity} {event.symbol} @ {event.price}. Cash: {self.current_cash:.2f}"
        )
