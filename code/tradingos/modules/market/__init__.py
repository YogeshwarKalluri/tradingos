"""Market Data module package."""

from tradingos.modules.market.alpaca_ws import AlpacaWebSocket
from tradingos.modules.market.cache import MarketCache
from tradingos.modules.market.duckdb_store import DuckDBStore
from tradingos.modules.market.gap_detector import GapDetector
from tradingos.modules.market.interfaces import OHLCV, DataSource, MarketData
from tradingos.modules.market.market import MarketDataModule
from tradingos.modules.market.polygon_ws import PolygonWebSocket

__all__ = [
    "DataSource",
    "MarketData",
    "OHLCV",
    "MarketDataModule",
    "DuckDBStore",
    "PolygonWebSocket",
    "AlpacaWebSocket",
    "MarketCache",
    "GapDetector",
]
