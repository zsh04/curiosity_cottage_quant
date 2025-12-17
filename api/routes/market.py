from litestar import Controller, get
from app.services.market import MarketService
from typing import List, Dict, Any


class MarketController(Controller):
    path = "/market"
    tags = ["market"]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.market_service = MarketService()

    @get("/history/{symbol:str}")
    async def get_history(self, symbol: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Fetch historical bars for a symbol.
        Used for instant chart population on frontend load.
        """
        # Call new service method
        try:
            return self.market_service.get_chart_history(symbol, limit=limit)
        except Exception as e:
            return []
