"""TradingOS Configuration Management."""

from pathlib import Path
from typing import Any, Dict, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
import yaml


class AppConfig(BaseSettings):
    """Application configuration."""
    name: str = "TradingOS"
    version: str = "0.1.0"
    timezone: str = "America/New_York"
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_prefix="TRADINGOS_APP_")


class MarketHoursConfig(BaseSettings):
    """Market hours configuration."""
    pre_market_start: str = "08:30"
    market_open: str = "09:30"
    market_close: str = "16:00"
    post_market_end: str = "16:30"
    timezone: str = "America/New_York"

    model_config = SettingsConfigDict(env_prefix="TRADINGOS_MARKET_")


class EventBusConfig(BaseSettings):
    """Event bus configuration."""
    queue_size: int = 10000
    worker_count: int = 4
    batch_timeout_ms: int = 10

    model_config = SettingsConfigDict(env_prefix="TRADINGOS_EVENTS_")


class ModelManagerConfig(BaseSettings):
    """Model manager configuration."""
    vram_budget_mb: int = 14336
    headroom_mb: int = 2048
    warmup_runs: int = 3
    health_check_interval_sec: int = 60
    auto_recover: bool = True
    market_hours_models: list[str] = Field(default_factory=list)
    after_hours_models: list[str] = Field(default_factory=list)

    model_config = SettingsConfigDict(env_prefix="TRADINGOS_MODELS_")


class ScannerConfig(BaseSettings):
    """Scanner module configuration."""
    deduplication_window_minutes: int = 5
    priority_weights: Dict[str, float] = Field(default_factory=dict)

    model_config = SettingsConfigDict(env_prefix="TRADINGOS_SCANNER_")


class MarketDataConfig(BaseSettings):
    """Market data module configuration."""
    duckdb_path: str = "data/market.duckdb"
    cache_ttl_seconds: int = 1

    model_config = SettingsConfigDict(env_prefix="TRADINGOS_MARKET_DATA_")


class ChartsConfig(BaseSettings):
    """Chart engine configuration."""
    timeframes: list[str] = Field(default_factory=lambda: ["1m", "5m", "15m", "1d"])
    output_shape: list[int] = Field(default_factory=lambda: [4, 256, 256, 3])

    model_config = SettingsConfigDict(env_prefix="TRADINGOS_CHARTS_")


class IndicatorsConfig(BaseSettings):
    """Indicators configuration."""
    vwap: bool = True
    ema_periods: list[int] = Field(default_factory=lambda: [9, 20, 50, 200])
    atr_period: int = 14
    rsi_period: int = 14
    rvol_lookback_days: int = 20

    model_config = SettingsConfigDict(env_prefix="TRADINGOS_INDICATORS_")


class VisionConfig(BaseSettings):
    """Vision engine configuration."""
    pattern_classes: list[str] = Field(default_factory=list)
    confidence_threshold: float = 0.65
    nms_iou_threshold: float = 0.45

    model_config = SettingsConfigDict(env_prefix="TRADINGOS_VISION_")


class MemoryConfig(BaseSettings):
    """Memory engine configuration."""
    qdrant_path: str = "data/qdrant"
    collection_name: str = "trade_embeddings"
    vector_size: int = 768
    distance: str = "Cosine"
    duckdb_path: str = "data/trades.duckdb"

    model_config = SettingsConfigDict(env_prefix="TRADINGOS_MEMORY_")


class ReasoningConfig(BaseSettings):
    """Reasoning engine configuration."""
    evidence_weights: Dict[str, float] = Field(default_factory=dict)
    min_confidence: float = 0.55

    model_config = SettingsConfigDict(env_prefix="TRADINGOS_REASONING_")


class RiskConfig(BaseSettings):
    """Risk engine configuration."""
    hard_rules: Dict[str, Any] = Field(default_factory=dict)
    dynamic_rules: Dict[str, Any] = Field(default_factory=dict)

    model_config = SettingsConfigDict(env_prefix="TRADINGOS_RISK_")


class ExecutionConfig(BaseSettings):
    """Execution engine configuration."""
    mode: str = "paper"

    model_config = SettingsConfigDict(env_prefix="TRADINGOS_EXECUTION_")


class JournalConfig(BaseSettings):
    """Journal module configuration."""
    jsonl_path: str = "data/journal/decisions"
    duckdb_path: str = "data/journal.duckdb"
    batch_size: int = 100
    flush_interval_sec: int = 5

    model_config = SettingsConfigDict(env_prefix="TRADINGOS_JOURNAL_")


class VideoConfig(BaseSettings):
    """Video pipeline configuration."""
    inbox_path: str = "knowledge/ross_videos/inbox"
    processing_path: str = "knowledge/ross_videos/processing"
    done_path: str = "knowledge/ross_videos/done"
    failed_path: str = "knowledge/ross_videos/failed"
    charts_path: str = "knowledge/ross_videos/charts"
    review_queue_path: str = "knowledge/ross_videos/review_queue"
    frame_rate: int = 1

    model_config = SettingsConfigDict(env_prefix="TRADINGOS_VIDEO_")


class DashboardConfig(BaseSettings):
    """Dashboard configuration."""
    host: str = "0.0.0.0"
    port: int = 8080
    websocket_ping_interval: int = 30
    update_batch_ms: int = 100

    model_config = SettingsConfigDict(env_prefix="TRADINGOS_DASHBOARD_")


class HealthConfig(BaseSettings):
    """Health monitoring configuration."""
    port: int = 8080
    path: str = "/health"
    metrics_path: str = "/metrics"

    model_config = SettingsConfigDict(env_prefix="TRADINGOS_HEALTH_")


class LoggingConfig(BaseSettings):
    """Logging configuration."""
    level: str = "INFO"
    json_file: str = "logs/tradingos.jsonl"
    console: bool = True
    trace_id_header: str = "x-trace-id"

    model_config = SettingsConfigDict(env_prefix="TRADINGOS_LOGGING_")


class Config:
    """Main configuration container."""

    def __init__(self, env: str = "development"):
        self.env = env
        self._load_configs()

    def _load_configs(self):
        """Load configuration from YAML files."""
        base_path = Path(__file__).parent.parent.parent / "config"
        
        # Load base config
        with open(base_path / "base.yaml") as f:
            base = yaml.safe_load(f)
        
        # Load environment-specific config
        env_file = base_path / f"{self.env}.yaml"
        env_config = {}
        if env_file.exists():
            with open(env_file) as f:
                env_config = yaml.safe_load(f) or {}
        
        # Merge configs (env overrides base)
        merged = self._deep_merge(base, env_config)
        
        # Initialize sub-configs
        self.app = AppConfig(**merged.get("app", {}))
        self.market_hours = MarketHoursConfig(**merged.get("market_hours", {}))
        self.event_bus = EventBusConfig(**merged.get("event_bus", {}))
        self.model_manager = ModelManagerConfig(**merged.get("model_manager", {}))
        self.scanner = ScannerConfig(**merged.get("scanner", {}))
        self.market_data = MarketDataConfig(**merged.get("market_data", {}))
        self.charts = ChartsConfig(**merged.get("charts", {}))
        self.indicators = IndicatorsConfig(**merged.get("indicators", {}))
        self.vision = VisionConfig(**merged.get("vision", {}))
        self.memory = MemoryConfig(**merged.get("memory", {}))
        self.reasoning = ReasoningConfig(**merged.get("reasoning", {}))
        self.risk = RiskConfig(**merged.get("risk", {}))
        self.execution = ExecutionConfig(**merged.get("execution", {}))
        self.journal = JournalConfig(**merged.get("journal", {}))
        self.video = VideoConfig(**merged.get("video", {}))
        self.dashboard = DashboardConfig(**merged.get("dashboard", {}))
        self.health = HealthConfig(**merged.get("health", {}))
        self.logging = LoggingConfig(**merged.get("logging", {}))

    def _deep_merge(self, base: dict, override: dict) -> dict:
        """Deep merge two dictionaries."""
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result


# Global config instance
_config: Optional[Config] = None


def get_config(env: Optional[str] = None) -> Config:
    """Get global configuration instance."""
    global _config
    if _config is None or (env is not None and _config.env != env):
        _config = Config(env or "development")
    return _config


def reset_config():
    """Reset global configuration (for testing)."""
    global _config
    _config = None