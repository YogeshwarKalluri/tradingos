"""Scanner module interfaces."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class StockCandidate:
    """Represents a stock candidate from scanner."""

    ticker: str
    timestamp: datetime
    price: float
    gap_pct: float
    rel_volume: float
    float_shares: int
    source: str
    priority_score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.priority_score == 0.0:
            self.priority_score = self._calculate_priority()

    def _calculate_priority(self) -> float:
        """Calculate priority score based on scanner metrics."""
        # Higher RVol, higher gap%, lower float = higher priority
        # Add small epsilon to avoid division by zero
        float_factor = 1.0 / max(self.float_shares, 1_000_000)
        return self.rel_volume * self.gap_pct * float_factor


class ScannerSource:
    """Base class for scanner input sources."""

    async def start(self) -> None:
        """Start the source."""
        raise NotImplementedError

    async def stop(self) -> None:
        """Stop the source."""
        raise NotImplementedError

    async def get_candidates(self) -> list[StockCandidate]:
        """Get new candidates from source."""
        raise NotImplementedError
