"""
Tests for core/types.py
"""

import time
from datetime import datetime
from uuid import UUID

import pytest

from core.types import (
    Action,
    BarEvent,
    ErrorEvent,
    Event,
    EventType,
    HeartbeatEvent,
    OrderFilledEvent,
    OrderStatus,
    OrderSubmittedEvent,
    OrderType,
    PatternDetectedEvent,
    PatternType,
    PositionClosedEvent,
    PositionOpenedEvent,
    RiskApprovedEvent,
    RiskRejectedEvent,
    Side,
    StockDetectedEvent,
    TickEvent,
    Timeframe,
    TradeDecisionEvent,
    TradeRecordedEvent,
)


class TestEnums:
    """Test enum values."""

    def test_timeframe_values(self):
        assert Timeframe.MIN_1 == "1m"
        assert Timeframe.MIN_5 == "5m"
        assert Timeframe.HOUR_1 == "1h"
        assert Timeframe.DAY_1 == "1d"

    def test_side_values(self):
        assert Side.BUY == "buy"
        assert Side.SELL == "sell"

    def test_action_values(self):
        assert Action.BUY == "buy"
        assert Action.SELL == "sell"
        assert Action.HOLD == "hold"

    def test_pattern_type_values(self):
        assert PatternType.BULL_FLAG == "bull_flag"
        assert PatternType.VWAP_RECLAIM == "vwap_reclaim"
        assert PatternType.OPENING_RANGE_BREAKOUT == "opening_range_breakout"


class TestBaseEvent:
    """Test base Event class."""

    def test_event_creation(self):
        event = Event(event_type=EventType.TICK, source="test")
        assert event.event_type == EventType.TICK
        assert event.source == "test"
        assert isinstance(event.timestamp_ns, int)
        assert event.timestamp_ns > 0
        assert isinstance(event.correlation_id, UUID)
        assert isinstance(event.metadata, dict)

    def test_timestamp_properties(self):
        event = Event(event_type=EventType.TICK)
        dt = event.timestamp
        assert isinstance(dt, datetime)
        ms = event.timestamp_ms
        assert isinstance(ms, int)
        assert ms == event.timestamp_ns // 1_000_000


class TestTickEvent:
    """Test TickEvent."""

    def test_tick_event_creation(self):
        tick = TickEvent(
            symbol="AAPL",
            price=150.25,
            size=100,
            bid=150.24,
            ask=150.26,
            exchange="NASDAQ"
        )
        assert tick.symbol == "AAPL"
        assert tick.price == 150.25
        assert tick.event_type == EventType.TICK

    def test_tick_event_defaults(self):
        tick = TickEvent()
        assert tick.symbol == ""
        assert tick.price == 0.0
        assert tick.size == 0


class TestBarEvent:
    """Test BarEvent."""

    def test_bar_event_creation(self):
        bar = BarEvent(
            symbol="AAPL",
            timeframe=Timeframe.MIN_1,
            open=150.0,
            high=151.0,
            low=149.5,
            close=150.5,
            volume=10000,
            vwap=150.25,
        )
        assert bar.symbol == "AAPL"
        assert bar.timeframe == Timeframe.MIN_1
        assert bar.open == 150.0
        assert bar.event_type == EventType.BAR


class TestStockDetectedEvent:
    """Test StockDetectedEvent."""

    def test_stock_detected_creation(self):
        event = StockDetectedEvent(
            symbol="AAPL",
            price=150.25,
            volume=1000000,
            change_pct=2.5,
            relative_volume=3.2,
            scanner_id="momentum_scanner",
            filters_passed=["volume_spike", "price_momentum"]
        )
        assert event.symbol == "AAPL"
        assert event.change_pct == 2.5
        assert event.relative_volume == 3.2
        assert event.scanner_id == "momentum_scanner"
        assert "volume_spike" in event.filters_passed
        assert event.event_type == EventType.STOCK_DETECTED


class TestPatternDetectedEvent:
    """Test PatternDetectedEvent."""

    def test_pattern_detected_creation(self):
        event = PatternDetectedEvent(
            symbol="AAPL",
            pattern_type=PatternType.BULL_FLAG,
            confidence=0.85,
            bounding_box=(100, 100, 200, 150),
            timeframe=Timeframe.MIN_5,
        )
        assert event.pattern_type == PatternType.BULL_FLAG
        assert event.confidence == 0.85
        assert event.bounding_box == (100, 100, 200, 150)
        assert event.timeframe == Timeframe.MIN_5
        assert event.event_type == EventType.PATTERN_DETECTED


class TestTradeDecisionEvent:
    """Test TradeDecisionEvent."""

    def test_trade_decision_creation(self):
        event = TradeDecisionEvent(
            symbol="AAPL",
            action=Action.BUY,
            confidence=0.8,
            reasoning="Strong bull flag with volume confirmation",
            position_size=100,
            entry_price=150.25,
            stop_loss=148.0,
            take_profit=155.0,
            risk_reward=2.0,
        )
        assert event.action == Action.BUY
        assert event.confidence == 0.8
        assert event.position_size == 100
        assert event.risk_reward == 2.0
        assert event.event_type == EventType.TRADE_DECISION


class TestRiskEvents:
    """Test risk approval/rejection events."""

    def test_risk_approved(self):
        decision = TradeDecisionEvent(
            symbol="AAPL", action=Action.BUY, confidence=0.8,
            position_size=100, entry_price=150.0, stop_loss=148.0, take_profit=155.0
        )
        event = RiskApprovedEvent(
            decision=decision,
            approved_size=100,
            risk_metrics={"portfolio_risk": 0.01, "position_risk": 0.005},
            warnings=["High volatility"]
        )
        assert event.approved_size == 100
        assert event.decision == decision
        assert "High volatility" in event.warnings
        assert event.event_type == EventType.RISK_APPROVED

    def test_risk_rejected(self):
        decision = TradeDecisionEvent(
            symbol="AAPL", action=Action.BUY, confidence=0.8,
            position_size=100, entry_price=150.0, stop_loss=148.0, take_profit=155.0
        )
        event = RiskRejectedEvent(
            decision=decision,
            reason="Exceeds max position size",
            risk_metrics={"portfolio_risk": 0.05}
        )
        assert event.reason == "Exceeds max position size"
        assert event.event_type == EventType.RISK_REJECTED


class TestOrderEvents:
    """Test order events."""

    def test_order_submitted(self):
        event = OrderSubmittedEvent(
            order_id=UUID("12345678-1234-5678-1234-567812345678"),
            symbol="AAPL",
            side=Side.BUY,
            order_type=OrderType.LIMIT,
            quantity=100,
            price=150.0,
        )
        assert event.order_id == UUID("12345678-1234-5678-1234-567812345678")
        assert event.side == Side.BUY
        assert event.order_type == OrderType.LIMIT
        assert event.status == OrderStatus.PENDING
        assert event.event_type == EventType.ORDER_SUBMITTED

    def test_order_filled(self):
        event = OrderFilledEvent(
            symbol="AAPL",
            side=Side.BUY,
            quantity=100,
            fill_price=150.10,
            fill_qty=100,
        )
        assert event.fill_price == 150.10
        assert event.fill_qty == 100
        assert event.event_type == EventType.ORDER_FILLED


class TestPositionEvents:
    """Test position events."""

    def test_position_opened(self):
        event = PositionOpenedEvent(
            symbol="AAPL",
            side=Side.BUY,
            quantity=100,
            entry_price=150.0,
            current_price=150.5,
            stop_loss=148.0,
            take_profit=155.0,
        )
        assert event.quantity == 100
        assert event.unrealized_pnl == 0.0  # not calculated yet
        assert event.event_type == EventType.POSITION_OPENED

    def test_position_closed(self):
        event = PositionClosedEvent(
            symbol="AAPL",
            side=Side.BUY,
            quantity=100,
            entry_price=150.0,
            exit_price=153.0,
            exit_reason="take_profit_hit",
        )
        assert event.exit_price == 153.0
        assert event.exit_reason == "take_profit_hit"
        assert event.event_type == EventType.POSITION_CLOSED


class TestTradeRecordedEvent:
    """Test trade journal event."""

    def test_trade_recorded(self):
        event = TradeRecordedEvent(
            symbol="AAPL",
            entry_time_ns=time.time_ns() - 3600_000_000_000,
            exit_time_ns=time.time_ns(),
            side=Side.BUY,
            entry_price=150.0,
            exit_price=153.0,
            quantity=100,
            pnl=300.0,
            commission=1.0,
            setup_type="bull_flag",
            pattern_confidence=0.85,
            reasoning="Strong breakout with volume",
            risk_metrics={"max_drawdown": 0.01},
            tags=["momentum", "breakout"],
        )
        assert event.pnl == 300.0
        assert event.setup_type == "bull_flag"
        assert "momentum" in event.tags
        assert event.event_type == EventType.TRADE_RECORDED


class TestErrorEvent:
    """Test error event."""

    def test_error_event(self):
        event = ErrorEvent(
            error_type="ConnectionError",
            message="Failed to connect to Polygon WebSocket",
            traceback="...",
            severity="error",
            module="market_data",
            recoverable=True,
        )
        assert event.error_type == "ConnectionError"
        assert event.severity == "error"
        assert event.module == "market_data"
        assert event.recoverable is True
        assert event.event_type == EventType.ERROR


class TestHeartbeatEvent:
    """Test heartbeat event."""

    def test_heartbeat(self):
        event = HeartbeatEvent(
            module="scanner",
            status="healthy",
            metrics={"stocks_scanned": 500, "latency_ms": 5.2},
        )
        assert event.module == "scanner"
        assert event.status == "healthy"
        assert event.metrics["stocks_scanned"] == 500
        assert event.event_type == EventType.HEARTBEAT


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
