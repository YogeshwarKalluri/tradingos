"""
Tests for database/sqlite/connection.py
"""

import tempfile
from pathlib import Path

import pytest

from database.sqlite.connection import SQLitePool, close_sqlite_pool, get_sqlite_pool


class TestSQLitePool:
    """Test SQLite connection pool."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database path for testing."""
        import uuid
        db_path = Path(tempfile.gettempdir()) / f"test_{uuid.uuid4().hex}.db"
        yield db_path
        # Don't try to delete - temp files will be cleaned up by OS
        pass

    @pytest.fixture
    def pool(self, temp_db):
        """Create a SQLite pool for testing."""
        from database.sqlite.connection import SQLiteConfig
        config = SQLiteConfig(path=temp_db, enable_wal=True)
        pool = SQLitePool(config)
        yield pool

    def test_initialization(self, pool):
        """Test pool initialization."""
        assert pool is not None

    def test_write_and_read(self, pool):
        """Test write and read operations."""
        # Write
        pool.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, value TEXT)")
        pool.execute("INSERT INTO test (value) VALUES (?)", ("hello",))
        pool.execute("INSERT INTO test (value) VALUES (?)", ("world",))

        # Read
        rows = pool.fetchall("SELECT * FROM test ORDER BY id")
        assert len(rows) == 2
        assert rows[0]['value'] == 'hello'
        assert rows[1]['value'] == 'world'

    def test_fetchone(self, pool):
        """Test fetchone."""
        pool.execute("CREATE TABLE test2 (id INTEGER PRIMARY KEY, value TEXT)")
        pool.execute("INSERT INTO test2 (value) VALUES (?)", ("single",))

        row = pool.fetchone("SELECT * FROM test2 WHERE id = 1")
        assert row is not None
        assert row['value'] == 'single'

        # Non-existent
        row = pool.fetchone("SELECT * FROM test2 WHERE id = 999")
        assert row is None

    def test_context_manager(self, pool):
        """Test connection context manager."""
        with pool.connection() as conn:
            conn.execute("CREATE TABLE test3 (id INTEGER PRIMARY KEY, value TEXT)")
            conn.execute("INSERT INTO test3 (value) VALUES (?)", ("ctx",))

        with pool.connection() as conn:
            row = conn.execute("SELECT * FROM test3").fetchone()
            assert row is not None
            assert row['value'] == 'ctx'

    def test_rollback_on_error(self, pool):
        """Test that rollback works on error."""
        pool.execute("CREATE TABLE test4 (id INTEGER PRIMARY KEY, value TEXT)")
        pool.execute("INSERT INTO test4 (value) VALUES (?)", ("first",))

        # Try to insert duplicate key
        try:
            with pool.connection() as conn:
                conn.execute("INSERT INTO test4 (id, value) VALUES (1, 'duplicate')")
        except Exception:
            pass

        # Original row should still exist
        count = pool.fetchone("SELECT COUNT(*) as c FROM test4")['c']
        assert count == 1


class TestSQLiteGlobalPool:
    """Test global pool functions."""

    def test_get_pool(self):
        """Test getting global pool."""
        close_sqlite_pool()  # Clean up any existing
        pool = get_sqlite_pool()
        assert pool is not None
        close_sqlite_pool()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
