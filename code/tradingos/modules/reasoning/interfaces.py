"""Reasoning Engine interfaces."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class TradeThesis:
    """Reasoning output for a trade decision."""

    ticker: str
    direction: str
    confidence: float
    entry_price: float
    stop_loss: float
    target_price: float
    position_size_pct: float
    pattern: str
    reasoning: str
    similar_trades_count: int
    historical_win_rate: float
    indicators_used: list[str] = field(default_factory=list)
    timestamp: datetime | None = None


class ReasoningEngine:
    """Base class for reasoning."""

    async def evaluate(self, evidence: dict[str, Any]) -> TradeThesis:
        raise NotImplementedError
