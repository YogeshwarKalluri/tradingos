"""
DuckDB Connection Pool and Schema for TradingOS
Analytics & Time-Series Database
"""

from __future__ import annotations
import asyncio
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Generator

import duckdb
import pandas as pd
import polars as pl

from core.config import get_settings
from core.types import Timeframe, Side, Action, OrderStatus, PatternType, EventType


@dataclass(slots=True)
class DuckDBConfig:
    """DuckDB connection configuration."""
    path: str
    memory_limit: str = "4GB"
    threads: int = 8
    max_connections: int = 10


class DuckDBPool:
    """
    Thread-safe DuckDB connection pool.
    
    DuckDB is not thread-safe for concurrent writes, so we use
    a connection pool with serialized access for writes.
    """
    
    def __init__(self, config: DuckDBConfig):
        self._config = config
        self._local = threading.local()
        self._write_lock = threading.Lock()
        self._initialized = False
        # Create initial connection to validate path
        self._init_connection()
    
    def _init_connection(self) -> None:
        """Initialize and validate the database file."""
        conn = duckdb.connect(self._config.path)
        conn.execute(f"PRAGMA memory_limit='{self._config.memory_limit}'")
        conn.execute(f"PRAGMA threads={self._config.threads}")
        conn.close()
    
    def _get_connection(self) -> duckdb.DuckDBPyConnection:
        """Get thread-local connection."""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            conn = duckdb.connect(self._config.path)
            conn.execute(f"PRAGMA memory_limit='{self._config.memory_limit}'")
            conn.execute(f"PRAGMA threads={self._config.threads}")
            self._local.conn = conn
        return self._local.conn
    
    def close_all_connections(self) -> None:
        """Close all thread-local connections."""
        if hasattr(self._local, 'conn') and self._local.conn is not None:
            self._local.conn.close()
            self._local.conn = None
    
    @contextmanager
    def read(self) -> Generator[duckdb.DuckDBPyConnection, None, None]:
        """Context manager for read operations (concurrent)."""
        conn = self._get_connection()
        yield conn
    
    @contextmanager
    def write(self) -> Generator[duckdb.DuckDBPyConnection, None, None]:
        """Context manager for write operations (serialized)."""
        with self._write_lock:
            conn = self._get_connection()
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
    
    def execute(self, query: str, params: Optional[List[Any]] = None) -> Any:
        """Execute a write query."""
        with self.write() as conn:
            if params:
                return conn.execute(query, params)
            return conn.execute(query)
    
    def query(self, query: str, params: Optional[List[Any]] = None) -> pd.DataFrame:
        """Execute a read query and return pandas DataFrame."""
        with self.read() as conn:
            if params:
                return conn.execute(query, params).fetchdf()
            return conn.execute(query).fetchdf()
    
    def query_pl(self, query: str, params: Optional[List[Any]] = None) -> pl.DataFrame:
        """Execute a read query and return Polars DataFrame."""
        with self.read() as conn:
            if params:
                return conn.execute(query, params).pl()
            return conn.execute(query).pl()
    
    def fetchone(self, query: str, params: Optional[List[Any]] = None) -> Optional[tuple]:
        """Fetch single row."""
        with self.read() as conn:
            if params:
                return conn.execute(query, params).fetchone()
            return conn.execute(query).fetchone()
    
    def fetchall(self, query: str, params: Optional[List[Any]] = None) -> List[tuple]:
        """Fetch all rows."""
        with self.read() as conn:
            if params:
                return conn.execute(query, params).fetchall()
            return conn.execute(query).fetchall()
    
    def initialize_schema(self) -> None:
        """Create all tables and indexes."""
        if self._initialized:
            return
        
        with self.write() as conn:
            # Market data - OHLCV bars
            conn.execute("""
                CREATE TABLE IF NOT EXISTS bars (
                    symbol VARCHAR NOT NULL,
                    timeframe VARCHAR NOT NULL,
                    timestamp BIGINT NOT NULL,  -- nanoseconds since epoch
                    open DOUBLE NOT NULL,
                    high DOUBLE NOT NULL,
                    low DOUBLE NOT NULL,
                    close DOUBLE NOT NULL,
                    volume BIGINT NOT NULL,
                    vwap DOUBLE,
                    trades BIGINT,
                    PRIMARY KEY (symbol, timeframe, timestamp)
                )
            """)
            
            # Pre-computed indicators
            conn.execute("""
                CREATE TABLE IF NOT EXISTS indicators (
                    symbol VARCHAR NOT NULL,
                    timeframe VARCHAR NOT NULL,
                    timestamp BIGINT NOT NULL,
                    indicator_name VARCHAR NOT NULL,
                    value DOUBLE NOT NULL,
                    PRIMARY KEY (symbol, timeframe, timestamp, indicator_name)
                )
            """)
            
            # Trade journal
            conn.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    trade_id UUID PRIMARY KEY,
                    symbol VARCHAR NOT NULL,
                    entry_time BIGINT NOT NULL,
                    exit_time BIGINT,
                    side VARCHAR NOT NULL,
                    entry_price DOUBLE NOT NULL,
                    exit_price DOUBLE,
                    quantity DOUBLE NOT NULL,
                    pnl DOUBLE,
                    commission DOUBLE,
                    setup_type VARCHAR,
                    pattern_confidence DOUBLE,
                    reasoning TEXT,
                    risk_metrics JSON,
                    tags VARCHAR[],
                    created_at BIGINT DEFAULT (EXTRACT(EPOCH FROM NOW()) * 1000000000)
                )
            """)
            
            # Positions (for current state)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS positions (
                    position_id UUID PRIMARY KEY,
                    symbol VARCHAR NOT NULL,
                    side VARCHAR NOT NULL,
                    quantity DOUBLE NOT NULL,
                    entry_price DOUBLE NOT NULL,
                    current_price DOUBLE,
                    unrealized_pnl DOUBLE,
                    realized_pnl DOUBLE,
                    stop_loss DOUBLE,
                    take_profit DOUBLE,
                    entry_time BIGINT NOT NULL,
                    updated_at BIGINT DEFAULT (EXTRACT(EPOCH FROM NOW()) * 1000000000)
                )
            """)
            
            # Orders
            conn.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    order_id UUID PRIMARY KEY,
                    symbol VARCHAR NOT NULL,
                    side VARCHAR NOT NULL,
                    order_type VARCHAR NOT NULL,
                    quantity DOUBLE NOT NULL,
                    price DOUBLE,
                    status VARCHAR NOT NULL,
                    filled_qty DOUBLE DEFAULT 0,
                    avg_fill_price DOUBLE,
                    commission DOUBLE DEFAULT 0,
                    submitted_at BIGINT NOT NULL,
                    filled_at BIGINT,
                    cancelled_at BIGINT,
                    parent_order_id UUID,
                    metadata JSON
                )
            """)
            
            # Scanner detections
            conn.execute("""
                CREATE TABLE IF NOT EXISTS scanner_detections (
                    detection_id UUID PRIMARY KEY,
                    symbol VARCHAR NOT NULL,
                    timestamp BIGINT NOT NULL,
                    price DOUBLE NOT NULL,
                    volume BIGINT NOT NULL,
                    change_pct DOUBLE,
                    relative_volume DOUBLE,
                    scanner_id VARCHAR NOT NULL,
                    filters_passed VARCHAR[],
                    metadata JSON
                )
            """)
            
            # Pattern detections
            conn.execute("""
                CREATE TABLE IF NOT EXISTS pattern_detections (
                    pattern_id UUID PRIMARY KEY,
                    symbol VARCHAR NOT NULL,
                    pattern_type VARCHAR NOT NULL,
                    confidence DOUBLE NOT NULL,
                    timeframe VARCHAR NOT NULL,
                    timestamp BIGINT NOT NULL,
                    bounding_box_x INT,
                    bounding_box_y INT,
                    bounding_box_w INT,
                    bounding_box_h INT,
                    metadata JSON
                )
            """)
            
            # Create indexes for common queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_bars_symbol_time 
                ON bars(symbol, timestamp DESC)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_bars_timeframe 
                ON bars(timeframe)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_trades_symbol_time 
                ON trades(symbol, entry_time DESC)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_trades_pnl 
                ON trades(pnl DESC)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_positions_symbol 
                ON positions(symbol)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_orders_status 
                ON orders(status)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_orders_symbol_time 
                ON orders(symbol, submitted_at DESC)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_scanner_time 
                ON scanner_detections(timestamp DESC)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_patterns_symbol_time 
                ON pattern_detections(symbol, timestamp DESC)
            """)
            
            self._initialized = True


# Global pool instance
_duckdb_pool: Optional[DuckDBPool] = None


def get_duckdb_pool() -> DuckDBPool:
    """Get or create the global DuckDB pool."""
    global _duckdb_pool
    if _duckdb_pool is None:
        settings = get_settings()
        config = DuckDBConfig(
            path=settings.databases.duckdb_path,
            memory_limit=settings.databases.duckdb_memory_limit,
            threads=settings.databases.duckdb_threads,
        )
        _duckdb_pool = DuckDBPool(config)
        _duckdb_pool.initialize_schema()
    return _duckdb_pool


def set_duckdb_pool(pool: DuckDBPool) -> None:
    """Set the global DuckDB pool (for testing)."""
    global _duckdb_pool
    _duckdb_pool = pool


def close_duckdb_pool() -> None:
    """Close the global DuckDB pool."""
    global _duckdb_pool
    if _duckdb_pool:
        # DuckDB connections are closed automatically on garbage collection
        _duckdb_pool = None