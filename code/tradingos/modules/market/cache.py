"""In-memory hot cache for market data with TTL."""

import asyncio
from datetime import datetime, timedelta
from typing import Any

from tradingos.core.logging import get_logger

logger = get_logger(__name__)


class MarketCache:
    """Thread-safe in-memory cache with TTL for hot market data."""

    def __init__(self, default_ttl: int = 1):
        self._cache: dict[str, tuple[Any, datetime]] = {}
        self._default_ttl = timedelta(seconds=default_ttl)
        self._lock = asyncio.Lock()

    def _make_key(self, prefix: str, *parts: str) -> str:
        """Create cache key."""
        return f"{prefix}:{':'.join(parts)}"

    async def set(
        self,
        prefix: str,
        value: Any,
        *parts: str,
        ttl: timedelta | None = None,
    ) -> None:
        """Set cache entry with TTL."""
        key = self._make_key(prefix, *parts)
        expiry = datetime.now() + (ttl or self._default_ttl)
        async with self._lock:
            self._cache[key] = (value, expiry)

    async def get(self, prefix: str, *parts: str) -> Any | None:
        """Get cache entry if not expired."""
        key = self._make_key(prefix, *parts)
        async with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            value, expiry = entry
            if datetime.now() > expiry:
                del self._cache[key]
                return None
            return value

    async def delete(self, prefix: str, *parts: str) -> bool:
        """Delete cache entry."""
        key = self._make_key(prefix, *parts)
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    async def clear_expired(self) -> int:
        """Remove all expired entries."""
        now = datetime.now()
        async with self._lock:
            expired = [k for k, (_, exp) in self._cache.items() if now > exp]
            for k in expired:
                del self._cache[k]
            return len(expired)

    async def clear(self) -> None:
        """Clear all cache entries."""
        async with self._lock:
            self._cache.clear()

    # Convenience methods for common market data
    async def set_latest_bar(self, ticker: str, bar: dict) -> None:
        await self.set("bar", bar, ticker)

    async def get_latest_bar(self, ticker: str) -> dict | None:
        return await self.get("bar", ticker)

    async def set_l2_snapshot(self, ticker: str, snapshot: dict) -> None:
        await self.set("l2", snapshot, ticker)

    async def get_l2_snapshot(self, ticker: str) -> dict | None:
        return await self.get("l2", ticker)

    async def set_fundamentals(self, ticker: str, data: dict, ttl: timedelta | None = None) -> None:
        await self.set("fundamentals", data, ticker, ttl=ttl or timedelta(hours=24))

    async def get_fundamentals(self, ticker: str) -> dict | None:
        return await self.get("fundamentals", ticker)

    async def get_stats(self) -> dict:
        """Get cache statistics."""
        async with self._lock:
            now = datetime.now()
            total = len(self._cache)
            expired = sum(1 for _, exp in self._cache.values() if now > exp)
            return {
                "total_entries": total,
                "expired_entries": expired,
                "active_entries": total - expired,
            }
