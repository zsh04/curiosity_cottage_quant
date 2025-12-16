from typing import List


class MarketAdapter:
    @staticmethod
    def get_current_price(symbol: str) -> float:
        # TODO: Implement actual API call (e.g. Tiingo/Alpaca)
        return 450.0

    @staticmethod
    def get_historic_returns(symbol: str) -> List[float]:
        # TODO: Implement actual API call
        # Mocking last 10 days returns
        return [0.001, -0.002, 0.005, 0.001, -0.001, 0.003, 0.004, -0.002, 0.001, 0.0]
