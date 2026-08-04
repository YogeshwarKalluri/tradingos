"""Scanner module - coordinates all scanner sources."""

from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timedelta

from tradingos.core.events import StockDetected, publish_event
from tradingos.core.logging import get_logger
from tradingos.modules.scanner.interfaces import ScannerSource

logger = get_logger(__name__)


@dataclass
class ScannerConfig:
    """Scanner module configuration."""
    deduplication_window_minutes: int = 5
    priority_weights: dict[str, float] | None = None


class Scanner:
    """Main scanner coordinator."""

    def __init__(self, config: ScannerConfig | None = None):
        self.config = config or ScannerConfig()
        self.sources: list[ScannerSource] = []
        self._running = False
        self._dedup_cache: OrderedDict[str, datetime] = OrderedDict()
        self._max_cache_size = 10000

    def add_source(self, source: ScannerSource) -> None:
        """Add a scanner source."""
        self.sources.append(source)
        logger.info("scanner_source_added", source=source.__class__.__name__)

    async def start(self) -> None:
        """Start all scanner sources."""
        self._running = True
        for source in self.sources:
            await source.start()
        logger.info("scanner_started", sources=len(self.sources))

    async def stop(self) -> None:
        """Stop all scanner sources."""
        self._running = False
        for source in self.sources:
            await source.stop()
        logger.info("scanner_stopped")

    async def _on_candidates(self, candidates: list) -> None:
        """Process incoming candidates from sources."""
        for candidate in candidates:
            if await self._should_process(candidate):
                await self._emit_candidate(candidate)

    async def _should_process(self, candidate) -> bool:
        """Check if candidate should be processed (deduplication)."""
        key = f"{candidate.ticker}:{candidate.timestamp.isoformat()}"
        now = datetime.now()

        # Check if we've seen this recently
        if key in self._dedup_cache:
            last_seen = self._dedup_cache[key]
            if now - last_seen < timedelta(minutes=self.config.deduplication_window_minutes):
                logger.debug("candidate_deduplicated", ticker=candidate.ticker)
                return False

        # Add to cache
        self._dedup_cache[key] = now

        # Limit cache size
        while len(self._dedup_cache) > self._max_cache_size:
            self._dedup_cache.popitem(last=False)

        return True

    async def _emit_candidate(self, candidate) -> None:
        """Emit StockDetected event."""
        event = StockDetected(candidate=candidate, source="scanner")
        await publish_event(event)
        logger.info(
            "candidate_emitted",
            ticker=candidate.ticker,
            price=candidate.price,
            priority=candidate.priority_score,
        )


async def create_scanner(config: ScannerConfig | None = None) -> Scanner:
    """Factory function to create scanner with all sources."""
    scanner = Scanner(config)

    # Import sources
    from tradingos.core.config import get_config
    from tradingos.modules.scanner.sources import FileWatchSource, IPCSource, WebhookSource

    app_config = get_config()

    # File watch source
    if app_config.scanner.sources.file_watch.enabled:
        file_source = FileWatchSource(
            path=app_config.scanner.sources.file_watch.path,
            pattern=app_config.scanner.sources.file_watch.pattern,
            callback=scanner._on_candidates,
        )
        scanner.add_source(file_source)

    # Webhook source
    if app_config.scanner.sources.webhook.enabled:
        webhook_host = (
            app_config.scanner.sources.webhook.host
            if hasattr(app_config.scanner.sources.webhook, "host")
            else "0.0.0.0"
        )
        webhook_source = WebhookSource(
            host=webhook_host,
            port=app_config.scanner.sources.webhook.port,
            path=app_config.scanner.sources.webhook.path,
            callback=scanner._on_candidates,
        )
        scanner.add_source(webhook_source)

    # IPC source
    if app_config.scanner.sources.ipc.enabled:
        ipc_source = IPCSource(
            pipe_path=app_config.scanner.sources.ipc.pipe_name,
            callback=scanner._on_candidates,
        )
        scanner.add_source(ipc_source)

    return scanner
