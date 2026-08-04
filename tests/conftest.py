"""Pytest configuration for TradingOS."""

import asyncio
import sys
from pathlib import Path

import pytest

# Package is installed as 'tradingos' (lowercase)
# No need to add to path since it's installed in editable mode


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset global singletons between tests."""
    from tradingos.core.config import reset_config
    from tradingos.core.events import set_event_bus
    from tradingos.core.models import set_model_manager
    
    reset_config()
    set_event_bus(None)
    set_model_manager(None)
    
    yield
    
    # Cleanup after test
    reset_config()
    set_event_bus(None)
    set_model_manager(None)


def pytest_configure(config):
    """Configure pytest."""
    config.addinivalue_line("markers", "asyncio: mark test as async")


# Async test support
try:
    import pytest_asyncio
except ImportError:
    pass