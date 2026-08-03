"""
In-Process Async Event Bus for TradingOS
Direct dispatch, zero-copy event handling optimized for low latency.
"""

from __future__ import annotations
import asyncio
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable, TypeVar
from uuid import UUID, uuid4

from core.types import Event, EventType

T = TypeVar('T', bound=Event)


@dataclass(slots=True)
class Subscription:
    """Event subscription with priority and filter."""
    event_type: EventType
    handler: Callable[[Event], Awaitable[None]]
    priority: int = 0  # Higher = earlier execution
    filter_fn: Callable[[Event], bool] | None = None
    subscription_id: UUID = field(default_factory=uuid4)
    created_at: float = field(default_factory=time.time)
    
    def __lt__(self, other: Subscription) -> bool:
        # For priority queue ordering (higher priority first)
        return self.priority > other.priority


@dataclass(slots=True)
class EventBusMetrics:
    """Event bus performance metrics."""
    events_published: int = 0
    events_dropped: int = 0
    handler_errors: int = 0
    total_dispatch_time_ns: int = 0
    
    def record_publish(self, dispatch_time_ns: int):
        self.events_published += 1
        self.total_dispatch_time_ns += dispatch_time_ns
    
    def record_drop(self):
        self.events_dropped += 1
    
    def record_error(self):
        self.handler_errors += 1
    
    @property
    def avg_dispatch_time_us(self) -> float:
        if self.events_published == 0:
            return 0.0
        return (self.total_dispatch_time_ns / self.events_published) / 1000


class EventBus:
    """
    High-performance in-process async event bus with direct dispatch.
    
    Features:
    - Direct async handler execution (no queue overhead)
    - Priority-based handler ordering
    - Zero-copy event dispatch (no serialization)
    - Filter support for conditional handling
    - Comprehensive metrics
    - Sub-millisecond dispatch latency
    """
    
    def __init__(
        self,
        default_priority: int = 0,
        enable_metrics: bool = True,
    ):
        self._subscribers: dict[EventType, list[Subscription]] = defaultdict(list)
        self._default_priority = default_priority
        self._enable_metrics = enable_metrics
        self._metrics = EventBusMetrics() if enable_metrics else None
        self._running = False
    
    async def start(self) -> None:
        """Start the event bus."""
        if self._running:
            return
        self._running = True
    
    async def stop(self, timeout: float = 5.0) -> None:
        """Stop the event bus."""
        self._running = False
    
    async def subscribe(
        self,
        event_type: EventType,
        handler: Callable[[Event], Awaitable[None]],
        priority: int | None = None,
        filter_fn: Callable[[Event], bool] | None = None,
    ) -> Subscription:
        """
        Subscribe to an event type.
        
        Args:
            event_type: Event type to subscribe to
            handler: Async callback function
            priority: Handler priority (higher = earlier execution)
            filter_fn: Optional filter function(event) -> bool
        
        Returns:
            Subscription object for later unsubscription
        """
        subscription = Subscription(
            event_type=event_type,
            handler=handler,
            priority=priority if priority is not None else self._default_priority,
            filter_fn=filter_fn,
        )
        
        # Insert maintaining priority order (highest first)
        subscribers = self._subscribers[event_type]
        inserted = False
        for i, sub in enumerate(subscribers):
            if subscription.priority > sub.priority:
                subscribers.insert(i, subscription)
                inserted = True
                break
        if not inserted:
            subscribers.append(subscription)
        
        return subscription
    
    def unsubscribe(self, subscription: Subscription) -> bool:
        """Unsubscribe a handler."""
        subscribers = self._subscribers.get(subscription.event_type, [])
        for i, sub in enumerate(subscribers):
            if sub.subscription_id == subscription.subscription_id:
                subscribers.pop(i)
                return True
        return False
    
    def unsubscribe_by_id(self, event_type: EventType, subscription_id: UUID) -> bool:
        """Unsubscribe by subscription ID."""
        subscribers = self._subscribers.get(event_type, [])
        for i, sub in enumerate(subscribers):
            if sub.subscription_id == subscription_id:
                subscribers.pop(i)
                return True
        return False
    
    async def publish(self, event: Event) -> None:
        """
        Fire-and-forget event publish.
        Dispatches directly to all matching handlers.
        """
        if not self._running:
            await self.start()
        
        subscribers = self._subscribers.get(event.event_type, [])
        if not subscribers:
            if self._metrics:
                self._metrics.record_drop()
            return
        
        # Filter subscribers
        filtered = [
            sub for sub in subscribers
            if sub.filter_fn is None or sub.filter_fn(event)
        ]
        
        if not filtered:
            return
        
        start = time.time_ns()
        
        # Execute handlers in priority order
        for sub in filtered:
            try:
                await sub.handler(event)
            except Exception as e:
                if self._metrics:
                    self._metrics.record_error()
                import logging
                logging.getLogger(__name__).error(
                    f"Handler error for {event.event_type}: {e}",
                    exc_info=True
                )
        
        if self._metrics:
            self._metrics.record_publish(time.time_ns() - start)
    
    async def publish_sync(self, event: Event, timeout: float | None = None) -> list[Any]:
        """
        Publish event and wait for all handlers to complete.
        Returns list of handler results.
        """
        if not self._running:
            await self.start()
        
        subscribers = self._subscribers.get(event.event_type, [])
        if not subscribers:
            return []
        
        # Filter subscribers
        filtered = [
            sub for sub in subscribers
            if sub.filter_fn is None or sub.filter_fn(event)
        ]
        
        if not filtered:
            return []
        
        start = time.time_ns()
        results = []
        
        # Execute handlers in priority order
        for sub in filtered:
            try:
                result = await sub.handler(event)
                results.append(result)
            except Exception as e:
                if self._metrics:
                    self._metrics.record_error()
                import logging
                logging.getLogger(__name__).error(
                    f"Handler error for {event.event_type}: {e}",
                    exc_info=True
                )
        
        if self._metrics:
            self._metrics.record_publish(time.time_ns() - start)
        
        return results
    
    async def publish_and_wait(
        self,
        event: Event,
        expected_handlers: int | None = None,
        timeout: float = 30.0,
    ) -> list[Any]:
        """
        Publish and wait for handlers to complete.
        Useful for request-response patterns.
        """
        return await self.publish_sync(event, timeout)
    
    def get_subscriber_count(self, event_type: EventType) -> int:
        """Get number of subscribers for an event type."""
        return len(self._subscribers.get(event_type, []))
    
    def get_queue_depth(self, event_type: EventType) -> int:
        """Get current queue depth (always 0 for direct dispatch)."""
        return 0
    
    def get_metrics(self) -> EventBusMetrics | None:
        """Get event bus metrics."""
        return self._metrics
    
    def clear_metrics(self) -> None:
        """Reset metrics."""
        if self._metrics:
            self._metrics = EventBusMetrics()
    
    @property
    def is_running(self) -> bool:
        return self._running
    
    def __repr__(self) -> str:
        return (
            f"EventBus(running={self._running}, "
            f"subscribers={sum(len(s) for s in self._subscribers.values())})"
        )


# Global event bus instance (singleton pattern for convenience)
_global_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    """Get or create the global event bus."""
    global _global_bus
    if _global_bus is None:
        _global_bus = EventBus()
    return _global_bus


def set_event_bus(bus: EventBus) -> None:
    """Set the global event bus (for testing)."""
    global _global_bus
    _global_bus = bus


async def shutdown_event_bus() -> None:
    """Shutdown the global event bus."""
    global _global_bus
    if _global_bus:
        await _global_bus.stop()
        _global_bus = None