"""Execution Engine interfaces."""

from dataclasses import dataclass


@dataclass
class Order:
    """Order representation.

    ``order_id`` and ``status`` are assigned by the execution engine when the
    order is placed; they carry defaults so that an Order is inspectable before
    submission rather than raising AttributeError.
    """

    ticker: str
    side: str
    qty: int
    order_type: str
    limit_price: float | None = None
    stop_price: float | None = None
    order_id: str | None = None
    status: str = "created"
    submitted_at: str | None = None
    filled_at: str | None = None
    fill_price: float | None = None


@dataclass
class Fill:
    """Fill representation."""

    order_id: str
    ticker: str
    side: str
    qty: int
    price: float
    timestamp: str
    fill_id: str | None = None
    commission: float = 0.0


class ExecutionEngine:
    """Base class for order execution."""

    async def place_order(self, order: Order) -> str:
        raise NotImplementedError

    async def cancel_order(self, order_id: str) -> bool:
        raise NotImplementedError
