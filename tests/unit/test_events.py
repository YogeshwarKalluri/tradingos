"""Tests for TradingOS Event Bus."""

import asyncio
import pytest

from tradingos.core.events import (
    Event, EventBus, StockDetected, MarketDataReady,
    get_event_bus, set_event_bus, publish_event
)
from tradingos.core.config import reset_config, get_config


class TestEventBus:
    """Test event bus functionality."""
    
    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Setup and teardown for each test."""
        reset_config()
        config = get_config("development")
        bus = EventBus(
            queue_size=config.event_bus.queue_size,
            worker_count=config.event_bus.worker_count
        )
        set_event_bus(bus)
        yield bus
        # Properly stop the bus using the existing event loop
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Schedule stop on the running loop
                asyncio.create_task(bus.stop())
            else:
                loop.run_until_complete(bus.stop())
        except RuntimeError:
            # No event loop, ignore
            pass
    
    @pytest.mark.asyncio
    async def test_subscribe_and_publish(self):
        """Test basic subscribe and publish."""
        bus = get_event_bus()
        await bus.start()
        
        received = []
        
        async def handler(event: Event):
            received.append(event)
        
        bus.subscribe(StockDetected, handler)
        
        event = StockDetected(source="test")
        await publish_event(event)
        
        # Wait for processing
        await asyncio.sleep(0.1)
        
        assert len(received) == 1
        assert received[0].source == "test"
        assert received[0].trace_id == event.trace_id
    
    @pytest.mark.asyncio
    async def test_multiple_subscribers(self):
        """Test multiple subscribers receive event."""
        bus = get_event_bus()
        await bus.start()
        
        received1 = []
        received2 = []
        
        async def handler1(event: Event):
            received1.append(event)
        
        async def handler2(event: Event):
            received2.append(event)
        
        bus.subscribe(StockDetected, handler1)
        bus.subscribe(StockDetected, handler2)
        
        event = StockDetected(source="test")
        await publish_event(event)
        
        await asyncio.sleep(0.1)
        
        assert len(received1) == 1
        assert len(received2) == 1
    
    @pytest.mark.asyncio
    async def test_publish_sync(self):
        """Test synchronous publish waits for handlers."""
        bus = get_event_bus()
        await bus.start()
        
        results = []
        
        async def handler(event: Event):
            await asyncio.sleep(0.01)
            results.append(event.source)
        
        bus.subscribe(StockDetected, handler)
        
        event = StockDetected(source="sync_test")
        await bus.publish_sync(event)
        
        assert results == ["sync_test"]
    
    @pytest.mark.asyncio
    async def test_event_stats(self):
        """Test event bus statistics."""
        bus = get_event_bus()
        await bus.start()
        
        async def handler(event: Event):
            pass
        
        bus.subscribe(StockDetected, handler)
        
        for i in range(5):
            await publish_event(StockDetected(source=f"test_{i}"))
        
        await asyncio.sleep(0.1)
        
        stats = bus.get_stats()
        assert "StockDetected" in stats
        assert stats["StockDetected"]["count"] == 5
    
    @pytest.mark.asyncio
    async def test_unsubscribe(self):
        """Test unsubscribe removes handler."""
        bus = get_event_bus()
        await bus.start()
        
        received = []
        
        async def handler(event: Event):
            received.append(event)
        
        bus.subscribe(StockDetected, handler)
        await publish_event(StockDetected(source="test1"))
        await asyncio.sleep(0.05)
        
        bus.unsubscribe(StockDetected, handler)
        await publish_event(StockDetected(source="test2"))
        await asyncio.sleep(0.05)
        
        assert len(received) == 1
        assert received[0].source == "test1"


class TestEventDataclasses:
    """Test event dataclass definitions."""
    
    def test_stock_detected_creation(self):
        """Test StockDetected event creation."""
        event = StockDetected(source="scanner")
        assert event.event_id is not None
        assert event.trace_id is not None
        assert event.timestamp is not None
        assert event.source == "scanner"
    
    def test_trace_id_propagation(self):
        """Test trace ID is propagated."""
        from tradingos.core.logging import set_trace_id, clear_trace_id
        
        test_trace = "test-trace-123"
        set_trace_id(test_trace)
        
        event = StockDetected(source="test")
        assert event.trace_id == test_trace
        
        clear_trace_id()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])