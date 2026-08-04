"""DuckDB storage for market data."""

import threading
from datetime import datetime
from pathlib import Path

import duckdb

from tradingos.core.logging import get_logger
from tradingos.modules.market.interfaces import OHLCV

logger = get_logger(__name__)


class DuckDBStore:
    """Thread-safe DuckDB store for market data."""

    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._init_schema()

    def _get_conn(self) -> duckdb.DuckDBPyConnection:
        """Get thread-local connection."""
        if not hasattr(self._local, "conn"):
            self._local.conn = duckdb.connect(str(self.db_path))
            self._local.conn.execute("PRAGMA threads=4")
        return self._local.conn

    def _init_schema(self) -> None:
        """Initialize database schema with partitioned tables."""
        conn = self._get_conn()

        # 1-minute OHLCV (primary trading resolution)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ohlcv_1m (
                ticker VARCHAR NOT NULL,
                ts TIMESTAMP NOT NULL,
                open DOUBLE NOT NULL,
                high DOUBLE NOT NULL,
                low DOUBLE NOT NULL,
                close DOUBLE NOT NULL,
                volume BIGINT NOT NULL,
                vwap DOUBLE,
                trades INTEGER,
                interpolated BOOLEAN DEFAULT FALSE,
                source VARCHAR DEFAULT 'polygon',
                PRIMARY KEY (ticker, ts)
            )
        """)

        # 5-minute OHLCV (derived from 1m)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ohlcv_5m (
                ticker VARCHAR NOT NULL,
                ts TIMESTAMP NOT NULL,
                open DOUBLE NOT NULL,
                high DOUBLE NOT NULL,
                low DOUBLE NOT NULL,
                close DOUBLE NOT NULL,
                volume BIGINT NOT NULL,
                vwap DOUBLE,
                PRIMARY KEY (ticker, ts)
            )
        """)

        # 15-minute OHLCV
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ohlcv_15m (
                ticker VARCHAR NOT NULL,
                ts TIMESTAMP NOT NULL,
                open DOUBLE NOT NULL,
                high DOUBLE NOT NULL,
                low DOUBLE NOT NULL,
                close DOUBLE NOT NULL,
                volume BIGINT NOT NULL,
                vwap DOUBLE,
                PRIMARY KEY (ticker, ts)
            )
        """)

        # Daily OHLCV
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ohlcv_daily (
                ticker VARCHAR NOT NULL,
                date DATE NOT NULL,
                open DOUBLE NOT NULL,
                high DOUBLE NOT NULL,
                low DOUBLE NOT NULL,
                close DOUBLE NOT NULL,
                volume BIGINT NOT NULL,
                vwap DOUBLE,
                adj_close DOUBLE,
                PRIMARY KEY (ticker, date)
            )
        """)

        # Level 2 snapshots (on-demand)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS level2_snapshots (
                snapshot_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                ticker VARCHAR NOT NULL,
                ts TIMESTAMP NOT NULL,
                bids JSON NOT NULL,
                asks JSON NOT NULL,
                spread DOUBLE,
                bid_volume BIGINT,
                ask_volume BIGINT
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_level2_ticker_ts ON level2_snapshots(ticker, ts)"
        )

        # News / sentiment
        conn.execute("""
            CREATE TABLE IF NOT EXISTS news (
                news_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                ticker VARCHAR,
                ts TIMESTAMP NOT NULL,
                headline VARCHAR NOT NULL,
                summary TEXT,
                source VARCHAR NOT NULL,
                sentiment_score DOUBLE,
                relevance_score DOUBLE,
                url VARCHAR
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_news_ticker_ts ON news(ticker, ts)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_news_ts ON news(ts)")

        # Fundamentals / static data
        conn.execute("""
            CREATE TABLE IF NOT EXISTS fundamentals (
                ticker VARCHAR PRIMARY KEY,
                company_name VARCHAR,
                sector VARCHAR,
                industry VARCHAR,
                market_cap BIGINT,
                shares_outstanding BIGINT,
                float_shares BIGINT,
                short_interest DOUBLE,
                short_ratio DOUBLE,
                avg_volume_30d BIGINT,
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)

        logger.info("duckdb_schema_initialized", path=str(self.db_path))

    def insert_bars_1m(self, bars: list[OHLCV]) -> int:
        """Bulk insert 1-minute bars with upsert."""
        if not bars:
            return 0

        conn = self._get_conn()
        data = [
            (
                b.ticker, b.ts, b.open, b.high, b.low, b.close,
                b.volume, b.vwap, b.trades, b.interpolated, b.source
            )
            for b in bars
        ]

        conn.executemany(
            """
            INSERT INTO ohlcv_1m (ticker, ts, open, high, low, close, volume,
                vwap, trades, interpolated, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (ticker, ts) DO UPDATE SET
                open=excluded.open, high=excluded.high, low=excluded.low,
                close=excluded.close, volume=excluded.volume,
                vwap=excluded.vwap, trades=excluded.trades,
                interpolated=excluded.interpolated, source=excluded.source
            """,
            data,
        )

        return len(bars)

    def get_bars_1m(self, ticker: str, start: datetime, end: datetime) -> list[dict]:
        """Get 1-minute bars for time range."""
        conn = self._get_conn()
        return conn.execute("""
            SELECT ticker, ts, open, high, low, close, volume, vwap, trades, interpolated, source
            FROM ohlcv_1m
            WHERE ticker = ? AND ts >= ? AND ts <= ?
            ORDER BY ts
        """, (ticker, start, end)).fetchall()

    def get_latest_bar_1m(self, ticker: str) -> dict | None:
        """Get most recent 1-minute bar."""
        conn = self._get_conn()
        row = conn.execute("""
            SELECT ticker, ts, open, high, low, close, volume, vwap, trades, interpolated, source
            FROM ohlcv_1m
            WHERE ticker = ?
            ORDER BY ts DESC LIMIT 1
        """, (ticker,)).fetchone()
        return dict(row) if row else None

    def get_fundamentals(self, ticker: str) -> dict | None:
        """Get fundamental data for ticker."""
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM fundamentals WHERE ticker = ?", (ticker,)).fetchone()
        return dict(row) if row else None

    def upsert_fundamentals(self, data: dict) -> None:
        """Insert or update fundamental data."""
        conn = self._get_conn()
        conn.execute(
            """
            INSERT INTO fundamentals (ticker, company_name, sector, industry, market_cap,
                shares_outstanding, float_shares, short_interest, short_ratio,
                avg_volume_30d, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NOW())
            ON CONFLICT (ticker) DO UPDATE SET
                company_name=excluded.company_name, sector=excluded.sector,
                industry=excluded.industry, market_cap=excluded.market_cap,
                shares_outstanding=excluded.shares_outstanding,
                float_shares=excluded.float_shares,
                short_interest=excluded.short_interest, short_ratio=excluded.short_ratio,
                avg_volume_30d=excluded.avg_volume_30d, updated_at=NOW()
            """,
            (
                data.get("ticker"), data.get("company_name"), data.get("sector"),
                data.get("industry"), data.get("market_cap"),
                data.get("shares_outstanding"), data.get("float_shares"),
                data.get("short_interest"), data.get("short_ratio"),
                data.get("avg_volume_30d")
            ),
        )

    def close(self) -> None:
        """Close thread-local connection."""
        if hasattr(self._local, "conn"):
            self._local.conn.close()
            del self._local.conn
