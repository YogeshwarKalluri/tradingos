"""
Tests for database/duckdb/connection.py
"""

import pytest
import tempfile
from pathlib import Path

from database.duckdb.connection import DuckDBPool, get_duckdb_pool, close_duckdb_pool


class TestDuckDBPool:
    """Test DuckDB connection pool."""
    
    @pytest.fixture
    def temp_db(self):
        """Create a temporary database path for testing."""
        import uuid
        db_path = Path(tempfile.gettempdir()) / f"test_{uuid.uuid4().hex}.duckdb"
        yield db_path
        # Cleanup if file was created
        Path(db_path).unlink(missing_ok=True)
    
    @pytest.fixture
    def pool(self, temp_db):
        """Create a DuckDB pool for testing."""
        from database.duckdb.connection import DuckDBConfig
        config = DuckDBConfig(path=temp_db, memory_limit="1GB", threads=2)
        pool = DuckDBPool(config)
        yield pool
    
    def test_initialization(self, pool):
        """Test pool initialization."""
        assert pool is not None
    
    def test_write_and_read(self, pool):
        """Test write and read operations."""
        # Write
        pool.execute("CREATE TABLE test (id INTEGER, value TEXT)")
        pool.execute("INSERT INTO test VALUES (?, ?)", [1, "hello"])
        pool.execute("INSERT INTO test VALUES (?, ?)", [2, "world"])
        
        # Read
        result = pool.query("SELECT * FROM test ORDER BY id")
        assert len(result) == 2
        assert result.iloc[0]['value'] == 'hello'
        assert result.iloc[1]['value'] == 'world'
    
    def test_fetchone(self, pool):
        """Test fetchone."""
        pool.execute("CREATE TABLE test2 (id INTEGER, value TEXT)")
        pool.execute("INSERT INTO test2 VALUES (?, ?)", [1, "single"])
        
        row = pool.fetchone("SELECT * FROM test2 WHERE id = ?", [1])
        assert row is not None
        assert row[1] == 'single'
        
        # Non-existent
        row = pool.fetchone("SELECT * FROM test2 WHERE id = ?", [999])
        assert row is None
    
    def test_fetchall(self, pool):
        """Test fetchall."""
        pool.execute("CREATE TABLE test3 (id INTEGER, value TEXT)")
        pool.execute("INSERT INTO test3 VALUES (?, ?)", [1, "a"])
        pool.execute("INSERT INTO test3 VALUES (?, ?)", [2, "b"])
        
        rows = pool.fetchall("SELECT * FROM test3 ORDER BY id")
        assert len(rows) == 2
        assert rows[0][1] == 'a'
        assert rows[1][1] == 'b'
    
    def test_context_managers(self, pool):
        """Test read/write context managers."""
        with pool.write() as conn:
            conn.execute("CREATE TABLE test4 (id INTEGER, value TEXT)")
            conn.execute("INSERT INTO test4 VALUES (1, 'ctx')")
        
        with pool.read() as conn:
            result = conn.execute("SELECT * FROM test4").fetchall()
            assert len(result) == 1
            assert result[0][1] == 'ctx'
    
    def test_rollback_on_error(self, pool):
        """Test that rollback works on error."""
        pool.execute("CREATE TABLE test5 (id INTEGER PRIMARY KEY, value TEXT)")
        pool.execute("INSERT INTO test5 VALUES (1, 'first')")
        
        # Try to insert duplicate key
        try:
            with pool.write() as conn:
                conn.execute("INSERT INTO test5 VALUES (1, 'duplicate')")
        except Exception:
            pass
        
        # Original row should still exist
        count = pool.query("SELECT COUNT(*) as c FROM test5").iloc[0]['c']
        assert count == 1
    
    def test_polars_output(self, pool):
        """Test Polars DataFrame output."""
        pool.execute("CREATE TABLE test_pl (id INTEGER, value TEXT)")
        pool.execute("INSERT INTO test_pl VALUES (?, ?)", [1, "polars"])
        
        df = pool.query_pl("SELECT * FROM test_pl")
        assert len(df) == 1
        assert df[0, 'value'] == 'polars'


class TestDuckDBGlobalPool:
    """Test global pool functions."""
    
    def test_get_pool(self):
        """Test getting global pool."""
        # This test just verifies the functions exist and work
        close_duckdb_pool()  # Clean up any existing
        pool = get_duckdb_pool()
        assert pool is not None
        close_duckdb_pool()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])