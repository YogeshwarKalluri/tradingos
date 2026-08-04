"""TradingOS - Local AI-Powered Momentum Day Trading Platform."""

__version__ = "0.1.0"
__author__ = "Yogeshwar Kalluri"
__description__ = "Local AI-Powered Momentum Day Trading Platform"

from tradingos.core import (
    get_config,
    setup_logging,
    get_logger,
    get_event_bus,
    get_model_manager,
)

__all__ = [
    "get_config",
    "setup_logging",
    "get_logger",
    "get_event_bus",
    "get_model_manager",
]