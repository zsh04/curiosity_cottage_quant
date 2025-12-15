from typing import Dict, Any, List
import pandas as pd
from app.data.base import MarketDataProvider
from app.data.alpaca import AlpacaProvider
from app.data.yahoo import YahooFinanceProvider
from app.data.finnhub import FinnhubProvider
from app.data.alpha_vantage import AlphaVantageProvider
from app.data.tiingo import TiingoProvider


class DataAggregator:
    """
    Facade for all market data.
    Handles failover from Alpaca to Yahoo for prices.
    """

    def __init__(self):
        self.alpaca = AlpacaProvider()
        self.yahoo = YahooFinanceProvider()
        self.finnhub = FinnhubProvider()
        self.alpha = AlphaVantageProvider()
        self.tiingo = TiingoProvider()

    def get_price_history(self, symbol: str, limit: int = 100) -> pd.DataFrame:
        """
        Try Alpaca, failover to Yahoo.
        """
        try:
            return self.alpaca.get_bars(symbol, limit=limit)
        except Exception as e:
            print(f"Warning: Alpaca failed for {symbol} ({e}). Switching to Yahoo.")
            return self.yahoo.get_bars(symbol, limit=limit)

    def get_current_price(self, symbol: str) -> float:
        try:
            return self.alpaca.get_current_price(symbol)
        except Exception as e:
            print(f"Alpaca Price Error: {e}")
            try:
                print(f"Falling back to Yahoo Finance for {symbol} price...")
                return self.yahoo.get_current_price(symbol)
            except Exception as e2:
                print(f"Yahoo Price Error: {e2}")
                try:
                    print(f"Falling back to Tiingo for {symbol} price...")
                    return self.tiingo.get_current_price(symbol)
                except Exception as e3:
                    print(f"Tiingo Price Error: {e3}")
                    return 0.0

    def get_macro_context(self) -> Dict[str, Any]:
        """
        Aggregates data for Macro Agent.
        """
        # 1. 10Y Yield
        bond_yield = self.alpha.get_treasury_yield()

        # 2. Sector Performance (using SPY and Sector ETFs via Price Feed)
        sectors = ["SPY", "XLK", "XLE", "XLV", "XLF"]
        perf = {}
        for s in sectors:
            try:
                bars = self.get_price_history(s, limit=5)  # 1 week
                if not bars.empty:
                    close = bars["close"].values
                    ret = (close[-1] - close[0]) / close[0]
                    perf[s] = f"{ret * 100:.2f}%"
            except:
                perf[s] = "0.00%"

        return {
            "Treasury_10Y": f"{bond_yield}%",
            "Sector_Performance": perf,
            "SPY_History": self.get_price_history("SPY", limit=200)[
                "close"
            ].tolist(),  # For Hurst
        }

    def get_sentiment_context(self, symbol: str) -> str:
        """
        Fetches news headlines for sentiment analysis.
        Prioritizes Tiingo, falls back to Finnhub.
        """
        headlines = []
        source_used = "Alpaca"

        # 1. Try Alpaca (Primary)
        try:
            news_items = self.alpaca.get_news(symbol, limit=5)
            if news_items:
                headlines = [
                    item["headline"] for item in news_items if item.get("headline")
                ]
        except Exception as e:
            print(f"Alpaca Sentiment Error: {e}")

        # 2. Try Tiingo (Secondary)
        if not headlines:
            source_used = "Tiingo"
            try:
                news_items = self.tiingo.get_news(symbol, limit=5)
                if news_items:
                    headlines = [
                        item["headline"] for item in news_items if item.get("headline")
                    ]
            except Exception as e:
                print(f"Tiingo Sentiment Error: {e}")

        # 3. Fallback to Finnhub if empty
        if not headlines:
            source_used = "Finnhub"
            try:
                news_items = self.finnhub.get_news(symbol)
                # Finnhub returns dicts specific to its schema
                headlines = [
                    item["headline"] for item in news_items if item.get("headline")
                ]
            except Exception as e:
                print(f"Finnhub Sentiment Error: {e}")

        # Format context
        if not headlines:
            return "No recent news available."

        context = f"Recent News ({source_used}):\n"
        for h in headlines[:5]:
            context += f"- {h}\n"

        return context

    def get_account_data(self) -> Dict[str, Any]:
        """
        Risk Agent needs this.
        """
        # No failover for account data, must come from Broker
        return self.alpaca.get_account_summary()
