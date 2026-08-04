import asyncio
import contextlib
import json
import os
from collections.abc import Callable
from pathlib import Path

from aiohttp import web
from watchfiles import watch

from tradingos.core.logging import get_logger
from tradingos.modules.scanner.interfaces import ScannerSource, StockCandidate

logger = get_logger(__name__)


class FileWatchSource(ScannerSource):
    """Watch a directory for JSONL files with stock candidates."""

    def __init__(
        self,
        path: str,
        pattern: str = "*.jsonl",
        callback: Callable[[list[StockCandidate]], None] | None = None,
    ):
        self.path = Path(path)
        self.pattern = pattern
        self.callback = callback
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start watching the directory."""
        self.path.mkdir(parents=True, exist_ok=True)
        self._running = True
        self._task = asyncio.create_task(self._watch())
        logger.info("file_watch_started", path=str(self.path))

    async def stop(self) -> None:
        """Stop watching."""
        self._running = False
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        logger.info("file_watch_stopped")

    async def _watch(self) -> None:
        """Watch for file changes."""
        async for changes in watch(str(self.path), watch_filter=lambda p: p.match(self.pattern)):
            if not self._running:
                break
            for change_type, file_path in changes:
                if change_type in (1, 2):  # Added or modified
                    await self._process_file(Path(file_path))

    async def _process_file(self, file_path: Path) -> None:
        """Process a JSONL file."""
        try:
            candidates = []
            with open(file_path) as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        candidate = StockCandidate(**data)
                        candidates.append(candidate)
                    except Exception as e:
                        logger.warning(
                            "invalid_jsonl_line",
                            file=str(file_path),
                            line=line_num,
                            error=str(e),
                        )

            if candidates and self.callback:
                await self.callback(candidates)

        except Exception as e:
            logger.error("file_process_error", file=str(file_path), error=str(e))

    async def get_candidates(self) -> list[StockCandidate]:
        """Not used for push-based source."""
        return []


class WebhookSource(ScannerSource):
    """HTTP webhook endpoint for receiving candidates."""

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8081,
        path: str = "/scanner/candidates",
        callback: Callable[[list[StockCandidate]], None] | None = None,
    ):
        self.host = host
        self.port = port
        self.path = path
        self.callback = callback
        self._app = None
        self._server = None

    async def start(self) -> None:
        """Start the webhook server."""
        self._app = web.Application()
        self._app.router.add_post(self.path, self._handle_post)

        runner = web.AppRunner(self._app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()

        self._runner = runner
        logger.info("webhook_started", host=self.host, port=self.port, path=self.path)

    async def _handle_post(self, request) -> web.Response:
        """Handle incoming webhook POST."""
        try:
            data = await request.json()
            if isinstance(data, list):
                candidates = [StockCandidate(**item) for item in data]
            else:
                candidates = [StockCandidate(**data)]

            if self.callback:
                await self.callback(candidates)

            return web.json_response({"status": "ok", "received": len(candidates)})
        except Exception as e:
            logger.error("webhook_error", error=str(e))
            return web.json_response({"status": "error", "message": str(e)}, status=400)

    async def stop(self) -> None:
        """Stop the webhook server."""
        if self._runner:
            await self._runner.cleanup()
        logger.info("webhook_stopped")

    async def get_candidates(self) -> list[StockCandidate]:
        """Not used for push-based source."""
        return []


class IPCSource(ScannerSource):
    """Named pipe / Unix socket for local IPC."""

    def __init__(
        self,
        pipe_path: str,
        callback: Callable[[list[StockCandidate]], None] | None = None,
    ):
        self.pipe_path = pipe_path
        self.callback = callback
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start listening on the pipe."""
        # Remove existing pipe
        if os.path.exists(self.pipe_path):
            os.unlink(self.pipe_path)

        # Create FIFO
        os.mkfifo(self.pipe_path)
        self._running = True
        self._task = asyncio.create_task(self._listen())
        logger.info("ipc_started", pipe=self.pipe_path)

    async def stop(self) -> None:
        """Stop listening."""
        self._running = False
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        if os.path.exists(self.pipe_path):
            os.unlink(self.pipe_path)
        logger.info("ipc_stopped")

    async def _listen(self) -> None:
        """Listen for data on the pipe."""
        loop = asyncio.get_event_loop()
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)

        # Connect to FIFO
        async with open(self.pipe_path) as f:
            transport, _ = await loop.connect_read_pipe(lambda: protocol, f)

        try:
            while self._running:
                line = await reader.readline()
                if not line:
                    break
                line = line.decode().strip()
                if not line:
                    continue

                try:
                    data = json.loads(line)
                    if isinstance(data, list):
                        candidates = [StockCandidate(**item) for item in data]
                    else:
                        candidates = [StockCandidate(**data)]

                    if self.callback:
                        await self.callback(candidates)
                except Exception as e:
                    logger.warning("ipc_parse_error", line=line, error=str(e))
        finally:
            transport.close()

    async def get_candidates(self) -> list[StockCandidate]:
        """Not used for push-based source."""
        return []
