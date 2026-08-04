"""Chart Engine interfaces - stub for forward references."""

from dataclasses import dataclass
from typing import Any


@dataclass
class ChartTensor:
    """Normalized chart tensor ready for vision model."""
    ticker: str
    timeframes: dict[str, Any]  # {timeframe: tensor}
    metadata: dict[str, Any]


class ChartRenderer:
    """Base class for chart rendering."""

    async def render(self, ticker: str, bars: dict[str, list]) -> ChartTensor:
        raise NotImplementedError
