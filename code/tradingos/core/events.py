"""TradingOS Event Bus - Async Pub/Sub with Typed Events."""

import asyncio
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Set, Type, TypeVar
import structlog

from tradingos.core.logging import get_logger, get_trace_id, set_trace_id, clear_trace_id

logger = get_logger(__name__)

# Type variables for generic event handling
EventT = TypeVar("EventT", bound="Event")


@dataclass
class Event:
    """Base event class with metadata."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    trace_id: str = field(default_factory=get_trace_id)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source: str = "unknown"
    
    def __post_init__(self):
        if not self.trace_id:
            self.trace_id = get_trace_id()


# Core system events
@dataclass
class StockDetected(Event):
    """Scanner detected a new candidate."""
    candidate: "StockCandidate" = None  # Forward reference
    source: str = "scanner"


@dataclass
class MarketDataReady(Event):
    """Market data enriched for candidate."""
    candidate: "StockCandidate" = None
    market_data: "MarketData" = None
    source: str = "market_data"


@dataclass
class ChartReady(Event):
    """Chart tensor generated for candidate."""
    candidate: "StockCandidate" = None
    chart_tensor: "ChartTensor" = None
    source: str = "charts"


@dataclass
class IndicatorsReady(Event):
    """Indicators calculated for candidate."""
    candidate: "StockCandidate" = None
    indicators: "IndicatorSnapshot" = None
    source: str = "indicators"


@dataclass
class VisionResult(Event):
    """Vision analysis complete for candidate."""
    candidate: "StockCandidate" = None
    vision_output: "VisionOutput" = None
    source: str = "vision"


@dataclass
class MemoryResults(Event):
    """Similar historical trades retrieved."""
    candidate: "StockCandidate" = None
    similar_trades: List["HistoricalTrade"] = field(default_factory=list)
    source: str = "memory"


@dataclass
class ThesisReady(Event):
    """Reasoning engine produced trade thesis."""
    candidate: "StockCandidate" = None
    thesis: "TradeThesis" = None
    source: str = "reasoning"


@dataclass
class RiskDecision(Event):
    """Risk engine decision."""
    candidate: "StockCandidate" = None
    decision: "RiskDecisionResult" = None
    source: str = "risk"


@dataclass
class OrderSubmitted(Event):
    """Order submitted to execution engine."""
    order: "Order" = None
    source: str = "execution"


@dataclass
class FillReceived(Event):
    """Fill received from execution."""
    fill: "Fill" = None
    source: str = "execution"


@dataclass
class PipelineError(Event):
    """Pipeline stage error."""
    stage: str = ""
    error_type: str = ""
    error_message: str = ""
    candidate: Optional["StockCandidate"] = None
    source: str = "pipeline"


@dataclass
class DataQualityWarning(Event):
    """Market data quality issue."""
    ticker: str = ""
    issue: str = ""
    severity: str = "warning"  # warning, error
    source: str = "market_data"


# Type alias for event handlers
EventHandler = Callable[[Event], Any]


class EventBus:
    """Async event bus with typed subscriptions."""
    
    def __init__(self, queue_size: int = 10000, worker_count: int = 4):
        self.queue_size = queue_size
        self.worker_count = worker_count
        self._subscribers: Dict[Type[Event], List[EventHandler]] = defaultdict(list)
        self._queues: Dict[Type[Event], asyncio.Queue] = {}
        self._workers: List[asyncio.Task] = []
        self._running = False
        self._event_counts: Dict[str, int] = defaultdict(int)
        self._latency_sum: Dict[str, float] = defaultdict(float)
    
    def subscribe(self, event_type: Type[EventT], handler: EventHandler) -> None:
        """Subscribe handler to event type."""
        self._subscribers[event_type].append(handler)
        if event_type not in self._queues:
            self._queues[event_type] = asyncio.Queue(maxsize=self.queue_size)
            # If bus is running, start workers for this new queue
            if self._running:
                for i in range(self.worker_count):
                    task = asyncio.create_task(self._worker(event_type, self._queues[event_type], i))
                    self._workers.append(task)
        logger.debug("subscribed", event_type=event_type.__name__, handler=handler.__name__)
    
    def unsubscribe(self, event_type: Type[Event], handler: EventHandler) -> None:
        """Unsubscribe handler from event type."""
        if handler in self._subscribers[event_type]:
            self._subscribers[event_type].remove(handler)
    
    async def publish(self, event: Event) -> None:
        """Publish event to all subscribers."""
        event_type = type(event)
        self._event_counts[event_type.__name__] += 1
        
        # Log event
        logger.debug("event_published", 
                    event_type=event_type.__name__, 
                    trace_id=event.trace_id,
                    event_id=event.event_id)
        
        # Put in queue for workers
        if event_type in self._queues:
            try:
                self._queues[event_type].put_nowait(event)
            except asyncio.QueueFull:
                logger.warning("event_queue_full", event_type=event_type.__name__)
    
    async def publish_sync(self, event: Event) -> None:
        """Publish event and wait for all handlers to complete."""
        event_type = type(event)
        handlers = self._subscribers.get(event_type, [])
        
        if not handlers:
            return
        
        start = datetime.now(timezone.utc)
        
        # Run all handlers concurrently
        await asyncio.gather(*[handler(event) for handler in handlers], return_exceptions=True)
        
        elapsed = (datetime.now(timezone.utc) - start).total_seconds() * 1000
        self._latency_sum[event_type.__name__] += elapsed
        
        logger.debug("event_processed_sync", 
                    event_type=event_type.__name__, 
                    handlers=len(handlers),
                    elapsed_ms=elapsed)
    
    async def start(self) -> None:
        """Start event bus workers."""
        if self._running:
            return
        
        self._running = True
        
        # Start worker for each event type
        for event_type, queue in self._queues.items():
            for i in range(self.worker_count):
                task = asyncio.create_task(self._worker(event_type, queue, i))
                self._workers.append(task)
        
        logger.info("event_bus_started", workers=len(self._workers))
    
    async def stop(self) -> None:
        """Stop event bus workers."""
        if not self._running:
            return
        
        self._running = False
        
        # Cancel all workers
        for task in self._workers:
            task.cancel()
        
        # Wait for cancellation
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()
        
        logger.info("event_bus_stopped")
    
    async def _worker(self, event_type: Type[Event], queue: asyncio.Queue, worker_id: int) -> None:
        """Worker task to process events from queue."""
        logger.debug("worker_started", event_type=event_type.__name__, worker_id=worker_id)
        
        while self._running:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=1.0)
                
                # Set trace context for this event
                previous_trace = get_trace_id()
                set_trace_id(event.trace_id)
                
                try:
                    handlers = self._subscribers.get(event_type, [])
                    if handlers:
                        start = datetime.now(timezone.utc)
                        await asyncio.gather(*[handler(event) for handler in handlers], return_exceptions=True)
                        elapsed = (datetime.now(timezone.utc) - start).total_seconds() * 1000
                        self._latency_sum[event_type.__name__] += elapsed
                        
                        logger.debug("event_processed", 
                                    event_type=event_type.__name__, 
                                    worker_id=worker_id,
                                    handlers=len(handlers),
                                    elapsed_ms=elapsed)
                except Exception as e:
                    logger.error("worker_error", 
                                event_type=event_type.__name__, 
                                worker_id=worker_id,
                                error=str(e))
                finally:
                    # Restore trace context
                    if previous_trace:
                        set_trace_id(previous_trace)
                    else:
                        clear_trace_id()
                        
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("worker_exception", 
                            event_type=event_type.__name__, 
                            worker_id=worker_id,
                            error=str(e))
        
        logger.debug("worker_stopped", event_type=event_type.__name__, worker_id=worker_id)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get event bus statistics."""
        stats = {}
        for event_name, count in self._event_counts.items():
            avg_latency = self._latency_sum[event_name] / count if count > 0 else 0
            stats[event_name] = {
                "count": count,
                "avg_latency_ms": round(avg_latency, 2),
                "queue_size": self._queues.get(event_name, asyncio.Queue()).qsize() if event_name in self._queues else 0
            }
        return stats


# Global event bus instance
_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Get global event bus instance."""
    global _event_bus
    if _event_bus is None:
        config = get_config()
        _event_bus = EventBus(
            queue_size=config.event_bus.queue_size,
            worker_count=config.event_bus.worker_count
        )
    return _event_bus


def set_event_bus(bus: EventBus) -> None:
    """Set global event bus instance (for testing)."""
    global _event_bus
    _event_bus = bus


# Convenience function for publishing
async def publish_event(event: Event) -> None:
    """Publish event to global event bus."""
    bus = get_event_bus()
    await bus.publish(event)


async def publish_event_sync(event: Event) -> None:
    """Publish event synchronously to global event bus."""
    bus = get_event_bus()
    await bus.publish_sync(event)