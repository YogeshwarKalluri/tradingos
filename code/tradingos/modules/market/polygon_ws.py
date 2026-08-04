"""Polygon.io WebSocket client for real-time market data."""

import asyncio
import contextlib
import json
import os
from collections.abc import Callable
from datetime import datetime
from typing import Any

import websockets
from websockets.client import WebSocketClientProtocol

from tradingos.core.logging import get_logger
from tradingos.modules.market.interfaces import OHLCV, DataSource

logger = get_logger(__name__)


class PolygonWebSocket(DataSource):
    """Polygon.io WebSocket client for real-time trades and quotes."""

    def __init__(
        self,
        api_key: str | None = None,
        on_bar: Callable[[OHLCV], Any] | None = None,
        on_trade: Callable[[dict], Any] | None = None,
        on_quote: Callable[[dict], Any] | None = None,
    ):
        self.api_key = api_key or os.getenv("POLYGON_API_KEY")
        self.on_bar = on_bar
        self.on_trade = on_trade
        self.on_quote = on_quote

        self._ws: WebSocketClientProtocol | None = None
        self._running = False
        self._task: asyncio.Task | None = None
        self._subscriptions: set[str] = set()
        self._reconnect_delay = 1
        self._max_reconnect_delay = 60
        self._pending_subscriptions: list[str] = []

        self._bar_accumulators: dict[str, dict] = {}

    async def start(self) -> None:
        """Start WebSocket connection."""
        if not self.api_key:
            logger.warning("polygon_api_key_missing")
            return

        self._running = True
        self._task = asyncio.create_task(self._run())
        logger.info("polygon_ws_started")

    async def stop(self) -> None:
        """Stop WebSocket connection."""
        self._running = False
        if self._ws:
            await self._ws.close()
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        logger.info("polygon_ws_stopped")

    async def _run(self) -> None:
        """Main WebSocket loop with reconnection."""
        while self._running:
            try:
                await self._connect()
                await self._listen()
            except Exception as e:
                logger.error("polygon_ws_error", error=str(e))
                if self._running:
                    await asyncio.sleep(self._reconnect_delay)
                    self._reconnect_delay = min(
                        self._reconnect_delay * 2,
                        self._max_reconnect_delay,
                    )
            else:
                self._reconnect_delay = 1

    async def _connect(self) -> None:
        """Establish WebSocket connection."""
        url = f"wss://socket.polygon.io/stocks?apiKey={self.api_key}"
        self._ws = await websockets.connect(url, ping_interval=20, ping_timeout=10)

        # Authenticate
        await self._ws.send(json.dumps({"action": "auth", "params": self.api_key}))
        response = await self._ws.recv()
        auth_data = json.loads(response)
        if auth_data[0].get("status") != "auth_success":
            raise RuntimeError(f"Auth failed: {auth_data}")

        # Resubscribe to pending tickers
        for ticker in self._pending_subscriptions:
            await self._subscribe_internal(ticker)
        self._pending_subscriptions.clear()

        logger.info("polygon_ws_connected")

    async def _listen(self) -> None:
        """Listen for messages."""
        async for message in self._ws:
            if not self._running:
                break
            try:
                data = json.loads(message)
                await self._handle_message(data)
            except Exception as e:
                logger.error("polygon_ws_parse_error", error=str(e))

    async def _handle_message(self, data: list[dict]) -> None:
        """Handle incoming message batch."""
        for msg in data:
            ev = msg.get("ev")
            if ev == "T":  # Trade
                await self._handle_trade(msg)
            elif ev == "Q":  # Quote
                await self._handle_quote(msg)
            elif ev == "AM":  # Minute aggregate (bar)
                await self._handle_bar(msg)
            elif ev == "status":
                logger.info("polygon_ws_status", status=msg)

    async def _handle_trade(self, msg: dict) -> None:
        """Handle trade message."""
        trade = {
            "ticker": msg.get("sym"),
            "price": msg.get("p"),
            "size": msg.get("s"),
            "timestamp": datetime.fromtimestamp(msg.get("t", 0) / 1e9),
            "conditions": msg.get("c", []),
        }
        if self.on_trade:
            await self.on_trade(trade)

        # Accumulate for bar building
        ticker = trade["ticker"]
        if ticker not in self._bar_accumulators:
            self._bar_accumulators[ticker] = {"trades": [], "start": None}
        self._bar_accumulators[ticker]["trades"].append(trade)

    async def _handle_quote(self, msg: dict) -> None:
        """Handle quote message."""
        quote = {
            "ticker": msg.get("sym"),
            "bid_price": msg.get("bp"),
            "bid_size": msg.get("bs"),
            "ask_price": msg.get("ap"),
            "ask_size": msg.get("as"),
            "timestamp": datetime.fromtimestamp(msg.get("t", 0) / 1e9),
        }
        if self.on_quote:
            await self.on_quote(quote)

    async def _handle_bar(self, msg: dict) -> None:
        """Handle minute aggregate (bar)."""
        bar = OHLCV(
            ticker=msg.get("sym"),
            ts=datetime.fromtimestamp(msg.get("s", 0) / 1000),
            open=msg.get("o"),
            high=msg.get("h"),
            low=msg.get("l"),
            close=msg.get("c"),
            volume=msg.get("v"),
            vwap=msg.get("vw"),
            trades=msg.get("n"),
            source="polygon",
        )
        if self.on_bar:
            await self.on_bar(bar)

    async def _subscribe_internal(self, ticker: str) -> None:
        """Subscribe to ticker (internal, assumes connected)."""
        if not self._ws:
            return
        await self._ws.send(json.dumps({
            "action": "subscribe",
            "params": f"T.{ticker},Q.{ticker},AM.{ticker}",
        }))
        self._subscriptions.add(ticker)

    async def subscribe(self, tickers: list[str]) -> None:
        """Subscribe to tickers."""
        for ticker in tickers:
            if ticker in self._subscriptions:
                continue
            if self._ws:
                await self._subscribe_internal(ticker)
            else:
                self._pending_subscriptions.append(ticker)

    async def unsubscribe(self, tickers: list[str]) -> None:
        """Unsubscribe from tickers."""
        if not self._ws:
            self._subscriptions.difference_update(tickers)
            self._pending_subscriptions = [
                t for t in self._pending_subscriptions if t not in tickers
            ]
            return

        for ticker in tickers:
            if ticker not in self._subscriptions:
                continue
            await self._ws.send(json.dumps({
                "action": "unsubscribe",
                "params": f"T.{ticker},Q.{ticker},AM.{ticker}",
            }))
            self._subscriptions.discard(ticker)

    async def get_bars(
        self,
        ticker: str,
        timeframe: str,
        start: datetime,
        end: datetime,
    ) -> list:
        """Not implemented for real-time source."""
        raise NotImplementedError("Use DuckDBStore for historical bars")

    def get_bar_accumulator(self, ticker: str) -> dict | None:
        """Get current bar accumulator for ticker."""
        return self._bar_accumulators.get(ticker)
