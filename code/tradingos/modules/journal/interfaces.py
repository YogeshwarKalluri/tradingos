"""Journal module interfaces - Trade logging and performance analytics."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class TradeRecord:
    """Complete trade record for journal."""
    trade_id: str
    ticker: str
    side: str  # long, short
    entry_price: float
    exit_price: float | None = None
    qty: int = 0
    entry_time: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    exit_time: str | None = None
    pnl: float = 0.0
    pnl_pct: float = 0.0
    commission: float = 0.0
    pattern: str | None = None
    setup_quality: float | None = None
    hold_time_minutes: int | None = None
    result: str = ""  # win, loss, breakeven
    reasoning: str = ""
    indicators: dict[str, float] = field(default_factory=dict)
    notes: str = ""


@dataclass
class JournalEngine:
    """Base class for trade journal."""

    async def record_trade(self, trade: TradeRecord) -> None:
        raise NotImplementedError

    async def get_trades(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        ticker: str | None = None,
    ) -> list[TradeRecord]:
        raise NotImplementedError

    async def get_performance_stats(self) -> dict[str, Any]:
        raise NotImplementedError

    async def get_daily_pnl(self, days: int = 30) -> list[dict[str, Any]]:
        raise NotImplementedError
