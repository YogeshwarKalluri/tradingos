"""Market Data module - coordinates all market data sources."""

import asyncio
from datetime import datetime, timedelta

from tradingos.core.config import get_config
from tradingos.core.events import MarketDataReady, publish_event
from tradingos.core.logging import get_logger
from tradingos.modules.market.cache import MarketCache
from tradingos.modules.market.duckdb_store import DuckDBStore
from tradingos.modules.market.gap_detector import GapDetector
from tradingos.modules.market.interfaces import OHLCV, MarketData
from tradingos.modules.market.polygon_ws import PolygonWebSocket

logger = get_logger(__name__)


class MarketDataModule:
    """Main market data coordinator."""

    def __init__(self):
        self.config = get_config().market_data
        self.duckdb = DuckDBStore(self.config.duckdb_path)
        self.cache = MarketCache(default_ttl=self.config.cache_ttl_seconds)
        self.gap_detector = GapDetector(
            max_gap_minutes=self.config.gap_detection.max_gap_minutes,
            interpolate_small_gaps=self.config.gap_detection.interpolate_small_gaps,
        )
        self.polygon_ws = PolygonWebSocket(
            on_bar=self._on_bar,
            on_trade=self._on_trade,
            on_quote=self._on_quote,
        )
        self._running = False
        self._candidates_pending: dict[str, asyncio.Future] = {}

    async def start(self) -> None:
        """Start all market data sources."""
        self._running = True
        await self.polygon_ws.start()
        logger.info("market_data_started")

    async def stop(self) -> None:
        """Stop all market data sources."""
        self._running = False
        await self.polygon_ws.stop()
        self.duckdb.close()
        logger.info("market_data_stopped")

    async def _on_bar(self, bar: OHLCV) -> None:
        """Handle incoming minute bar from Polygon."""
        # Cache latest bar
        await self.cache.set_latest_bar(bar.ticker, {
            "ticker": bar.ticker,
            "ts": bar.ts,
            "open": bar.open,
            "high": bar.high,
            "low": bar.low,
            "close": bar.close,
            "volume": bar.volume,
            "vwap": bar.vwap,
            "trades": bar.trades,
        })

        # Store in DuckDB
        self.duckdb.insert_bars_1m([bar])

        # Check for gap
        await self._check_gaps(bar.ticker)

    async def _on_trade(self, trade: dict) -> None:
        """Handle incoming trade."""
        # Could be used for real-time chart updates
        pass

    async def _on_quote(self, quote: dict) -> None:
        """Handle incoming quote."""
        await self.cache.set_l2_snapshot(quote["ticker"], quote)

    async def _check_gaps(self, ticker: str) -> None:
        """Check for data gaps after new bar."""
        latest = self.duckdb.get_latest_bar_1m(ticker)
        if not latest:
            return

        # Get previous bar
        prev_ts = latest["ts"] - timedelta(minutes=1)
        bars = self.duckdb.get_bars_1m(ticker, prev_ts - timedelta(minutes=5), latest["ts"])

        if len(bars) >= 2:
            gaps = self.gap_detector.detect_gaps(bars, "1m", timedelta(minutes=1))
            if gaps:
                for gap in gaps:
                    logger.warning(
                        "data_gap_detected",
                        ticker=ticker,
                        gap_minutes=gap["gap_minutes"],
                    )
                    if (
                        gap["gap_minutes"] <= self.gap_detector.max_gap_minutes
                        and self.gap_detector.interpolate_small_gaps
                    ):
                        pass

    async def enrich_candidate(self, candidate) -> None:
        """Enrich a stock candidate with market data."""
        ticker = candidate.ticker

        # Get cached latest bar
        latest_bar = await self.cache.get_latest_bar(ticker)

        # Get 1m bars for chart (last 100 bars = ~100 min)
        end_ts = datetime.now()
        start_ts = end_ts - timedelta(minutes=120)
        bars_1m = self.duckdb.get_bars_1m(ticker, start_ts, end_ts)

        # Get fundamentals
        fundamentals = await self.cache.get_fundamentals(ticker)
        if not fundamentals:
            fundamentals = self.duckdb.get_fundamentals(ticker)
            if fundamentals:
                await self.cache.set_fundamentals(ticker, fundamentals)

        # Create market data object
        market_data = MarketData(
            ticker=ticker,
            bars_1m=bars_1m,
            bars_5m=[],  # Could derive or fetch
            bars_15m=[],
            bars_daily=[],
            latest_bar=latest_bar,
            fundamentals=fundamentals,
        )

        # Emit event
        event = MarketDataReady(candidate=candidate, market_data=market_data)
        await publish_event(event)
        logger.debug("candidate_enriched", ticker=ticker)

    def subscribe_tickers(self, tickers: list[str]) -> None:
        """Subscribe to real-time data for tickers."""
        asyncio.create_task(self.polygon_ws.subscribe(tickers))

    def unsubscribe_tickers(self, tickers: list[str]) -> None:
        """Unsubscribe from tickers."""
        asyncio.create_task(self.polygon_ws.unsubscribe(tickers))
