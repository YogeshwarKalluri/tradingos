"""Reasoning Engine interfaces - stub for forward references."""

from dataclasses import dataclass
from typing import Any


@dataclass
class TradeThesis:
    """Reasoning output for a trade decision."""
    thesis: str
    confidence: float
    evidence: list[str]
    risk_factors: list[str]
    metadata: dict[str, Any]


class ReasoningEngine:
    """Base class for reasoning."""

    async def evaluate(self, evidence: dict[str, Any]) -> TradeThesis:
        raise NotImplementedError
