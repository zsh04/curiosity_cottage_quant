import os
import logging
from typing import List
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
    Fetches real-time snapshots, historical bars, and news.
    """

    def __init__(self):
        """
        Initialize Alpaca Historical Data Client and Tiingo.
        Reads API credentials from environment variables.
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

    def get_current_price(self, symbol: str) -> float:
        """
        Fetch the latest trade price for a given symbol.

        Args:
            symbol: Stock ticker (e.g., 'SPY')

        Returns:
            float: Latest trade price, or 0.0 on error
        """
        try:
            request = StockLatestTradeRequest(symbol_or_symbols=symbol)
            latest_trade = self.client.get_stock_latest_trade(request)

            if symbol in latest_trade:
                price = float(latest_trade[symbol].price)
                logger.info(f"📊 {symbol} latest price: ${price:.2f}")
                return price
            else:
                logger.error(f"No trade data returned for {symbol}")
                return 0.0

        except Exception as e:
            logger.error(f"Failed to fetch current price for {symbol}: {e}")
            return 0.0

    def get_historic_returns(self, symbol: str, lookback: int = 200) -> List[float]:
        """
        Fetch historical daily bars and calculate percentage returns.

        Args:
            symbol: Stock ticker
            lookback: Number of trading days to fetch (default 200)

        Returns:
            List[float]: List of daily percentage returns, or [] on error
        """
        try:
            # Calculate start time with buffer for weekends/holidays
            start_time = datetime.now(timezone.utc) - timedelta(days=lookback * 2)
            end_time = datetime.now(timezone.utc)

            request = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=TimeFrame.Day,
                start=start_time,
                end=end_time,
            )

            bars = self.client.get_stock_bars(request)

            if symbol not in bars:
                logger.error(f"No bar data returned for {symbol}")
                return []

            # Extract close prices
            close_prices = [float(bar.close) for bar in bars[symbol]]

            if len(close_prices) < 2:
                logger.warning(
                    f"Insufficient data for {symbol}: only {len(close_prices)} bars"
                )
                return []

            # Calculate percentage returns: (price_t / price_t-1) - 1
            returns = [
                (close_prices[i] / close_prices[i - 1]) - 1.0
                for i in range(1, len(close_prices))
            ]

            logger.info(
                f"📈 {symbol} returns: {len(returns)} days (last: {returns[-1]:.4%})"
            )
            return returns

        except Exception as e:
            logger.error(f"Failed to fetch historic returns for {symbol}: {e}")
            return []

    @tracer.start_as_current_span("market_get_news")
    def get_news(self, symbol: str, limit: int = 5) -> List[str]:
        """
        Fetch recent news headlines for a symbol.
        Uses Tiingo as primary source with Alpaca as fallback.

        Args:
            symbol: Stock ticker
            limit: Maximum number of headlines to return

        Returns:
            List[str]: List of headline strings, or [] if both sources fail
        """
        span = trace.get_current_span()
        span.set_attribute("market.symbol", symbol)
        span.set_attribute("market.news_limit", limit)

        headlines = []

        # Primary: Tiingo
        if self.tiingo:
            try:
                span.set_attribute("market.news_source", "tiingo")
                news_items = self.tiingo.fetch_news(tickers=symbol, limit=limit)
                if news_items:
                    headlines = [
                        item.get("title", "")
                        for item in news_items
                        if item.get("title")
                    ]
                    logger.info(
                        f"📰 Tiingo: Fetched {len(headlines)} headlines for {symbol}"
                    )
                    span.set_attribute("market.news_count", len(headlines))
                    span.set_attribute("market.news_success", True)
                    return headlines[:limit]
            except Exception as e:
                logger.warning(f"Tiingo news fetch failed for {symbol}: {e}")
                span.set_attribute("market.tiingo_error", str(e))

        # Fallback: Alpaca News API
        try:
            span.set_attribute("market.news_source", "alpaca_fallback")
            # Alpaca News API endpoint
            # Note: This requires alpaca-py with news support
            # For now, return empty as we don't have Alpaca news configured
            logger.warning(f"Alpaca news fallback not yet implemented for {symbol}")
            return []
        except Exception as e:
            logger.warning(f"Alpaca news fetch failed for {symbol}: {e}")
            span.set_attribute("market.alpaca_error", str(e))

        # Both failed
        if not headlines:
            logger.warning(f"⚠️  No news available for {symbol} from any source")
            span.set_attribute("market.news_success", False)

        return []
