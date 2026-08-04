import asyncio
import contextlib
import json
import os
from collections.abc import Callable
from datetime import datetime
from typing import Any

import websockets

from tradingos.core.logging import get_logger
from tradingos.modules.market.interfaces import OHLCV, DataSource

logger = get_logger(__name__)


class AlpacaWebSocket(DataSource):
    """Alpaca WebSocket client for backup market data."""

    def __init__(
        self,
        api_key: str | None = None,
        secret_key: str | None = None,
        on_bar: Callable[[OHLCV], Any] | None = None,
        on_trade: Callable[[dict], Any] | None = None,
        on_quote: Callable[[dict], Any] | None = None,
    ):
        self.api_key = api_key or os.getenv("ALPACA_API_KEY")
        self.secret_key = secret_key or os.getenv("ALPACA_SECRET_KEY")
        self.on_bar = on_bar
        self.on_trade = on_trade
        self.on_quote = on_quote

        self._ws = None
        self._running = False
        self._task = None
        self._subscriptions = set()

    async def start(self) -> None:
        """Start WebSocket connection."""
        if not self.api_key or not self.secret_key:
            logger.warning("alpaca_credentials_missing")
            return

        self._running = True
        self._task = asyncio.create_task(self._run())
        logger.info("alpaca_ws_started")

    async def stop(self) -> None:
        self._running = False
        if self._ws:
            await self._ws.close()
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        logger.info("alpaca_ws_stopped")

    async def _run(self) -> None:
        while self._running:
            try:
                await self._connect()
                await self._listen()
            except Exception as e:
                logger.error("alpaca_ws_error", error=str(e))
                if self._running:
                    await asyncio.sleep(5)

    async def _connect(self) -> None:
        url = "wss://stream.data.alpaca.markets/v2/iex"
        self._ws = await websockets.connect(url, ping_interval=20, ping_timeout=10)

        # Authenticate
        await self._ws.send(json.dumps({
            "action": "auth",
            "key": self.api_key,
            "secret": self.secret_key,
        }))
        response = await self._ws.recv()
        auth_data = json.loads(response)
        stream_ok = auth_data.get("stream") == "authentication"
        auth_ok = auth_data.get("data", {}).get("status") == "authorized"
        if not stream_ok or not auth_ok:
            raise RuntimeError(f"Auth failed: {auth_data}")

        logger.info("alpaca_ws_connected")

    async def _listen(self) -> None:
        async for message in self._ws:
            if not self._running:
                break
            try:
                data = json.loads(message)
                await self._handle_message(data)
            except Exception as e:
                logger.error("alpaca_ws_parse_error", error=str(e))

    async def _handle_message(self, data: list[dict]) -> None:
        for msg in data:
            msg_type = msg.get("T")
            if msg_type == "t":  # Trade
                trade = {
                    "ticker": msg.get("S"),
                    "price": msg.get("p"),
                    "size": msg.get("s"),
                    "timestamp": datetime.fromisoformat(msg.get("t").replace("Z", "+00:00")),
                }
                # Note: Alpaca doesn't send minute bars directly via WS
                if self.on_trade:
                    await self.on_trade(trade)
            elif msg_type == "q":  # Quote
                quote = {
                    "ticker": msg.get("S"),
                    "bid_price": msg.get("bp"),
                    "bid_size": msg.get("bs"),
                    "ask_price": msg.get("ap"),
                    "ask_size": msg.get("as"),
                    "timestamp": datetime.fromisoformat(msg.get("t").replace("Z", "+00:00")),
                }
                if self.on_quote:
                    await self.on_quote(quote)

    async def subscribe(self, tickers: list[str]) -> None:
        if not self._ws:
            return
        await self._ws.send(json.dumps({
            "action": "subscribe",
            "trades": tickers,
            "quotes": tickers,
        }))

    async def unsubscribe(self, tickers: list[str]) -> None:
        if not self._ws:
            return
        await self._ws.send(json.dumps({
            "action": "unsubscribe",
            "trades": tickers,
            "quotes": tickers,
        }))

    async def get_bars(self, ticker: str, timeframe: str, start: datetime, end: datetime) -> list:
        raise NotImplementedError
