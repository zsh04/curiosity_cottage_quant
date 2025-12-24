from app.backtest.events import SignalEvent, OrderEvent, FillEvent, MarketEvent
from app.backtest.reporting import PerformanceReporter
import queue


class Portfolio:
    """Simulated Portfolio Manager for Backtesting.

    Tracks cash, positions, and equity curve. Handles signal-to-order conversion
    and fill updates.

    Attributes:
        current_cash (float): Available cash balance.
        positions (Dict[str, int]): Current quantity per symbol (e.g., {'AAPL': 100}).
        history (List[Dict]): Equity curve history for reporting.
        performance_reporter (PerformanceReporter): Metric calculation helper.
    """

    def __init__(self, initial_capital=100000.0, start_date=None, data_feed=None):
        self.initial_capital = initial_capital
        self.current_cash = initial_capital
        self.positions = {}  # { 'AAPL': 100 }
        self.holdings = {}  # { 'AAPL': { 'quantity': 100, 'market_value': ... } }
        self.latest_prices = {}  # { 'AAPL': 150.0 }
        self.start_date = start_date
        self.data_feed = data_feed

        # History for Reporting
        self.history = []  # List of {'timestamp': t, 'total_equity': v}
        self.performance_reporter = PerformanceReporter(self.history)

        # CurrentValue Snapshot
        self.current_holdings = {"CASH": initial_capital, "TOTAL_HOLDINGS_VALUE": 0.0}

    def update_on_market_event(self, event: MarketEvent):
        """Updates portfolio valuation based on new market data.

        Mark-to-Market (MtM) valuation:
        1. Updates latest price for the symbol.
        2. Re-calculates market value of holdings.
        3. Updates total equity (cash + holdings).
        4. Records snapshot to equity history.

        Args:
            event (MarketEvent): New market data bar.
        """
        sym = event.symbol
        self.latest_prices[sym] = event.close  # Update latest price registry

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
        """Converts valid trade signals into execution orders.

        Logic:
        1.  **Risk Check**: Vetoes signals with low strength/confidence.
        2.  **Sizing**: Calculates quantity based on signal strength (fraction of cash).
        3.  **Generation**: Creates 'MARKET' orders for entry or exit.

        Args:
            event (SignalEvent): The signal to process.
            event_queue (queue.Queue): Order queue to append new orders to.
        """
        # RISK CHECK: Use event.strength from Risk Node
        strength = getattr(
            event, "strength", 1.0
        )  # Default to 1.0 if missing, but usually Risk sets it 0.0-1.0

        # 1. VETO
        if strength <= 0.0:
            print(f"🚫 SIGNAL VETOED BY RISK: {event.symbol} Strength={strength}")
            return

        if event.direction == "LONG":
            # 2. Dynamic Sizing
            target_value = (
                self.current_cash * strength
            )  # e.g. 20% of CASH or NAV? User said holdings['cash'] * strength.
            # Note: Risk approved size is usually "size_notional".
            # If strength is "fraction of portfolio", this works.
            # If strength is "approved_size" (absolute $), then target_value = strength.
            # Assuming 'strength' is the 'approved_size' (absolute value) passed from Risk Node if mapped that way,
            # OR 'strength' is confidence/fraction.
            # Analysing previous step: Risk Node sets `approved_size` (Absolute $).
            # Strategy Wrapper creates SignalEvent.
            # app/backtest/strategy_wrapper.py creates SignalEvent.
            # Let's assume strength = fraction for now as per user formula: target_value = cash * strength logic.
            # User Request: "target_value = self.current_holdings['cash'] * event.strength"
            # Proceeding with specific user instruction.

            # Need Price
            price = 0.0
            if self.data_feed and hasattr(self.data_feed, "get_current_price"):
                try:
                    price = self.data_feed.get_current_price(event.symbol)
                except Exception:
                    price = self.latest_prices.get(event.symbol, 0.0)
            else:
                # Fallback to internal price tracker
                price = self.latest_prices.get(event.symbol, 0.0)

            if price > 0:
                qty = int(target_value / price)

                if qty > 0:
                    order = OrderEvent(
                        timestamp=event.timestamp,
                        symbol=event.symbol,
                        order_type="MARKET",
                        quantity=qty,
                        direction="BUY",
                    )
                    event_queue.put(order)
                    print(
                        f"⚖️ PORTFOLIO: Generated BUY for {qty} {event.symbol} (${target_value:.2f})"
                    )
                else:
                    print(
                        f"⚠️ PORTFOLIO: Calculated Qty is 0 for {event.symbol} (Val=${target_value:.2f} Price=${price:.2f})"
                    )
            else:
                print(f"⚠️ PORTFOLIO: No price for {event.symbol}, cannot size.")

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
        """Updates cash and positions based on executed fills.

        Adjusts:
        - **Cash**: Deducts cost (price * qty) and commissions.
        - **Positions**: Updates held quantity.

        Args:
            event (FillEvent): The execution confirmation details.
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
