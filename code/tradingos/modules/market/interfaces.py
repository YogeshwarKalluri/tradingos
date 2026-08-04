"""Market Data module interfaces."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class OHLCV:
    """Single OHLCV bar."""
    ticker: str
    ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    vwap: float | None = None
    trades: int | None = None
    interpolated: bool = False
    source: str = "polygon"


@dataclass
class MarketData:
    """Aggregated market data for a candidate."""
    ticker: str
    bars_1m: list
    bars_5m: list
    bars_15m: list
    bars_daily: list
    latest_bar: Any | None = None
    level2: Any | None = None
    fundamentals: Any | None = None


class DataSource:
    """Base class for market data sources."""

    async def start(self) -> None:
        raise NotImplementedError

    async def stop(self) -> None:
        raise NotImplementedError

    async def get_bars(
        self,
        ticker: str,
        timeframe: str,
        start: datetime,
        end: datetime,
    ) -> list:
        raise NotImplementedError

    async def subscribe(self, tickers: list[str]) -> None:
        raise NotImplementedError

    async def unsubscribe(self, tickers: list[str]) -> None:
        raise NotImplementedError
