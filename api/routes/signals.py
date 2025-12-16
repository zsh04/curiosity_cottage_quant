from litestar import Controller, get
from dataclasses import dataclass
from typing import List


@dataclass
class Signal:
    time: str
    symbol: str
    action: str
    confidence: str


class SignalsController(Controller):
    path = "/signals"
    tags = ["signals"]

    @get("/")
    async def get_recent_signals(self) -> List[Signal]:
        """Get recent trading signals."""
        return [
            Signal(time="10:42:05", symbol="BTC-PERP", action="LONG", confidence="92%"),
            Signal(
                time="10:41:12", symbol="ETH-PERP", action="SHORT", confidence="88%"
            ),
            Signal(
                time="10:38:55", symbol="SOL-PERP", action="CLOSE", confidence="N/A"
            ),
            Signal(
                time="10:35:10", symbol="AVAX-PERP", action="LONG", confidence="75%"
            ),
        ]
