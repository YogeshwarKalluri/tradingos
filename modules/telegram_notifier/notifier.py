"""
Telegram Notification Module for TradingOS
Sends trade alerts, system status updates, and trade notifications via Telegram bot.
"""

from __future__ import annotations
import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import aiohttp
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

from core.config import get_settings
from core.event_bus import EventBus, get_event_bus
from core.types import Event, EventType, Side, Action, OrderStatus, PatternType


logger = logging.getLogger(__name__)


class NotificationPriority(str, Enum):
    """Notification priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationType(str, Enum):
    """Types of notifications."""
    TRADE_EXECUTED = "trade_executed"
    TRADE_FAILED = "trade_failed"
    PATTERN_DETECTED = "pattern_detected"
    RISK_WARNING = "risk_warning"
    SYSTEM_START = "system_start"
    SYSTEM_STOP = "system_stop"
    SYSTEM_ERROR = "system_error"
    DAILY_REPORT = "daily_report"
    RISK_LIMIT_BREACH = "risk_limit_breach"
    SCANNER_ALERT = "scanner_alert"
    POSITION_UPDATE = "position_update"
    MARKET_OPEN = "market_open"
    MARKET_CLOSE = "market_close"


@dataclass(slots=True)
class TelegramMessage:
    """Telegram message structure."""
    text: str
    parse_mode: str = "HTML"
    disable_web_page_preview: bool = True
    disable_notification: bool = False
    reply_to_message_id: Optional[int] = None


class TelegramConfig(BaseSettings):
    """Telegram bot configuration."""
    bot_token: str = Field(default="8974457297:AAF0P6nVQum8_10vkMr9BV_PA0AF5NBOQZ4", description="Telegram bot API token")
    chat_id: int = Field(default=0, description="Target chat ID for notifications")
    enabled: bool = Field(default=True, description="Enable/disable notifications")
    default_priority: NotificationPriority = Field(default=NotificationPriority.NORMAL)
    rate_limit_per_minute: int = Field(default=20, description="Max messages per minute")
    timeout_seconds: int = Field(default=10, description="HTTP request timeout")


class TelegramNotifier:
    """
    Telegram notification service for TradingOS.
    
    Features:
    - Async message sending with rate limiting
    - Multiple priority levels
    - Message formatting for different event types
    - Automatic retry with exponential backoff
    - Rate limiting (Telegram API limits)
    """
    
    def __init__(self, config: Optional[TelegramConfig] = None):
        self._config = config or self._load_config()
        self._session: Optional[aiohttp.ClientSession] = None
        self._rate_limit_semaphore: Optional[asyncio.Semaphore] = None
        self._last_message_time: float = 0
        self._message_count: int = 0
        self._window_start: float = 0
        self._enabled = self._config.enabled if self._config else False
        
    def _load_config(self) -> TelegramConfig:
        """Load configuration from settings."""
        settings = get_settings()
        return TelegramConfig(
            bot_token=settings.telegram_bot_token,
            chat_id=settings.telegram_chat_id,
            enabled=settings.telegram_enabled,
        )
    
    async def start(self) -> None:
        """Initialize the notifier."""
        if not self._enabled:
            logger.info("Telegram notifications disabled")
            return
            
        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self._config.timeout_seconds)
        )
        self._rate_limit_semaphore = asyncio.Semaphore(self._config.rate_limit_per_minute)
        self._window_start = asyncio.get_event_loop().time()
        
        # Test connection
        await self._test_connection()
        logger.info("Telegram notifier started")
    
    async def stop(self) -> None:
        """Stop the notifier."""
        if self._session:
            await self._session.close()
            self._session = None
        logger.info("Telegram notifier stopped")
    
    async def _test_connection(self) -> bool:
        """Test bot connection."""
        try:
            url = f"https://api.telegram.org/bot{self._config.bot_token}/getMe"
            async with self._session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    logger.info(f"Telegram bot connected: @{data.get('result', {}).get('username', 'unknown')}")
                    return True
                else:
                    logger.error(f"Telegram connection test failed: {resp.status}")
                    return False
        except Exception as e:
            logger.error(f"Telegram connection error: {e}")
            return False
    
    async def send_message(self, message: TelegramMessage) -> bool:
        """Send a message to Telegram."""
        if not self._enabled or not self._session:
            return False
        
        await self._rate_limit_semaphore.acquire()
        try:
            return await self._send_with_retry(message)
        finally:
            self._rate_limit_semaphore.release()
    
    async def _send_with_retry(self, message: TelegramMessage, max_retries: int = 3) -> bool:
        """Send message with exponential backoff retry."""
        url = f"https://api.telegram.org/bot{self._config.bot_token}/sendMessage"
        
        payload = {
            "chat_id": self._config.chat_id,
            "text": message.text,
            "parse_mode": message.parse_mode,
            "disable_web_page_preview": message.disable_web_page_preview,
            "disable_notification": message.disable_notification,
        }
        
        if message.reply_to_message_id:
            payload["reply_to_message_id"] = message.reply_to_message_id
        
        for attempt in range(max_retries):
            try:
                async with self._session.post(url, json=payload) as resp:
                    if resp.status == 200:
                        return True
                    elif resp.status == 429:
                        # Rate limited - wait and retry
                        retry_after = int(resp.headers.get("Retry-After", 1))
                        logger.warning(f"Telegram rate limited, waiting {retry_after}s")
                        await asyncio.sleep(retry_after)
                        continue
                    else:
                        error_text = await resp.text()
                        logger.error(f"Telegram send failed (attempt {attempt + 1}): {resp.status} - {error_text}")
            except asyncio.TimeoutError:
                logger.warning(f"Telegram timeout (attempt {attempt + 1})")
            except Exception as e:
                logger.error(f"Telegram send error (attempt {attempt + 1}): {e}")
            
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
        return False
    
    def _format_trade_message(self, event: Event) -> str:
        """Format trade execution message."""
        if event.event_type == EventType.ORDER_FILLED:
            side_emoji = "🟢" if event.side == Side.BUY else "🔴"
            return (
                f"{side_emoji} <b>TRADE EXECUTED</b>\n\n"
                f"Symbol: <code>{event.symbol}</code>\n"
                f"Side: {event.side.value.upper()}\n"
                f"Quantity: <code>{event.quantity}</code>\n"
                f"Price: <code>${event.fill_price:.2f}</code>\n"
                f"Time: {datetime.fromtimestamp(event.timestamp_ns / 1e9).strftime('%H:%M:%S')}\n"
                f"Order ID: <code>{event.order_id}</code>"
            )
        return ""
    
    def _format_risk_message(self, event: Event) -> str:
        """Format risk warning message."""
        if event.event_type == EventType.RISK_REJECTED:
            return (
                f"🛑 <b>RISK REJECTED</b>\n\n"
                f"Symbol: <code>{event.symbol}</code>\n"
                f"Reason: {event.reason}\n"
                f"Time: {datetime.fromtimestamp(event.timestamp_ns / 1e9).strftime('%H:%M:%S')}"
            )
        elif event.event_type == EventType.RISK_WARNING:
            return (
                f"⚠️ <b>RISK WARNING</b>\n\n"
                f"Message: {event.message}\n"
                f"Module: {event.module}\n"
                f"Time: {datetime.fromtimestamp(event.timestamp_ns / 1e9).strftime('%H:%M:%S')}"
            )
        return ""
    
    def _format_pattern_message(self, event: Event) -> str:
        """Format pattern detection message."""
        if event.event_type == EventType.PATTERN_DETECTED:
            pattern_emoji = "📈" if "bull" in event.pattern_type.value.lower() else "📉"
            return (
                f"{pattern_emoji} <b>PATTERN DETECTED</b>\n\n"
                f"Symbol: <code>{event.symbol}</code>\n"
                f"Pattern: <b>{event.pattern_type.value.replace('_', ' ').title()}</b>\n"
                f"Confidence: <code>{event.confidence:.1%}</code>\n"
                f"Timeframe: <code>{event.timeframe.value}</code>\n"
                f"Time: {datetime.fromtimestamp(event.timestamp_ns / 1e9).strftime('%H:%M:%S')}"
            )
        return ""
    
    def _format_system_message(self, event: Event) -> str:
        """Format system message."""
        if event.event_type == EventType.SYSTEM_START:
            return f"🚀 <b>TradingOS STARTED</b>\n\nTime: {datetime.fromtimestamp(event.timestamp_ns / 1e9).strftime('%Y-%m-%d %H:%M:%S')}"
        elif event.event_type == EventType.SYSTEM_STOP:
            return f"🛑 <b>TradingOS STOPPED</b>\n\nTime: {datetime.fromtimestamp(event.timestamp_ns / 1e9).strftime('%Y-%m-%d %H:%M:%S')}"
        elif event.event_type == EventType.SYSTEM_ERROR:
            return (
                f"💥 <b>SYSTEM ERROR</b>\n\n"
                f"Type: {event.error_type}\n"
                f"Message: {event.message}\n"
                f"Module: {event.module}\n"
                f"Severity: {event.severity}\n"
                f"Time: {datetime.fromtimestamp(event.timestamp_ns / 1e9).strftime('%H:%M:%S')}"
            )
        elif event.event_type == EventType.MARKET_OPEN:
            return f"🔔 <b>MARKET OPEN</b>\n\nTrading session started at 9:30 AM ET"
        elif event.event_type == EventType.MARKET_CLOSE:
            return f"🔔 <b>MARKET CLOSED</b>\n\nTrading session ended at 4:00 PM ET"
        return ""
    
    def format_event(self, event: Event) -> Optional[TelegramMessage]:
        """Format an event into a Telegram message."""
        text = ""
        
        if event.event_type in (EventType.ORDER_FILLED,):
            text = self._format_trade_message(event)
        elif event.event_type in (EventType.RISK_REJECTED, EventType.RISK_WARNING):
            text = self._format_risk_message(event)
        elif event.event_type in (EventType.PATTERN_DETECTED,):
            text = self._format_pattern_message(event)
        elif event.event_type in (EventType.SYSTEM_START, EventType.SYSTEM_STOP, EventType.SYSTEM_ERROR, EventType.MARKET_OPEN, EventType.MARKET_CLOSE):
            text = self._format_system_message(event)
        else:
            return None
        
        if not text:
            return None
        
        return TelegramMessage(
            text=text,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
    
    async def send_event(self, event: Event) -> bool:
        """Send formatted event notification."""
        message = self.format_event(event)
        if message:
            return await self.send_message(message)
        return False
    
    async def send_custom(
        self,
        text: str,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        parse_mode: str = "HTML",
    ) -> bool:
        """Send a custom notification."""
        if not self._enabled:
            return False
        
        message = TelegramMessage(
            text=text,
            parse_mode=parse_mode,
        )
        return await self.send_message(message)
    
    async def send_daily_report(self, report: Dict[str, Any]) -> bool:
        """Send formatted daily report."""
        text = self._format_daily_report(report)
        return await self.send_custom(text, priority=NotificationPriority.NORMAL)
    
    def _format_daily_report(self, report: Dict[str, Any]) -> str:
        """Format daily trading report."""
        date = report.get("date", datetime.now().strftime("%Y-%m-%d"))
        total_trades = report.get("total_trades", 0)
        winning_trades = report.get("winning_trades", 0)
        losing_trades = report.get("losing_trades", 0)
        total_pnl = report.get("total_pnl", 0.0)
        win_rate = report.get("win_rate", 0.0)
        max_drawdown = report.get("max_drawdown", 0.0)
        sharpe = report.get("sharpe_ratio", 0.0)
        
        pnl_emoji = "🟢" if total_pnl >= 0 else "🔴"
        
        return (
            f"📊 <b>DAILY REPORT - {date}</b>\n\n"
            f"{pnl_emoji} Total P&L: <b>${total_pnl:,.2f}</b>\n"
            f"📈 Total Trades: <b>{total_trades}</b>\n"
            f"✅ Wins: <b>{winning_trades}</b> | ❌ Losses: <b>{losing_trades}</b>\n"
            f"🎯 Win Rate: <b>{win_rate:.1%}</b>\n"
            f"📉 Max Drawdown: <b>{max_drawdown:.2%}</b>\n"
            f"⚡ Sharpe Ratio: <b>{sharpe:.2f}</b>"
        )


# Global notifier instance
_telegram_notifier: Optional[TelegramNotifier] = None


def get_telegram_notifier() -> TelegramNotifier:
    """Get or create the global telegram notifier."""
    global _telegram_notifier
    if _telegram_notifier is None:
        _telegram_notifier = TelegramNotifier()
    return _telegram_notifier


def set_telegram_notifier(notifier: TelegramNotifier) -> None:
    """Set the global telegram notifier (for testing)."""
    global _telegram_notifier
    _telegram_notifier = notifier


async def shutdown_telegram_notifier() -> None:
    """Shutdown the global telegram notifier."""
    global _telegram_notifier
    if _telegram_notifier:
        await _telegram_notifier.stop()
        _telegram_notifier = None


# Convenience functions
async def notify_trade_filled(event: Event) -> bool:
    """Send trade filled notification."""
    notifier = get_telegram_notifier()
    return await notifier.send_event(event)


async def notify_risk_rejected(event: Event) -> bool:
    """Send risk rejected notification."""
    notifier = get_telegram_notifier()
    return await notifier.send_event(event)


async def notify_pattern_detected(event: Event) -> bool:
    """Send pattern detected notification."""
    notifier = get_telegram_notifier()
    return await notifier.send_event(event)


async def notify_system_event(event: Event) -> bool:
    """Send system event notification."""
    notifier = get_telegram_notifier()
    return await notifier.send_event(event)


async def notify_custom(text: str, priority: NotificationPriority = NotificationPriority.NORMAL) -> bool:
    """Send custom notification."""
    notifier = get_telegram_notifier()
    return await notifier.send_custom(text, priority)