"""
SQLite Connection for TradingOS
Application metadata, settings, model configs
"""

from __future__ import annotations
import sqlite3
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

from core.config import get_settings


@dataclass(slots=True)
class SQLiteConfig:
    """SQLite connection configuration."""
    path: str
    max_connections: int = 5
    enable_wal: bool = True


class SQLitePool:
    """
    Thread-safe SQLite connection pool with WAL mode.
    """
    
    def __init__(self, config: SQLiteConfig):
        self._config = config
        self._local = threading.local()
        self._initialized = False
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local connection."""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            conn = sqlite3.connect(
                self._config.path,
                check_same_thread=False,
                isolation_level=None  # autocommit
            )
            conn.row_factory = sqlite3.Row
            
            if self._config.enable_wal:
                conn.execute("PRAGMA journal_mode=WAL")
            
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("PRAGMA busy_timeout=5000")
            conn.execute("PRAGMA synchronous=NORMAL")
            
            self._local.conn = conn
        
        return self._local.conn
    
    def close_all_connections(self) -> None:
        """Close all thread-local connections."""
        if hasattr(self._local, 'conn') and self._local.conn is not None:
            self._local.conn.close()
            self._local.conn = None
    
    @contextmanager
    def connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager for connection."""
        conn = self._get_connection()
        try:
            yield conn
        except Exception:
            conn.rollback()
            raise
    
    def execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """Execute a write query."""
        with self.connection() as conn:
            return conn.execute(query, params)
    
    def fetchone(self, query: str, params: tuple = ()) -> Optional[sqlite3.Row]:
        """Fetch single row."""
        with self.connection() as conn:
            return conn.execute(query, params).fetchone()
    
    def fetchall(self, query: str, params: tuple = ()) -> List[sqlite3.Row]:
        """Fetch all rows."""
        with self.connection() as conn:
            return conn.execute(query, params).fetchall()
    
    def initialize_schema(self) -> None:
        """Create all tables."""
        if self._initialized:
            return
        
        with self.connection() as conn:
            # Application settings
            conn.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at BIGINT NOT NULL DEFAULT (strftime('%s', 'now') * 1000000000)
                )
            """)
            
            # Model configurations
            conn.execute("""
                CREATE TABLE IF NOT EXISTS model_configs (
                    name TEXT PRIMARY KEY,
                    config TEXT NOT NULL,  -- JSON
                    version INTEGER NOT NULL DEFAULT 1,
                    updated_at BIGINT NOT NULL DEFAULT (strftime('%s', 'now') * 1000000000)
                )
            """)
            
            # Scanner configurations
            conn.execute("""
                CREATE TABLE IF NOT EXISTS scanner_configs (
                    id TEXT PRIMARY KEY,
                    config TEXT NOT NULL,  -- JSON
                    enabled INTEGER NOT NULL DEFAULT 1,
                    updated_at BIGINT NOT NULL DEFAULT (strftime('%s', 'now') * 1000000000)
                )
            """)
            
            # User preferences
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at BIGINT NOT NULL DEFAULT (strftime('%s', 'now') * 1000000000)
                )
            """)
            
            # API keys (encrypted in production)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS api_keys (
                    provider TEXT PRIMARY KEY,
                    key_encrypted TEXT NOT NULL,
                    secret_encrypted TEXT,
                    updated_at BIGINT NOT NULL DEFAULT (strftime('%s', 'now') * 1000000000)
                )
            """)
            
            # Create indexes
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_settings_updated 
                ON settings(updated_at)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_model_configs_updated 
                ON model_configs(updated_at)
            """)
            
            self._initialized = True


# Global pool instance
_sqlite_pool: Optional[SQLitePool] = None


def get_sqlite_pool() -> SQLitePool:
    """Get or create the global SQLite pool."""
    global _sqlite_pool
    if _sqlite_pool is None:
        settings = get_settings()
        config = SQLiteConfig(
            path=settings.databases.sqlite_path,
            enable_wal=True,
        )
        _sqlite_pool = SQLitePool(config)
        _sqlite_pool.initialize_schema()
    return _sqlite_pool


def set_sqlite_pool(pool: SQLitePool) -> None:
    """Set the global SQLite pool (for testing)."""
    global _sqlite_pool
    _sqlite_pool = pool


def close_sqlite_pool() -> None:
    """Close the global SQLite pool."""
    global _sqlite_pool
    if _sqlite_pool:
        _sqlite_pool = None