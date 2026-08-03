"""
DuckDB package for TradingOS
"""

from database.duckdb.connection import (
    DuckDBPool,
    get_duckdb_pool,
    set_duckdb_pool,
    close_duckdb_pool,
)

__all__ = [
    "DuckDBPool",
    "get_duckdb_pool",
    "set_duckdb_pool",
    "close_duckdb_pool",
]