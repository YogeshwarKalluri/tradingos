"""Memory Engine interfaces."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class HistoricalTrade:
    """Historical trade record for similarity search."""

    id: str
    ticker: str
    entry_price: float
    exit_price: float
    side: str
    pnl_pct: float
    result: str
    entry_time: str
    exit_time: str
    indicators: dict[str, Any] = field(default_factory=dict)
    pattern: str | None = None
    setup_quality: float | None = None
    hold_time_minutes: float | None = None
    chart_embedding: list[float] | None = None


class MemoryEngine:
    """Base class for historical trade search."""

    async def search(self, query: Any, top_k: int = 10) -> list[HistoricalTrade]:
        raise NotImplementedError
