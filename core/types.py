"""
Core Type Definitions for TradingOS
All events, enums, and shared types used across modules.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Generic, TypeVar
from uuid import UUID, uuid4
import time

# Type variables for generic events
T = TypeVar('T')


class Timeframe(str, Enum):
    """Chart timeframes."""
    TICK = "tick"
    SEC_1 = "1s"
    SEC_5 = "5s"
    SEC_15 = "15s"
    SEC_30 = "30s"
    MIN_1 = "1m"
    MIN_2 = "2m"
    MIN_3 = "3m"
    MIN_5 = "5m"
    MIN_15 = "15m"
    MIN_30 = "30m"
    HOUR_1 = "1h"
    HOUR_2 = "2h"
    HOUR_4 = "4h"
    DAY_1 = "1d"
    WEEK_1 = "1w"
    MONTH_1 = "1M"


class Side(str, Enum):
    """Order side."""
    BUY = "buy"
    SELL = "sell"


class Action(str, Enum):
    """Trading action."""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    CLOSE = "close"


class OrderType(str, Enum):
    """Order types."""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    TRAILING_STOP = "trailing_stop"


class OrderStatus(str, Enum):
    """Order status."""
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIAL = "partial"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class PatternType(str, Enum):
    """Chart pattern types."""
    BULL_FLAG = "bull_flag"
    BEAR_FLAG = "bear_flag"
    CUP_HANDLE = "cup_handle"
    DOUBLE_BOTTOM = "double_bottom"
    DOUBLE_TOP = "double_top"
    HEAD_SHOULDERS = "head_shoulders"
    INVERSE_HEAD_SHOULDERS = "inverse_head_shoulders"
    VWAP_RECLAIM = "vwap_reclaim"
    VWAP_BREAK = "vwap_break"
    OPENING_RANGE_BREAKOUT = "opening_range_breakout"
    OPENING_RANGE_BREAKDOWN = "opening_range_breakdown"
    ABCD = "abcd"
    THREE_DRIVES = "three_drives"
    WEDGE_RISING = "wedge_rising"
    WEDGE_FALLING = "wedge_falling"
    TRIANGLE_ASCENDING = "triangle_ascending"
    TRIANGLE_DESCENDING = "triangle_descending"
    TRIANGLE_SYMMETRICAL = "triangle_symmetrical"
    RECTANGLE = "rectangle"
    CHANNEL_UP = "channel_up"
    CHANNEL_DOWN = "channel_down"


class EventType(str, Enum):
    """Event types for the event bus."""
    # Market data events
    TICK = "tick"
    BAR = "bar"
    QUOTE = "quote"
    MARKET_OPEN = "market_open"
    MARKET_CLOSE = "market_close"
    
    # Scanner events
    STOCK_DETECTED = "stock_detected"
    FILTER_PASSED = "filter_passed"
    
    # Chart events
    CHART_READY = "chart_ready"
    CHART_UPDATED = "chart_updated"
    
    # Technical indicator events
    INDICATORS_COMPUTED = "indicators_computed"
    
    # Vision events
    PATTERN_DETECTED = "pattern_detected"
    PATTERN_CONFIRMED = "pattern_confirmed"
    
    # Memory events
    SIMILAR_TRADES_FOUND = "similar_trades_found"
    TRADE_EMBEDDED = "trade_embedded"
    
    # Reasoning events
    TRADE_DECISION = "trade_decision"
    DECISION_REQUIRED = "decision_required"
    
    # Risk events
    RISK_APPROVED = "risk_approved"
    RISK_REJECTED = "risk_rejected"
    RISK_WARNING = "risk_warning"
    
    # Execution events
    ORDER_SUBMITTED = "order_submitted"
    ORDER_FILLED = "order_filled"
    ORDER_CANCELLED = "order_cancelled"
    ORDER_REJECTED = "order_rejected"
    POSITION_OPENED = "position_opened"
    POSITION_CLOSED = "position_closed"
    POSITION_UPDATED = "position_updated"
    
    # Journal events
    TRADE_RECORDED = "trade_recorded"
    TRADE_ANALYZED = "trade_analyzed"
    
    # Learning events
    LEARNING_STARTED = "learning_started"
    LEARNING_COMPLETED = "learning_completed"
    MODEL_EVALUATED = "model_evaluated"
    REPORT_GENERATED = "report_generated"
    
    # System events
    STARTUP = "startup"
    SHUTDOWN = "shutdown"
    ERROR = "error"
    HEARTBEAT = "heartbeat"


@dataclass(slots=True)
class Event:
    """Base event class with timestamp and metadata."""
    event_type: EventType = EventType.TICK
    timestamp_ns: int = field(default_factory=lambda: time.time_ns())
    source: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    correlation_id: UUID = field(default_factory=uuid4)
    
    @property
    def timestamp(self) -> datetime:
        return datetime.fromtimestamp(self.timestamp_ns / 1e9)
    
    @property
    def timestamp_ms(self) -> int:
        return self.timestamp_ns // 1_000_000


@dataclass(slots=True)
class TickEvent(Event):
    """Real-time tick data."""
    symbol: str = ""
    price: float = 0.0
    size: int = 0
    bid: float = 0.0
    ask: float = 0.0
    bid_size: int = 0
    ask_size: int = 0
    exchange: str = ""
    conditions: list[str] = field(default_factory=list)
    event_type: EventType = field(default=EventType.TICK, init=False)
    
    def __post_init__(self):
        self.event_type = EventType.TICK


@dataclass(slots=True)
class BarEvent(Event):
    """OHLCV bar data."""
    symbol: str = ""
    timeframe: Timeframe = Timeframe.MIN_1
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    volume: int = 0
    vwap: float = 0.0
    trades: int = 0
    start_ns: int = 0
    end_ns: int = 0
    event_type: EventType = field(default=EventType.BAR, init=False)
    
    def __post_init__(self):
        self.event_type = EventType.BAR


@dataclass(slots=True)
class QuoteEvent(Event):
    """Level 1 quote data."""
    symbol: str = ""
    bid: float = 0.0
    ask: float = 0.0
    bid_size: int = 0
    ask_size: int = 0
    timestamp_ns: int = field(default_factory=lambda: time.time_ns())
    event_type: EventType = field(default=EventType.QUOTE, init=False)
    
    def __post_init__(self):
        self.event_type = EventType.QUOTE


@dataclass(slots=True)
class StockDetectedEvent(Event):
    """Scanner detected a stock meeting criteria."""
    symbol: str = ""
    price: float = 0.0
    volume: int = 0
    change_pct: float = 0.0
    relative_volume: float = 0.0
    scanner_id: str = ""
    filters_passed: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    event_type: EventType = field(default=EventType.STOCK_DETECTED, init=False)
    
    def __post_init__(self):
        self.event_type = EventType.STOCK_DETECTED


@dataclass(slots=True)
class ChartReadyEvent(Event):
    """Chart tensor ready for analysis."""
    symbol: str = ""
    timeframe: Timeframe = Timeframe.MIN_1
    # Zero-copy reference to GPU tensor (shape: C, H, W)
    chart_tensor: Any = None  # torch.Tensor or memoryview
    indicators: dict[str, Any] = field(default_factory=dict)  # indicator name -> tensor
    metadata: dict[str, Any] = field(default_factory=dict)
    event_type: EventType = field(default=EventType.CHART_READY, init=False)
    
    def __post_init__(self):
        self.event_type = EventType.CHART_READY


@dataclass(slots=True)
class PatternDetectedEvent(Event):
    """Vision model detected a pattern."""
    symbol: str = ""
    pattern_type: PatternType = PatternType.BULL_FLAG
    confidence: float = 0.0
    bounding_box: tuple[int, int, int, int] = (0, 0, 0, 0)  # x, y, w, h
    timeframe: Timeframe = Timeframe.MIN_1
    chart_tensor: Any = None  # reference to chart region
    metadata: dict[str, Any] = field(default_factory=dict)
    event_type: EventType = field(default=EventType.PATTERN_DETECTED, init=False)
    
    def __post_init__(self):
        self.event_type = EventType.PATTERN_DETECTED


@dataclass(slots=True)
class SimilarTradesFoundEvent(Event):
    """Memory engine found similar historical trades."""
    symbol: str = ""
    current_setup: dict[str, Any] = field(default_factory=dict)
    similar_trades: list[dict[str, Any]] = field(default_factory=list)
    similarity_scores: list[float] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    event_type: EventType = field(default=EventType.SIMILAR_TRADES_FOUND, init=False)
    
    def __post_init__(self):
        self.event_type = EventType.SIMILAR_TRADES_FOUND


@dataclass(slots=True)
class TradeDecisionEvent(Event):
    """Reasoning engine made a trade decision."""
    symbol: str = ""
    action: Action = Action.HOLD
    confidence: float = 0.0
    reasoning: str = ""
    evidence: list[dict[str, Any]] = field(default_factory=list)
    position_size: float = 0.0
    entry_price: float = 0.0
    stop_loss: float = 0.0
    take_profit: float = 0.0
    risk_reward: float = 0.0
    timeframe: Timeframe = Timeframe.MIN_1
    metadata: dict[str, Any] = field(default_factory=dict)
    event_type: EventType = field(default=EventType.TRADE_DECISION, init=False)
    
    def __post_init__(self):
        self.event_type = EventType.TRADE_DECISION


@dataclass(slots=True)
class RiskApprovedEvent(Event):
    """Risk engine approved the trade."""
    decision: TradeDecisionEvent = None  # type: ignore
    approved_size: float = 0.0
    risk_metrics: dict[str, float] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    event_type: EventType = field(default=EventType.RISK_APPROVED, init=False)
    
    def __post_init__(self):
        self.event_type = EventType.RISK_APPROVED


@dataclass(slots=True)
class RiskRejectedEvent(Event):
    """Risk engine rejected the trade."""
    decision: TradeDecisionEvent = None  # type: ignore
    reason: str = ""
    risk_metrics: dict[str, float] = field(default_factory=dict)
    event_type: EventType = field(default=EventType.RISK_REJECTED, init=False)
    
    def __post_init__(self):
        self.event_type = EventType.RISK_REJECTED


@dataclass(slots=True)
class OrderEvent(Event):
    """Base order event."""
    order_id: UUID = field(default_factory=uuid4)
    symbol: str = ""
    side: Side = Side.BUY
    order_type: OrderType = OrderType.MARKET
    quantity: float = 0.0
    price: float = 0.0  # limit/stop price
    status: OrderStatus = OrderStatus.PENDING
    filled_qty: float = 0.0
    avg_fill_price: float = 0.0
    commission: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    event_type: EventType = field(default=EventType.ORDER_SUBMITTED, init=False)


@dataclass(slots=True)
class OrderSubmittedEvent(OrderEvent):
    event_type: EventType = field(default=EventType.ORDER_SUBMITTED, init=False)
    
    def __post_init__(self):
        self.event_type = EventType.ORDER_SUBMITTED


@dataclass(slots=True)
class OrderFilledEvent(OrderEvent):
    fill_price: float = 0.0
    fill_qty: float = 0.0
    fill_timestamp_ns: int = field(default_factory=lambda: time.time_ns())
    event_type: EventType = field(default=EventType.ORDER_FILLED, init=False)
    
    def __post_init__(self):
        self.event_type = EventType.ORDER_FILLED


@dataclass(slots=True)
class PositionEvent(Event):
    """Position update event."""
    position_id: UUID = field(default_factory=uuid4)
    symbol: str = ""
    side: Side = Side.BUY
    quantity: float = 0.0
    entry_price: float = 0.0
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    stop_loss: float = 0.0
    take_profit: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    event_type: EventType = field(default=EventType.POSITION_OPENED, init=False)


@dataclass(slots=True)
class PositionOpenedEvent(PositionEvent):
    event_type: EventType = field(default=EventType.POSITION_OPENED, init=False)
    
    def __post_init__(self):
        self.event_type = EventType.POSITION_OPENED


@dataclass(slots=True)
class PositionClosedEvent(PositionEvent):
    exit_price: float = 0.0
    exit_reason: str = ""
    event_type: EventType = field(default=EventType.POSITION_CLOSED, init=False)
    
    def __post_init__(self):
        self.event_type = EventType.POSITION_CLOSED


@dataclass(slots=True)
class TradeRecordedEvent(Event):
    """Trade recorded in journal."""
    trade_id: UUID = field(default_factory=uuid4)
    symbol: str = ""
    entry_time_ns: int = 0
    exit_time_ns: int = 0
    side: Side = Side.BUY
    entry_price: float = 0.0
    exit_price: float = 0.0
    quantity: float = 0.0
    pnl: float = 0.0
    commission: float = 0.0
    setup_type: str = ""
    pattern_confidence: float = 0.0
    reasoning: str = ""
    risk_metrics: dict[str, float] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    event_type: EventType = field(default=EventType.TRADE_RECORDED, init=False)
    
    def __post_init__(self):
        self.event_type = EventType.TRADE_RECORDED


@dataclass(slots=True)
class ErrorEvent(Event):
    """System error event."""
    error_type: str = ""
    message: str = ""
    traceback: str = ""
    severity: str = "error"  # error, warning, info
    module: str = ""
    recoverable: bool = True
    event_type: EventType = field(default=EventType.ERROR, init=False)
    
    def __post_init__(self):
        self.event_type = EventType.ERROR


@dataclass(slots=True)
class HeartbeatEvent(Event):
    """Module heartbeat."""
    module: str = ""
    status: str = "healthy"  # healthy, degraded, unhealthy
    metrics: dict[str, float] = field(default_factory=dict)
    event_type: EventType = field(default=EventType.HEARTBEAT, init=False)
    
    def __post_init__(self):
        self.event_type = EventType.HEARTBEAT


# Type alias for event handlers
EventHandler = Generic[T]