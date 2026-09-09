"""Risk Engine interfaces."""

from dataclasses import dataclass
from typing import Any


@dataclass
class RiskDecisionResult:
    """Result of risk evaluation.

    Rejections carry only ``approved``, ``reason`` and ``risk_score``; the
    sizing fields are populated on approval, so they default to None.
    """

    approved: bool
    reason: str
    risk_score: float
    adjusted_size_pct: float | None = None
    stop_loss: float | None = None
    target_price: float | None = None
    max_loss_usd: float | None = None


class RiskEngine:
    """Base class for risk evaluation."""

    async def evaluate(self, thesis: Any) -> RiskDecisionResult:
        raise NotImplementedError
