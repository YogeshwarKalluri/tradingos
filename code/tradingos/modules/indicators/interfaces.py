"""Indicators Engine interfaces - stub for forward references."""

from dataclasses import dataclass
from typing import Any


@dataclass
class IndicatorSnapshot:
    """Technical indicator values at a point in time."""
    ticker: str
    timestamp: str
    vwap: float | None = None
    ema_9: float | None = None
    ema_20: float | None = None
    ema_50: float | None = None
    ema_200: float | None = None
    atr: float | None = None
    rvol: float | None = None
    gap_pct: float | None = None
    indicators: dict[str, float] | None = None


class IndicatorEngine:
    """Base class for indicator calculation."""

    async def calculate(self, bars: Any) -> IndicatorSnapshot:
        raise NotImplementedError
