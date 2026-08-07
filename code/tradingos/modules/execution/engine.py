"""Execution Engine - Paper trading with realistic fill simulation."""

import asyncio
import contextlib
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from tradingos.core.events import OrderFilled
from tradingos.core.logging import get_logger
from tradingos.modules.execution.interfaces import ExecutionEngine, Fill, Order

logger = get_logger(__name__)


@dataclass
class Position:
    """Position tracking."""
    ticker: str
    qty: int = 0
    avg_price: float = 0.0
    side: str = "flat"  # long, short, flat
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    entry_time: str | None = None


class PaperExecutionEngine(ExecutionEngine):
    """Paper trading execution engine with realistic simulation."""

    def __init__(
        self,
        config: dict[str, Any] | None = None,
        account_equity: float = 100_000.0,
        market_data=None,  # Reference to market data module for current prices
    ):
        self.config = config or {}
        self.account_equity = account_equity
        self.cash = account_equity
        self.market_data = market_data

        # Simulation parameters
        self.slippage_bps = self.config.get("slippage_bps", 5)  # 5 bps default
        self.latency_ms = self.config.get("latency_ms", 50)  # 50ms default
        self.commission_per_share = self.config.get("commission_per_share", 0.005)
        self.min_commission = self.config.get("min_commission", 1.0)

        # State
        self.orders: dict[str, Order] = {}
        self.fills: dict[str, Fill] = {}
        self.positions: dict[str, Position] = {}
        self.pending_orders: dict[str, asyncio.Task] = {}

        logger.info(
            "execution_engine_initialized",
            equity=account_equity,
            slippage_bps=self.slippage_bps,
            latency_ms=self.latency_ms,
        )

    async def place_order(self, order: Order) -> str:
        """Place an order and return order ID."""
        order_id = str(uuid.uuid4())
        order.order_id = order_id
        order.status = "pending"
        order.submitted_at = datetime.now(UTC).isoformat()

        self.orders[order_id] = order

        # Simulate latency
        await asyncio.sleep(self.latency_ms / 1000.0)

        # For market orders, fill immediately
        if order.order_type == "market":
            task = asyncio.create_task(self._execute_market_order(order))
            self.pending_orders[order_id] = task
        else:
            # Limit/stop orders would be managed by order book
            order.status = "open"
            logger.info("order_placed", order_id=order_id, type=order.order_type)

        return order_id

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending order."""
        if order_id in self.pending_orders:
            task = self.pending_orders.pop(order_id)
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

            if order_id in self.orders:
                self.orders[order_id].status = "cancelled"
            logger.info("order_cancelled", order_id=order_id)
            return True

        if order_id in self.orders:
            order = self.orders[order_id]
            if order.status in ("open", "pending"):
                order.status = "cancelled"
                logger.info("order_cancelled", order_id=order_id)
                return True

        return False

    async def _execute_market_order(self, order: Order) -> None:
        """Execute a market order with slippage simulation."""
        try:
            # Get current market price
            current_price = await self._get_current_price(order.ticker)
            if current_price is None:
                order.status = "rejected"
                logger.warning("order_rejected_no_price", order_id=order.order_id)
                return

            # Apply slippage
            if order.side == "buy":
                fill_price = current_price * (1 + self.slippage_bps / 10000)
            else:
                fill_price = current_price * (1 - self.slippage_bps / 10000)

            # Check buying power
            cost = fill_price * order.qty
            commission = max(order.qty * self.commission_per_share, self.min_commission)
            total_cost = cost + commission

            if order.side == "buy" and total_cost > self.cash:
                order.status = "rejected"
                logger.warning("order_rejected_insufficient_funds", order_id=order.order_id)
                return

            # Create fill
            fill = Fill(
                order_id=order.order_id,
                ticker=order.ticker,
                side=order.side,
                qty=order.qty,
                price=fill_price,
                timestamp=datetime.now(UTC).isoformat(),
            )
            fill.fill_id = str(uuid.uuid4())
            fill.commission = commission

            self.fills[fill.fill_id] = fill

            # Update order
            order.status = "filled"
            order.filled_at = fill.timestamp
            order.fill_price = fill_price

            # Update position
            await self._update_position(fill)

            # Update cash
            if order.side == "buy":
                self.cash -= total_cost
            else:
                self.cash += cost - commission

            logger.info(
                "order_filled",
                order_id=order.order_id,
                fill_id=fill.fill_id,
                price=fill_price,
                qty=order.qty,
            )

            # Publish fill event
            from tradingos.core.events import publish_event
            await publish_event(OrderFilled(
                order_id=order.order_id,
                fill_id=fill.fill_id,
                ticker=order.ticker,
                side=order.side,
                qty=order.qty,
                price=fill_price,
                commission=commission,
            ))

        except asyncio.CancelledError:
            order.status = "cancelled"
            raise
        except Exception as e:
            order.status = "rejected"
            logger.error("order_execution_error", order_id=order.order_id, error=str(e))

    async def _get_current_price(self, ticker: str) -> float | None:
        """Get current market price for ticker."""
        if self.market_data:
            try:
                # Try to get latest price from market data
                latest = self.market_data.duckdb.get_latest_bar_1m(ticker)
                if latest:
                    return latest["close"]
            except Exception:
                pass

        # Fallback: return a simulated price
        # In production, this would come from live market data
        return 100.0  # Placeholder

    async def _update_position(self, fill: Fill) -> None:
        """Update position after fill."""
        ticker = fill.ticker

        if ticker not in self.positions:
            self.positions[ticker] = Position(ticker=ticker)

        pos = self.positions[ticker]

        if fill.side == "buy":
            if pos.side == "short":
                # Covering short
                close_qty = min(fill.qty, abs(pos.qty))
                pnl = (pos.avg_price - fill.price) * close_qty
                pos.realized_pnl += pnl - fill.commission
                pos.qty += close_qty

                if pos.qty >= 0:
                    pos.side = "long" if pos.qty > 0 else "flat"
                    pos.avg_price = fill.price if pos.qty > 0 else 0.0
                    pos.entry_time = fill.timestamp if pos.qty > 0 else None
            else:
                # Adding to long or opening long
                if pos.qty == 0:
                    pos.entry_time = fill.timestamp
                total_cost = pos.qty * pos.avg_price + fill.qty * fill.price
                pos.qty += fill.qty
                pos.avg_price = total_cost / pos.qty if pos.qty > 0 else 0.0
                pos.side = "long"

        else:  # sell
            if pos.side == "long":
                # Selling long
                close_qty = min(fill.qty, pos.qty)
                pnl = (fill.price - pos.avg_price) * close_qty
                pos.realized_pnl += pnl - fill.commission
                pos.qty -= close_qty

                if pos.qty <= 0:
                    pos.side = "short" if pos.qty < 0 else "flat"
                    pos.avg_price = fill.price if pos.qty < 0 else 0.0
                    pos.entry_time = fill.timestamp if pos.qty < 0 else None
            else:
                # Adding to short or opening short
                if pos.qty == 0:
                    pos.entry_time = fill.timestamp
                total_cost = pos.qty * pos.avg_price - fill.qty * fill.price
                pos.qty -= fill.qty
                pos.avg_price = abs(total_cost / pos.qty) if pos.qty != 0 else 0.0
                pos.side = "short"

        # Update unrealized P&L
        current_price = await self._get_current_price(ticker)
        if current_price and pos.qty != 0:
            if pos.side == "long":
                pos.unrealized_pnl = (current_price - pos.avg_price) * pos.qty
            else:
                pos.unrealized_pnl = (pos.avg_price - current_price) * abs(pos.qty)

    def get_position(self, ticker: str) -> Position | None:
        """Get position for ticker."""
        return self.positions.get(ticker)

    def get_all_positions(self) -> dict[str, Position]:
        """Get all positions."""
        return self.positions.copy()

    def get_portfolio_value(self) -> dict[str, float]:
        """Get portfolio summary."""
        total_unrealized = sum(p.unrealized_pnl for p in self.positions.values())
        total_realized = sum(p.realized_pnl for p in self.positions.values())
        positions_value = sum(
            p.qty * (p.avg_price + p.unrealized_pnl / p.qty if p.qty != 0 else 0)
            for p in self.positions.values()
        )

        return {
            "cash": self.cash,
            "positions_value": positions_value,
            "total_equity": self.cash + positions_value,
            "unrealized_pnl": total_unrealized,
            "realized_pnl": total_realized,
            "total_pnl": total_unrealized + total_realized,
            "buying_power": self.cash,  # Simplified: cash only for now
        }

    def get_order(self, order_id: str) -> Order | None:
        """Get order by ID."""
        return self.orders.get(order_id)

    def get_fill(self, fill_id: str) -> Fill | None:
        """Get fill by ID."""
        return self.fills.get(fill_id)

    def get_open_orders(self) -> list[Order]:
        """Get all open/pending orders."""
        return [o for o in self.orders.values() if o.status in ("open", "pending")]

    async def close_position(self, ticker: str, qty: int | None = None) -> str | None:
        """Close a position (market order)."""
        pos = self.positions.get(ticker)
        if not pos or pos.qty == 0:
            return None

        close_qty = qty or abs(pos.qty)
        side = "sell" if pos.side == "long" else "buy"

        order = Order(
            ticker=ticker,
            side=side,
            qty=close_qty,
            order_type="market",
        )

        return await self.place_order(order)


def create_execution_engine(
    config: dict[str, Any] | None = None,
    account_equity: float = 100_000.0,
    market_data=None,
) -> ExecutionEngine:
    """Factory function to create execution engine."""
    return PaperExecutionEngine(config, account_equity, market_data)
