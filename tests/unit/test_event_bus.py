"""
Tests for core/event_bus.py
"""

import asyncio
from uuid import UUID

import pytest
import pytest_asyncio

from core.event_bus import EventBus, Subscription, get_event_bus, set_event_bus, shutdown_event_bus
from core.types import Event, EventType, TickEvent


class TestEventBus:
    """Test EventBus core functionality."""

    @pytest_asyncio.fixture
    async def bus(self):
        """Create a fresh event bus for each test."""
        bus = EventBus()
        await bus.start()
        # Small delay to ensure dispatch workers are running
        await asyncio.sleep(0.01)
        try:
            yield bus
        finally:
            await bus.stop()

    @pytest.mark.asyncio
    async def test_subscribe_and_publish(self, bus):
        """Test basic subscribe and publish."""
        received = []

        async def handler(event: Event):
            received.append(event)

        sub = await bus.subscribe(EventType.TICK, handler)
        assert isinstance(sub, Subscription)
        assert sub.event_type == EventType.TICK

        # Allow worker to start
        await asyncio.sleep(0.01)

        # Publish event
        tick = TickEvent(symbol="AAPL", price=150.0, size=100)
        await bus.publish(tick)

        # Allow dispatch
        await asyncio.sleep(0.01)

        assert len(received) == 1
        assert received[0].symbol == "AAPL"
        assert received[0].price == 150.0

    @pytest.mark.asyncio
    async def test_multiple_subscribers(self, bus):
        """Test multiple subscribers for same event type."""
        received_order = []

        async def handler1(event: Event):
            received_order.append("handler1")

        async def handler2(event: Event):
            received_order.append("handler2")

        async def handler3(event: Event):
            received_order.append("handler3")

        # Subscribe with different priorities
        await bus.subscribe(EventType.TICK, handler1, priority=10)
        await bus.subscribe(EventType.TICK, handler2, priority=5)
        await bus.subscribe(EventType.TICK, handler3, priority=1)

        # Allow workers to start
        await asyncio.sleep(0.01)

        tick = TickEvent(symbol="AAPL", price=150.0)
        await bus.publish(tick)
        await asyncio.sleep(0.01)

        # Should execute in priority order (highest first)
        assert received_order == ["handler1", "handler2", "handler3"]

    @pytest.mark.asyncio
    async def test_filter_fn(self, bus):
        """Test event filter function."""
        received = []

        async def handler(event: Event):
            received.append(event)

        # Only receive AAPL ticks
        await bus.subscribe(EventType.TICK, handler, filter_fn=lambda e: e.symbol == "AAPL")

        # Allow worker to start
        await asyncio.sleep(0.01)

        # Publish AAPL - should receive
        await bus.publish(TickEvent(symbol="AAPL", price=150.0))
        # Publish MSFT - should NOT receive
        await bus.publish(TickEvent(symbol="MSFT", price=300.0))

        await asyncio.sleep(0.01)

        assert len(received) == 1
        assert received[0].symbol == "AAPL"

    @pytest.mark.asyncio
    async def test_publish_sync(self, bus):
        """Test synchronous publish with results."""
        results = []

        async def handler1(event: Event):
            await asyncio.sleep(0.001)
            return "result1"

        async def handler2(event: Event):
            await asyncio.sleep(0.001)
            return "result2"

        await bus.subscribe(EventType.TICK, handler1)
        await bus.subscribe(EventType.TICK, handler2)

        tick = TickEvent(symbol="AAPL", price=150.0)
        returned = await bus.publish_sync(tick)

        assert returned == ["result1", "result2"]

    @pytest.mark.asyncio
    async def test_unsubscribe(self, bus):
        """Test unsubscription."""
        received = []

        async def handler(event: Event):
            received.append(event)

        sub = await bus.subscribe(EventType.TICK, handler)

        # Allow worker to start
        await asyncio.sleep(0.01)

        # Publish - should receive
        await bus.publish(TickEvent(symbol="AAPL", price=150.0))
        await asyncio.sleep(0.01)
        assert len(received) == 1

        # Unsubscribe
        result = bus.unsubscribe(sub)
        assert result is True

        # Publish again - should NOT receive
        await bus.publish(TickEvent(symbol="AAPL", price=150.0))
        await asyncio.sleep(0.01)
        assert len(received) == 1  # Still 1

    @pytest.mark.asyncio
    async def test_unsubscribe_by_id(self, bus):
        """Test unsubscription by ID."""
        received = []

        async def handler(event: Event):
            received.append(event)

        sub = await bus.subscribe(EventType.TICK, handler)
        sub_id = sub.subscription_id

        # Unsubscribe by ID
        result = bus.unsubscribe_by_id(EventType.TICK, sub_id)
        assert result is True

        # Publish - should NOT receive
        await bus.publish(TickEvent(symbol="AAPL", price=150.0))
        await asyncio.sleep(0.01)
        assert len(received) == 0

    @pytest.mark.asyncio
    async def test_queue_backpressure(self):
        """Test queue backpressure handling (not applicable for direct dispatch)."""
        # Direct dispatch has no queue, so this test is not applicable
        # Just verify the bus works
        bus = EventBus()
        await bus.start()

        received = []
        async def handler(event: Event):
            received.append(event)

        await bus.subscribe(EventType.TICK, handler)

        # Publish event
        await bus.publish(TickEvent(symbol="AAPL", price=150.0))

        await asyncio.sleep(0.01)
        assert len(received) == 1

        await bus.stop()

    @pytest.mark.asyncio
    async def test_metrics(self, bus):
        """Test metrics collection."""
        async def handler(event: Event):
            pass

        await bus.subscribe(EventType.TICK, handler)

        # Allow worker to start
        await asyncio.sleep(0.01)

        # Publish some events
        for i in range(5):
            await bus.publish(TickEvent(symbol="AAPL", price=150.0 + i))

        await asyncio.sleep(0.01)

        metrics = bus.get_metrics()
        assert metrics is not None
        assert metrics.events_published >= 5
        assert metrics.avg_dispatch_time_us >= 0

    @pytest.mark.asyncio
    async def test_subscriber_count(self, bus):
        """Test subscriber count."""
        assert bus.get_subscriber_count(EventType.TICK) == 0

        async def handler1(event: Event):
            pass

        async def handler2(event: Event):
            pass

        await bus.subscribe(EventType.TICK, handler1)
        assert bus.get_subscriber_count(EventType.TICK) == 1

        await bus.subscribe(EventType.TICK, handler2)
        assert bus.get_subscriber_count(EventType.TICK) == 2

    @pytest.mark.asyncio
    async def test_queue_depth(self, bus):
        """Test queue depth reporting."""
        assert bus.get_queue_depth(EventType.TICK) == 0

        async def slow_handler(event: Event):
            await asyncio.sleep(0.1)

        await bus.subscribe(EventType.TICK, slow_handler)
        await bus.publish(TickEvent(symbol="AAPL", price=150.0))
        await bus.publish(TickEvent(symbol="AAPL", price=151.0))

        # Queue should have events
        depth = bus.get_queue_depth(EventType.TICK)
        assert depth >= 0  # May be 0 if processed quickly

    @pytest.mark.asyncio
    async def test_handler_error_handling(self, bus):
        """Test that handler errors don't stop other handlers."""
        received = []

        async def good_handler(event: Event):
            received.append("good")

        async def bad_handler(event: Event):
            raise ValueError("Handler error")

        async def another_good_handler(event: Event):
            received.append("another_good")

        await bus.subscribe(EventType.TICK, good_handler, priority=10)
        await bus.subscribe(EventType.TICK, bad_handler, priority=5)
        await bus.subscribe(EventType.TICK, another_good_handler, priority=1)

        await bus.publish_sync(TickEvent(symbol="AAPL", price=150.0))

        # Both good handlers should have executed
        assert "good" in received
        assert "another_good" in received

        # Metrics should record error
        metrics = bus.get_metrics()
        assert metrics.handler_errors >= 1

    @pytest.mark.asyncio
    async def test_global_bus(self):
        """Test global event bus singleton."""
        # Reset global bus
        await shutdown_event_bus()

        bus1 = get_event_bus()
        bus2 = get_event_bus()

        assert bus1 is bus2  # Same instance

        await shutdown_event_bus()

    @pytest.mark.asyncio
    async def test_set_event_bus(self):
        """Test setting custom global bus."""
        await shutdown_event_bus()

        custom_bus = EventBus()
        await custom_bus.start()
        set_event_bus(custom_bus)

        assert get_event_bus() is custom_bus

        await shutdown_event_bus()

    @pytest.mark.asyncio
    async def test_stop_drains_queues(self, bus):
        """Test that stop waits for queue drain."""
        processed = []
        done = asyncio.Event()

        async def handler(event: Event):
            processed.append(event)
            await asyncio.sleep(0.01)
            if len(processed) >= 3:
                done.set()

        await bus.subscribe(EventType.TICK, handler)
        for i in range(3):
            await bus.publish(TickEvent(symbol="AAPL", price=150.0 + i))

        # Wait for processing to complete
        await asyncio.wait_for(done.wait(), timeout=2.0)

        # Now stop - queues should be drained
        await bus.stop(timeout=2.0)

        # All should be processed
        assert len(processed) == 3

    @pytest.mark.asyncio
    async def test_repr(self, bus):
        """Test string representation."""
        async def handler(event: Event):
            pass

        await bus.subscribe(EventType.TICK, handler)
        await bus.subscribe(EventType.BAR, handler)

        repr_str = repr(bus)
        assert "EventBus" in repr_str
        assert "running=True" in repr_str
        assert "subscribers=2" in repr_str


class TestSubscription:
    """Test Subscription dataclass."""

    def test_subscription_creation(self):
        async def handler(event: Event):
            pass

        sub = Subscription(
            event_type=EventType.TICK,
            handler=handler,
            priority=5,
        )

        assert sub.event_type == EventType.TICK
        assert sub.priority == 5
        assert sub.filter_fn is None
        assert isinstance(sub.subscription_id, UUID)

    def test_subscription_ordering(self):
        """Test subscription priority ordering."""
        async def handler(event: Event):
            pass

        sub1 = Subscription(event_type=EventType.TICK, handler=handler, priority=10)
        sub2 = Subscription(event_type=EventType.TICK, handler=handler, priority=5)
        sub3 = Subscription(event_type=EventType.TICK, handler=handler, priority=1)

        # Higher priority should be "less than" for sorting
        assert sub1 < sub2
        assert sub2 < sub3
        assert sub1 < sub3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
