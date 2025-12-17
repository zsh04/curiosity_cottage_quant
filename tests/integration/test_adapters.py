import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

# from app.adapters.alpaca import AlpacaAdapter  # DELETED in Audit V2
from app.adapters.tiingo import TiingoAdapter


class TestAdapters:
    # OBSOLETE TEST - AlpacaAdapter was deleted in Audit V2 refactor
    # Now using MarketAdapter -> alpaca-py SDK directly
    # TODO: Write new tests for MarketAdapter and MarketService

    # @patch("app.adapters.alpaca.StockHistoricalDataClient")
    # def test_alpaca_fetch_bars(self, mock_client_cls):
    #     """Test Alpaca Adapter fetching and parsing logic."""
    #     # Setup Mock
    #     mock_instance = mock_client_cls.return_value
    #     mock_bars_response = MagicMock()
    #
    #     # Mock DataFrame
    #     import pandas as pd
    #
    #     data = {
    #         "timestamp": [datetime(2023, 1, 1)],
    #         "symbol": ["AAPL"],
    #         "close": [150.0],
    #     }
    #     df = pd.DataFrame(data)
    #     mock_bars_response.df = df
    #     mock_instance.get_stock_bars.return_value = mock_bars_response
    #
    #     # Execute
    #     adapter = AlpacaAdapter(api_key="test", secret_key="test")
    #     bars = adapter.fetch_bars("AAPL", datetime(2023, 1, 1))
    #
    #     # Verify
    #     assert len(bars) == 1
    #     assert bars[0]["symbol"] == "AAPL"
    #     assert bars[0]["close"] == 150.0

    @patch("app.adapters.tiingo.requests.get")
    def test_tiingo_fetch_news(self, mock_get):
        """Test Tiingo Adapter news fetching."""
        # Setup Mock
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"title": "Test News", "description": "Bullish event"}
        ]
        mock_get.return_value = mock_response

        # Execute
        adapter = TiingoAdapter(api_key="test")
        news = adapter.fetch_news("AAPL")

        # Verify
        assert len(news) == 1
        assert news[0]["title"] == "Test News"
