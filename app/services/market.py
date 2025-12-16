from app.adapters.market import MarketAdapter
from app.adapters.sentiment import SentimentAdapter
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class MarketService:
    """
    High-Level Market Data Service (Sensor Fusion Layer).
    Consolidates data fetching (Price, History, News) and applies Sentiment Analysis
    to provide a unified 'Market Snapshot' for the Analyst Agent.
    """

    def __init__(self):
        self.market_adapter = MarketAdapter()
        self.sentiment_adapter = SentimentAdapter()

    def get_market_snapshot(self, symbol: str) -> Dict[str, Any]:
        """
        Fetches a complete market/sensory snapshot for the Analyst.

        Steps:
        1. Fetch Price & History (MarketAdapter)
        2. Fetch News (MarketAdapter)
        3. Analyze Sentiment (SentimentAdapter - FinBERT)
        4. Fuse into a single dict.

        Returns:
            {
                'symbol': str,
                'price': float,
                'history': List[float],    # Chronological close prices
                'news_context': str,       # Combined headlines
                'sentiment': dict,         # FinBERT result {label, score}
                'raw_news': List[str]      # List of headlines
            }
        """
        logger.info(f"🛒 MarketService: Fetching snapshot for {symbol}")

        # 1. Fetch Current Price
        try:
            price = self.market_adapter.get_price(symbol)
        except Exception as e:
            logger.error(f"MarketService: Failed to get price: {e}")
            price = 0.0

        # 2. Fetch History (Raw Prices for Physics)
        try:
            # 200 bars is standard for our lookback windows (Physics/Fractal)
            history = self.market_adapter.get_price_history(symbol, limit=200)
        except Exception as e:
            logger.error(f"MarketService: Failed to get history: {e}")
            history = []

        # 3. Fetch News
        try:
            raw_news = self.market_adapter.get_news(symbol, limit=5)
        except Exception as e:
            logger.error(f"MarketService: Failed to get news: {e}")
            raw_news = []

        # 4. Generate News Context & Sentiment
        news_context = "No recent news."
        sentiment_result = {"label": "neutral", "score": 0.0, "error": "no_news"}

        if raw_news:
            try:
                # Combine headlines for context
                news_context = " | ".join(raw_news)

                # Analyze Sentiment using FinBERT
                sentiment_result = self.sentiment_adapter.analyze(news_context)
            except Exception as e:
                logger.error(f"MarketService: Sentiment analysis failed: {e}")
                sentiment_result["error"] = str(e)

        return {
            "symbol": symbol,
            "price": price,
            "history": history,
            "news_context": news_context,
            "sentiment": sentiment_result,
            "raw_news": raw_news,
        }
