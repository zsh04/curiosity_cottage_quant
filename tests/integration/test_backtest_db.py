import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
from datetime import datetime
from app.backtest.feed import TimescaleDataFeed


class TestTimescaleIntegration:
    @patch("app.infra.database.client.TimescaleClient.get_bars")
    def test_feed_loading(self, mock_get_bars):
        # 1. Setup Mock Data
        dates = pd.date_range(start="2023-01-01", periods=3)
        mock_df = pd.DataFrame(
            {
                "open": [100, 101, 102],
                "high": [105, 106, 107],
                "low": [95, 96, 97],
                "close": [102, 103, 104],
                "volume": [1000, 1000, 1000],
            },
            index=dates,
        )

        mock_get_bars.return_value = mock_df

        # 2. Initialize Feed
        start = datetime(2023, 1, 1)
        end = datetime(2023, 1, 5)
        feed = TimescaleDataFeed(symbols=["AAPL"], start_date=start, end_date=end)

        # 3. Verify Mock Call
        mock_get_bars.assert_called_with("AAPL", start, end)

        # 4. Verify Data Consumption (Engine Loop simulation)
        event_queue = MagicMock()

        # Pull 3 bars
        feed.update_bars(event_queue)  # Bar 1
        feed.update_bars(event_queue)  # Bar 2
        feed.update_bars(event_queue)  # Bar 3

        assert feed.continue_backtest is True

        feed.update_bars(event_queue)  # End of Data

        assert feed.continue_backtest is False
        assert event_queue.put.call_count == 3
