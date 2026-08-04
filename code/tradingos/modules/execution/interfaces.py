"""Execution Engine interfaces - stub for forward references."""

from dataclasses import dataclass


@dataclass
class Order:
    """Order representation."""
    ticker: str
    side: str
    qty: int
    order_type: str
    limit_price: float | None = None
    stop_price: float | None = None


@dataclass
class Fill:
    """Fill representation."""
    order_id: str
    ticker: str
    side: str
    qty: int
    price: float
    timestamp: str


class ExecutionEngine:
    """Base class for order execution."""

    async def place_order(self, order: Order) -> str:
        raise NotImplementedError

    async def cancel_order(self, order_id: str) -> bool:
        raise NotImplementedError
