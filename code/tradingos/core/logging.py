"""TradingOS Structured Logging."""

import sys
import uuid
from contextvars import ContextVar
from typing import Any, Dict, Optional
import structlog
import orjson
from structlog.types import EventDict, Processor

from tradingos.core.config import get_config, LoggingConfig


# Context variable for trace ID propagation
trace_id_var: ContextVar[Optional[str]] = ContextVar("trace_id", default=None)


def get_trace_id() -> str:
    """Get current trace ID, generate if not set."""
    trace_id = trace_id_var.get()
    if trace_id is None:
        trace_id = str(uuid.uuid4())[:8]
        trace_id_var.set(trace_id)
    return trace_id


def set_trace_id(trace_id: str) -> None:
    """Set trace ID for current context."""
    trace_id_var.set(trace_id)


def clear_trace_id() -> None:
    """Clear trace ID from current context."""
    trace_id_var.set(None)


def add_trace_id(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Add trace ID to log event."""
    trace_id = get_trace_id()
    if trace_id:
        event_dict["trace_id"] = trace_id
    return event_dict


def add_timestamp(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Add ISO timestamp to log event."""
    from datetime import datetime, timezone
    event_dict["timestamp"] = datetime.now(timezone.utc).isoformat()
    return event_dict


def add_level(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Add log level to event dict."""
    event_dict["level"] = method_name.upper()
    return event_dict


def rename_event_key(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Rename 'event' key to 'message'."""
    if "event" in event_dict:
        event_dict["message"] = event_dict.pop("event")
    return event_dict


def drop_color_message_key(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Drop color_message key if present."""
    event_dict.pop("color_message", None)
    return event_dict


def json_renderer(logger: Any, method_name: str, event_dict: EventDict) -> str:
    """Render event dict as JSON using orjson."""
    return orjson.dumps(event_dict, option=orjson.OPT_APPEND_NEWLINE).decode()


def console_renderer(logger: Any, method_name: str, event_dict: EventDict) -> str:
    """Render event dict for console output."""
    import structlog.dev
    return structlog.dev.ConsoleRenderer(colors=True)(logger, method_name, event_dict)


def setup_logging(config: Optional[LoggingConfig] = None) -> None:
    """Configure structlog for TradingOS."""
    if config is None:
        config = get_config().logging

    # Shared processors
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        add_trace_id,
        add_timestamp,
        add_level,
        rename_event_key,
        drop_color_message_key,
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    # Configure structlog
    structlog.configure(
        processors=shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    import logging
    
    # File handler (JSON)
    file_handler = logging.FileHandler(config.json_file)
    file_handler.setFormatter(structlog.stdlib.ProcessorFormatter(
        processor=json_renderer,
        foreign_pre_chain=shared_processors,
    ))
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    if config.console:
        console_handler.setFormatter(structlog.stdlib.ProcessorFormatter(
            processor=console_renderer,
            foreign_pre_chain=shared_processors,
        ))
    else:
        console_handler.setFormatter(structlog.stdlib.ProcessorFormatter(
            processor=json_renderer,
            foreign_pre_chain=shared_processors,
        ))

    root_logger = logging.getLogger()
    root_logger.handlers = []
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    root_logger.setLevel(getattr(logging, config.level.upper()))

    # Suppress noisy loggers
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("numba").setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)


class TraceContext:
    """Context manager for trace ID propagation."""
    
    def __init__(self, trace_id: Optional[str] = None):
        self.trace_id = trace_id or str(uuid.uuid4())[:8]
        self.previous = None
    
    def __enter__(self) -> str:
        self.previous = trace_id_var.get()
        trace_id_var.set(self.trace_id)
        return self.trace_id
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.previous is not None:
            trace_id_var.set(self.previous)
        else:
            clear_trace_id()


def log_with_context(logger: structlog.stdlib.BoundLogger, 
                     level: str, 
                     message: str, 
                     **kwargs) -> None:
    """Log with automatic trace ID and context."""
    getattr(logger, level)(message, **kwargs)


# Convenience functions for common log patterns
def log_event_received(logger: structlog.stdlib.BoundLogger, 
                       event_type: str, 
                       trace_id: str,
                       **extra) -> None:
    """Log event received."""
    logger.info("event_received", event_type=event_type, trace_id=trace_id, **extra)


def log_event_published(logger: structlog.stdlib.BoundLogger, 
                        event_type: str, 
                        trace_id: str,
                        **extra) -> None:
    """Log event published."""
    logger.info("event_published", event_type=event_type, trace_id=trace_id, **extra)


def log_stage_start(logger: structlog.stdlib.BoundLogger, 
                    stage: str, 
                    trace_id: str,
                    **extra) -> None:
    """Log pipeline stage start."""
    logger.info("stage_start", stage=stage, trace_id=trace_id, **extra)


def log_stage_complete(logger: structlog.stdlib.BoundLogger, 
                       stage: str, 
                       trace_id: str,
                       duration_ms: float,
                       **extra) -> None:
    """Log pipeline stage completion."""
    logger.info("stage_complete", stage=stage, trace_id=trace_id, duration_ms=duration_ms, **extra)


def log_stage_error(logger: structlog.stdlib.BoundLogger, 
                    stage: str, 
                    trace_id: str,
                    error: Exception,
                    **extra) -> None:
    """Log pipeline stage error."""
    logger.error("stage_error", stage=stage, trace_id=trace_id, 
                 error_type=type(error).__name__, error_message=str(error), **extra)


def log_metric(logger: structlog.stdlib.BoundLogger, 
               name: str, 
               value: float, 
               trace_id: Optional[str] = None,
               **tags) -> None:
    """Log a metric value."""
    logger.info("metric", metric_name=name, metric_value=value, trace_id=trace_id or get_trace_id(), **tags)