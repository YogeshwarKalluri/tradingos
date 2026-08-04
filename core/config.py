"""
Configuration Management for TradingOS
Uses Pydantic Settings for type-safe configuration with YAML + environment variable support.
"""

from __future__ import annotations
from pathlib import Path
from typing import Any
from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from core.types import Timeframe, Side, Action, OrderType, OrderStatus, PatternType, EventType


class MarketHoursSettings(BaseSettings):
    """Market hours configuration."""
    pre_market: str = "04:00"
    regular_open: str = "09:30"
    regular_close: str = "16:00"
    post_market: str = "20:00"
    learning_window: str = "16:00-08:00"
    
    model_config = SettingsConfigDict(env_prefix="TRADINGOS_MARKET_HOURS_")


class ScannerSettings(BaseSettings):
    """Scanner configuration."""
    enabled: bool = True
    max_symbols: int = 500
    scan_interval_ms: int = 1000
    filters: list[dict[str, Any]] = Field(default_factory=lambda: [
        {"name": "volume_spike", "min_relative_volume": 2.0},
        {"name": "price_momentum", "min_change_pct": 1.5},
        {"name": "float_filter", "max_float_m": 50},
    ])
    
    model_config = SettingsConfigDict(env_prefix="TRADINGOS_SCANNER_")


class MarketDataSettings(BaseSettings):
    """Market data provider configuration."""
    primary: str = "polygon"
    fallback: str = "alpaca"
    websocket_reconnect_interval: int = 5
    max_messages_per_second: int = 10000
    cache_max_ticks_per_symbol: int = 100000
    cache_max_bars_per_symbol: int = 10000
    
    model_config = SettingsConfigDict(env_prefix="MARKET_DATA_")


class ChartBuilderSettings(BaseSettings):
    """Chart builder configuration."""
    renderer: str = "cuda"  # cuda, opengl, cpu
    default_timeframes: list[str] = Field(default_factory=lambda: ["1m", "5m", "15m", "1h", "1d"])
    chart_resolution: list[int] = Field(default_factory=lambda: [512, 512])
    gpu_memory_pool_mb: int = 512
    
    model_config = SettingsConfigDict(env_prefix="TRADINGOS_CHART_")


class TechnicalIndicatorsSettings(BaseSettings):
    """Technical indicators configuration."""
    engine: str = "numba_cuda"
    default_indicators: list[str] = Field(default_factory=lambda: [
        "vwap", "ema_9", "ema_20", "rsi_14", "macd", 
        "bollinger_bands", "atr_14"
    ])
    cache_size_mb: int = 1024
    
    model_config = SettingsConfigDict(env_prefix="TRADINGOS_INDICATORS_")


class VisionEngineSettings(BaseSettings):
    """Vision engine configuration."""
    model: str = "yolo_v8_custom"
    confidence_threshold: float = 0.7
    patterns: list[str] = Field(default_factory=lambda: [
        "bull_flag", "bear_flag", "cup_handle", "double_bottom",
        "vwap_reclaim", "opening_range_breakout"
    ])
    batch_size: int = 8
    inference_timeout_ms: int = 50
    
    model_config = SettingsConfigDict(env_prefix="TRADINGOS_VISION_")


class MemoryEngineSettings(BaseSettings):
    """Memory engine configuration."""
    vector_store: str = "qdrant"
    embedding_model: str = "bge-large-en-v1.5"
    top_k: int = 20
    similarity_threshold: float = 0.75
    rerank: bool = True
    
    model_config = SettingsConfigDict(env_prefix="TRADINGOS_MEMORY_")


class ReasoningEngineSettings(BaseSettings):
    """Reasoning engine configuration."""
    model: str = "nemotron-3-ultra"
    max_context_tokens: int = 8192
    temperature: float = 0.1
    evidence_weights: dict[str, float] = Field(default_factory=lambda: {
        "pattern": 0.3,
        "indicators": 0.2,
        "historical": 0.3,
        "volume": 0.2
    })
    
    model_config = SettingsConfigDict(env_prefix="TRADINGOS_REASONING_")


class RiskEngineSettings(BaseSettings):
    """Risk engine configuration."""
    max_position_pct: float = 0.05
    max_portfolio_risk: float = 0.02
    max_daily_loss: float = 0.01
    max_sector_exposure: float = 0.20
    kelly_fraction: float = 0.25
    stop_loss_atr_multiple: float = 2.0
    
    model_config = SettingsConfigDict(env_prefix="TRADINGOS_RISK_")


class ExecutionEngineSettings(BaseSettings):
    """Execution engine configuration."""
    mode: str = "paper"  # paper, live
    paper_starting_capital: float = 100000
    paper_commission_per_share: float = 0.005
    paper_min_commission: float = 1.0
    paper_slippage_bps: int = 5
    live_broker: str = "alpaca"
    live_api_key_env: str = "ALPACA_API_KEY"
    live_secret_env: str = "ALPACA_SECRET"
    
    model_config = SettingsConfigDict(env_prefix="TRADINGOS_EXECUTION_")


class JournalSettings(BaseSettings):
    """Journal configuration."""
    storage: str = "duckdb"
    auto_export: bool = True
    export_format: str = "parquet"
    
    model_config = SettingsConfigDict(env_prefix="TRADINGOS_JOURNAL_")


class LearningSettings(BaseSettings):
    """Learning pipeline configuration."""
    enabled: bool = True
    video_sources: list[str] = Field(default_factory=list)
    model_evaluation_metrics: list[str] = Field(default_factory=lambda: [
        "sharpe", "sortino", "max_drawdown", "win_rate"
    ])
    report_schedule: str = "daily"
    
    model_config = SettingsConfigDict(env_prefix="TRADINGOS_LEARNING_")


class DashboardSettings(BaseSettings):
    """Dashboard configuration."""
    enabled: bool = True
    host: str = "127.0.0.1"
    port: int = 8080
    update_interval_ms: int = 100
    theme: str = "dark"
    
    model_config = SettingsConfigDict(env_prefix="TRADINGOS_DASHBOARD_")


class LoggingSettings(BaseSettings):
    """Logging configuration."""
    level: str = "INFO"
    format: str = "json"
    file: str = "logs/tradingos.log"
    max_size_mb: int = 100
    backup_count: int = 10
    
    model_config = SettingsConfigDict(env_prefix="TRADINGOS_LOGGING_")


class TelegramSettings(BaseSettings):
    """Telegram bot configuration."""
    bot_token: str = "8974457297:AAF0P6nVQum8_10vkMr9BV_PA0AF5NBOQZ4"
    chat_id: int = 0
    enabled: bool = True
    default_priority: str = "normal"
    rate_limit_per_minute: int = 20
    timeout_seconds: int = 10
    
    model_config = SettingsConfigDict(env_prefix="TRADINGOS_TELEGRAM_")


class ModelManagerSettings(BaseSettings):
    """Model manager configuration."""
    device: str = "cuda"
    gpu_memory_fraction: float = 0.85
    models: dict[str, dict[str, Any]] = Field(default_factory=lambda: {
        "vision": {
            "name": "yolo_v8_custom",
            "path": "models/vision/yolo_v8_custom.engine",
            "backend": "tensorrt"
        },
        "reasoning": {
            "name": "nemotron-3-ultra",
            "path": "models/reasoning/nemotron-3-ultra.Q4_K_M.gguf",
            "backend": "llama_cpp",
            "context_size": 8192,
            "gpu_layers": -1
        },
        "embedding": {
            "name": "bge-large-en-v1.5",
            "path": "models/embedding/bge-large-en-v1.5",
            "backend": "onnx"
        },
        "speech": {
            "name": "whisper-large-v3",
            "path": "models/speech/whisper-large-v3",
            "backend": "faster_whisper"
        }
    })
    
    model_config = SettingsConfigDict(env_prefix="TRADINGOS_MODELS_")


class DatabaseSettings(BaseSettings):
    """Database configuration."""
    duckdb_path: str = "data/tradingos.duckdb"
    duckdb_memory_limit: str = "4GB"
    duckdb_threads: int = 8
    sqlite_path: str = "data/tradingos.db"
    qdrant_path: str = "data/qdrant"
    qdrant_port: int = 6333
    qdrant_prefer_grpc: bool = False
    
    model_config = SettingsConfigDict(env_prefix="TRADINGOS_DB_")


class AppSettings(BaseSettings):
    """Main application settings."""
    name: str = "TradingOS"
    environment: str = "development"  # development, paper, live
    timezone: str = "America/New_York"
    log_level: str = "INFO"
    
    # Nested settings
    market_hours: MarketHoursSettings = Field(default_factory=MarketHoursSettings)
    scanner: ScannerSettings = Field(default_factory=ScannerSettings)
    market_data: MarketDataSettings = Field(default_factory=MarketDataSettings)
    chart_builder: ChartBuilderSettings = Field(default_factory=ChartBuilderSettings)
    technical_indicators: TechnicalIndicatorsSettings = Field(default_factory=TechnicalIndicatorsSettings)
    vision_engine: VisionEngineSettings = Field(default_factory=VisionEngineSettings)
    memory_engine: MemoryEngineSettings = Field(default_factory=MemoryEngineSettings)
    reasoning_engine: ReasoningEngineSettings = Field(default_factory=ReasoningEngineSettings)
    risk_engine: RiskEngineSettings = Field(default_factory=RiskEngineSettings)
    execution_engine: ExecutionEngineSettings = Field(default_factory=ExecutionEngineSettings)
    journal: JournalSettings = Field(default_factory=JournalSettings)
    learning: LearningSettings = Field(default_factory=LearningSettings)
    dashboard: DashboardSettings = Field(default_factory=DashboardSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    telegram: TelegramSettings = Field(default_factory=TelegramSettings)
    model_manager: ModelManagerSettings = Field(default_factory=ModelManagerSettings)
    databases: DatabaseSettings = Field(default_factory=DatabaseSettings)
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_nested_delimiter="__",
        env_prefix="TRADINGOS_",
        extra="ignore"
    )
    
    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        if v not in ("development", "paper", "live"):
            raise ValueError("environment must be one of: development, paper, live")
        return v


# Global settings instance
_settings: AppSettings | None = None


def get_settings() -> AppSettings:
    """Get or create the global settings instance."""
    global _settings
    if _settings is None:
        _settings = AppSettings()
    return _settings


def set_settings(settings: AppSettings) -> None:
    """Set the global settings instance (for testing)."""
    global _settings
    _settings = settings


def reset_settings() -> None:
    """Reset the global settings instance."""
    global _settings
    _settings = None


@lru_cache(maxsize=1)
def get_cached_settings() -> AppSettings:
    """Get cached settings instance (for dependency injection)."""
    return get_settings()