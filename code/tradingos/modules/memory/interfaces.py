"""Memory Engine interfaces - stub for forward references."""

from dataclasses import dataclass
from typing import Any


@dataclass
class HistoricalTrade:
    """Historical trade record for similarity search."""
    ticker: str
    date: str
    pattern: str
    entry: float
    exit: float
    outcome: str
    metadata: dict[str, Any]


class MemoryEngine:
    """Base class for historical trade search."""

    async def search(self, query: Any, top_k: int = 10) -> list[HistoricalTrade]:
        raise NotImplementedError
