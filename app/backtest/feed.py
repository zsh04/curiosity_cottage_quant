from abc import ABC, abstractmethod
import pandas as pd
import queue
from app.backtest.events import MarketEvent


class DataFeed(ABC):
    """
    Abstract Base Class for Data Feeds (Historical or Live).
    """

    @abstractmethod
    def get_latest_bar(self, symbol):
        pass

    @abstractmethod
    def get_current_price(self, symbol) -> float:
        pass

    @abstractmethod
    def update_bars(self, event_queue):
        pass


class HistoricalCSVDataFeed(DataFeed):
    """
    Reads data from CSV or DataFrame and simulates a live feed.
    """

    def __init__(self, data_dict: dict[str, pd.DataFrame]):
        """
        data_dict: { 'AAPL': pd.DataFrame(index=datetime, columns=['open','high','low','close','volume']) }
        """
        self.data = data_dict
        self.symbol_list = list(data_dict.keys())
        self.continue_backtest = True
        self.bar_index = 0
        self._symbol_generators = {s: self.data[s].iterrows() for s in self.symbol_list}
        self.latest_prices = {}

    def get_latest_bar(self, symbol):
        # In a real implementation this would return the last seen bar from a buffer
        pass

    def get_current_price(self, symbol) -> float:
        return self.latest_prices.get(symbol, 0.0)

    def update_bars(self, event_queue: queue.Queue):
        """
        Pushes the next bar for all symbols to the Queue.
        """
        for symbol in self.symbol_list:
            try:
                index, row = next(self._symbol_generators[symbol])
                event = MarketEvent(
                    timestamp=index,
                    symbol=symbol,
                    open=row["open"],
                    high=row["high"],
                    low=row["low"],
                    close=row["close"],
                    volume=row.get("volume", 0),
                )
                self.latest_prices[symbol] = row["close"]
                event_queue.put(event)
            except StopIteration:
                self.continue_backtest = False


class TimescaleDataFeed(HistoricalCSVDataFeed):
    """
    Loads data from TimescaleDB and behaves like a Historical Feed.
    """

    def __init__(self, symbols: list[str], start_date, end_date):
        from app.infra.database.client import TimescaleClient

        client = TimescaleClient()
        data_dict = {}

        print(f"Loading data from TimescaleDB for {symbols}...")
        for symbol in symbols:
            df = client.get_bars(symbol, start_date, end_date)
            if not df.empty:
                data_dict[symbol] = df
                print(f"Loaded {len(df)} bars for {symbol}")
            else:
                print(f"Warning: No data found for {symbol}")

        super().__init__(data_dict)
