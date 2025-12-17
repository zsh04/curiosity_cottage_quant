from app.adapters.market import MarketAdapter
from app.adapters.sentiment import SentimentAdapter
import logging
from typing import Dict, Any, List
from opentelemetry import trace
from app.core import metrics as business_metrics

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class MarketService:
    """
    Market Service: Unified data aggregation layer.
    Provides: Price, History, News, Sentiment
    """

    def __init__(self):
        self.market_adapter = MarketAdapter()
        self.sentiment_adapter = SentimentAdapter()

    @tracer.start_as_current_span("market_get_snapshot")
    def get_market_snapshot(self, symbol: str) -> Dict[str, Any]:
        """
        Fetches a complete market/sensory snapshot for the Analyst.

        This is the "Sensor Fusion" layer - aggregates:
            - Real-time price
            - Historical bars (for physics/forecasting)
            - News headlines
            - Sentiment analysis

        Returns:
            {
                'symbol': str,
                'price': float,
                'history': List[float],    # Chronological close prices
                'news': List[str],         # List of headlines
                'sentiment': dict,         # FinBERT result {label, score}
            }
        """
        span = trace.get_current_span()
        span.set_attribute("market.symbol", symbol)

        logger.info(f"🛒 MarketService: Fetching snapshot for {symbol}")

        # 1. Fetch Current Price
        try:
            price = self.market_adapter.get_current_price(symbol)
            span.set_attribute("market.price", price)

            # Record market price metric
            business_metrics.market_price.set(price, {"symbol": symbol})
        except Exception as e:
            logger.error(f"MarketService: Failed to get price: {e}")
            price = 0.0
            span.set_attribute("market.price_error", str(e))

        # 2. Fetch Historical Prices
        try:
            history = self.market_adapter.get_price_history(symbol, limit=100)
            span.set_attribute("market.history_length", len(history))
        except Exception as e:
            logger.error(f"MarketService: Failed to get history: {e}")
            history = []
            span.set_attribute("market.history_error", str(e))

        # 3. Fetch News
        try:
            news_headlines = self.market_adapter.get_news(symbol, limit=5)
            span.set_attribute("market.news_count", len(news_headlines))
        except Exception as e:
            logger.error(f"MarketService: Failed to get news: {e}")
            news_headlines = []
            span.set_attribute("market.news_error", str(e))

        # 4. Generate News Context & Sentiment
        news_context = "No recent news."

        if news_headlines:
            try:
                # Combine headlines for context
                news_context = " | ".join(news_headlines)

                # Analyze Sentiment using FinBERT
                sentiment_result = self.sentiment_adapter.analyze(news_context)
                span.set_attribute(
                    "market.sentiment", sentiment_result.get("label", "neutral")
                )
                span.set_attribute(
                    "market.sentiment_score", sentiment_result.get("score", 0.0)
                )
            except Exception as e:
                sentiment_result = {"label": "neutral", "score": 0.0}
                logger.error(f"MarketService: Sentiment analysis failed: {e}")
                sentiment_result["error"] = str(e)
                span.set_attribute("market.sentiment_error", str(e))
        else:
            sentiment_result = {"label": "neutral", "score": 0.0}

        return {
            "symbol": symbol,
            "price": price,
            "history": history,
            "news": news_headlines,
            "sentiment": sentiment_result,
        }

    @tracer.start_as_current_span("market_scan")
    def scan_market(self, symbols: List[str]) -> Dict[str, Any]:
        """
        Scan multiple symbols for Macro Analysis.
        Returns a dictionary of snapshots.
        """
        try:
            return self.market_adapter.get_snapshots(symbols)
        except Exception as e:
            logger.error(f"MarketService: Scan failed: {e}")
            return {}

    def get_startup_bars(self, symbol: str, limit: int = 100) -> List[float]:
        """
        Fetch historical bars specifically for system warm-up (Physics/Kalman/LSTM).
        """
        try:
            logger.info(f"🔥 Warming up data for {symbol} (Limit: {limit})...")
            return self.market_adapter.get_price_history(symbol, limit=limit)
        except Exception as e:
            logger.error(f"MarketService: Warm-up fetch failed: {e}")
            return []
            return []

    def get_chart_history(self, symbol: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Fetch OHLCV history for valid charts.
        """
        try:
            return self.market_adapter.get_rich_history(symbol, limit=limit)
        except Exception as e:
            logger.error(f"MarketService: Chart history fetch failed: {e}")
            return []
