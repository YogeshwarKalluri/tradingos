"""Risk Engine interfaces - stub for forward references."""

from dataclasses import dataclass
from typing import Any


@dataclass
class RiskDecisionResult:
    """Result of risk evaluation."""
    approved: bool
    reason: str
    position_size: float
    stop_loss: float
    risk_reward: float
    metadata: dict[str, Any]


class RiskEngine:
    """Base class for risk evaluation."""

    async def evaluate(self, candidate: Any, market_data: Any) -> RiskDecisionResult:
        raise NotImplementedError
