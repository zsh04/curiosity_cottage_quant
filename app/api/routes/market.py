from litestar import Controller, get
from app.services.market import MarketService
from typing import List
from dataclasses import dataclass


@dataclass
class Bar:
    time: str
    open: float
    high: float
    low: float
    close: float
    volume: float


class MarketController(Controller):
    path = "/market"
    tags = ["market"]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.market_service = MarketService()

    @get("/history/{symbol:str}")
    async def get_history(self, symbol: str, limit: int = 100) -> List[Bar]:
        """
        Fetch historical bars for a symbol.
        Used for instant chart population on frontend load.
        """
        # Service returns List[Dict], we convert to List[Bar] for strict schema
        # Error handling delegated to Global Exception Handler (don't swallow errors)
        data = self.market_service.get_chart_history(symbol, limit=limit)

        return [
            Bar(
                time=d["time"],
                open=d["open"],
                high=d["high"],
                low=d["low"],
                close=d["close"],
                volume=d["volume"],
            )
            for d in data
        ]
