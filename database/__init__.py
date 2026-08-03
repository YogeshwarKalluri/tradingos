"""
Database package for TradingOS
"""

from database.duckdb.connection import (
    DuckDBPool,
    get_duckdb_pool,
    set_duckdb_pool,
    close_duckdb_pool,
)

from database.sqlite.connection import (
    SQLitePool,
    get_sqlite_pool,
    set_sqlite_pool,
    close_sqlite_pool,
)

from database.qdrant.client import (
    QdrantManager,
    get_qdrant_manager,
    set_qdrant_manager,
    close_qdrant_manager,
)

__all__ = [
    # DuckDB
    "DuckDBPool",
    "get_duckdb_pool",
    "set_duckdb_pool",
    "close_duckdb_pool",
    # SQLite
    "SQLitePool",
    "get_sqlite_pool",
    "set_sqlite_pool",
    "close_sqlite_pool",
    # Qdrant
    "QdrantManager",
    "get_qdrant_manager",
    "set_qdrant_manager",
    "close_qdrant_manager",
]