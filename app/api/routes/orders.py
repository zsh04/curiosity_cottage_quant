from litestar import Controller, Router, get, post
from dataclasses import dataclass
from typing import List, Optional, Any
from app.execution.alpaca_client import AlpacaClient
from app.core.config import settings


@dataclass
class OrderRequest:
    symbol: str
    qty: float
    side: str  # "buy" or "sell"
    type: str = "market"  # "market" or "limit"
    limit_price: Optional[float] = None


@dataclass
class OrderResponse:
    success: bool
    order_id: Optional[str] = None
    message: str = ""


@dataclass
class Position:
    symbol: str
    qty: float
    avg_entry_price: float
    current_price: float
    unrealized_pl: float
    unrealized_plpc: float
    market_value: float


class OrdersController(Controller):
    path = "/orders"
    tags = ["orders"]

    def __init__(self, owner: "Router", **kwargs: Any) -> None:
        super().__init__(owner, **kwargs)
        self.alpaca = AlpacaClient()

    @post("/submit")
    async def submit_order(self, data: OrderRequest) -> OrderResponse:
        """Submit a new order to Alpaca."""
        try:
            order = self.alpaca.submit_order(
                symbol=data.symbol,
                qty=data.qty,
                side=data.side,
                type=data.type,
                limit_price=data.limit_price,
            )
            return OrderResponse(
                success=True, order_id=order.id, message="Order submitted successfully"
            )
        except Exception as e:
            return OrderResponse(success=False, message=str(e))

    @get("/positions")
    async def get_positions(self) -> List[Position]:
        """Get current open positions."""
        try:
            alpaca_positions = self.alpaca.list_positions()
            return [
                Position(
                    symbol=p.symbol,
                    qty=float(p.qty),
                    avg_entry_price=float(p.avg_entry_price),
                    current_price=float(p.current_price),
                    unrealized_pl=float(p.unrealized_pl),
                    unrealized_plpc=float(p.unrealized_plpc),
                    market_value=float(p.market_value),
                )
                for p in alpaca_positions
            ]
        except Exception as e:
            print(f"Error fetching positions: {e}")
            return []
