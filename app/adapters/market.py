import os
import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta, timezone

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockLatestTradeRequest, StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from opentelemetry import trace

from app.adapters.tiingo import TiingoAdapter

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class MarketAdapter:
    """
    Production Market Data Adapter using Alpaca SDK.
    Serves as the Single Source of Truth for Market Data.
    """

    def __init__(self):
        """
        Initialize Alpaca Historical Data Client and Tiingo.
        """
        api_key = os.getenv("ALPACA_API_KEY")
        secret_key = os.getenv("ALPACA_API_SECRET")

        if not api_key or not secret_key:
            logger.warning(
                "ALPACA_API_KEY or ALPACA_API_SECRET not set. MarketAdapter will fail."
            )

        self.client = StockHistoricalDataClient(api_key=api_key, secret_key=secret_key)

        # Initialize Tiingo for news
        try:
            self.tiingo = TiingoAdapter()
        except ValueError as e:
            logger.warning(f"TiingoAdapter initialization failed: {e}")
            self.tiingo = None

    def get_price(self, symbol: str) -> float:
        """
        Fetch the latest trade price for a given symbol.
        """
        try:
            request = StockLatestTradeRequest(symbol_or_symbols=symbol)
            latest_trade = self.client.get_stock_latest_trade(request)

            if symbol in latest_trade:
                price = float(latest_trade[symbol].price)
                return price
            else:
                logger.error(f"No trade data returned for {symbol}")
                return 0.0

        except Exception as e:
            logger.error(f"Failed to fetch current price for {symbol}: {e}")
            return 0.0

    def get_price_history(self, symbol: str, limit: int = 100) -> List[float]:
        """
        Fetch the last `limit` bars of Close Prices.

        Args:
            symbol: Stock ticker.
            limit: Number of bars to return.

        Returns:
            List[float]: Close prices, ordered chronological [Oldest -> Newest].
        """
        try:
            # Heuristic start time: limit * 2 days ago to ensure we cover weekends/holidays
            # We fetch a bit more and slice the tail.
            start_time = datetime.now(timezone.utc) - timedelta(days=limit * 2 + 10)

            # Alpaca limit applies to the result set size
            request = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=TimeFrame.Day,
                start=start_time,
                limit=limit,
                # adjustment='raw' # Optional: if we want unadjusted
            )

            bars = self.client.get_stock_bars(request)

            if symbol not in bars:
                return []

            # Extract close prices
            # Alpaca bars should be chronological by default
            close_prices = [float(bar.close) for bar in bars[symbol]]

            # Ensure we respect the limit if api returned more (unlikely with limit param but safe)
            if len(close_prices) > limit:
                close_prices = close_prices[-limit:]

            return close_prices

        except Exception as e:
            logger.error(f"Failed to fetch price history for {symbol}: {e}")
            return []

    def get_news(self, symbol: str, limit: int = 5) -> List[str]:
        """
        Fetch recent news headlines.
        Returns a clean list of headline strings.
        """
        headlines = []

        # Primary: Tiingo
        if self.tiingo:
            try:
                items = self.tiingo.fetch_news(tickers=symbol, limit=limit)
                if items:
                    for item in items:
                        title = item.get("title")
                        if title:
                            headlines.append(title)
                    return headlines[:limit]
            except Exception as e:
                logger.warning(f"Tiingo news fetch failed: {e}")

        return []

    # --- DEPRECATED METHODS (Compatibility) ---

    def get_current_price(self, symbol: str) -> float:
        """DEPRECATED: Use get_price() instead."""
        # logger.warning("DeprecationWarning: get_current_price is deprecated. Use get_price.")
        return self.get_price(symbol)

    def get_historic_returns(self, symbol: str, lookback: int = 200) -> List[float]:
        """DEPRECATED: Use get_price_history() and calculate returns in Service."""
        # logger.warning("DeprecationWarning: get_historic_returns is deprecated.")
        prices = self.get_price_history(symbol, limit=lookback + 1)
        if len(prices) < 2:
            return []

        returns = [(prices[i] / prices[i - 1]) - 1.0 for i in range(1, len(prices))]
        return returns
