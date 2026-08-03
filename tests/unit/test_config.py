"""
Tests for core/config.py
"""

import os
import tempfile
from pathlib import Path

import pytest

from core.config import (
    AppSettings, MarketHoursSettings, ScannerSettings, MarketDataSettings,
    ChartBuilderSettings, TechnicalIndicatorsSettings, VisionEngineSettings,
    MemoryEngineSettings, ReasoningEngineSettings, RiskEngineSettings,
    ExecutionEngineSettings, JournalSettings, LearningSettings,
    DashboardSettings, LoggingSettings, ModelManagerSettings, DatabaseSettings,
    get_settings, set_settings, reset_settings, get_cached_settings
)


class TestMarketHoursSettings:
    """Test market hours settings."""
    
    def test_defaults(self):
        settings = MarketHoursSettings()
        assert settings.pre_market == "04:00"
        assert settings.regular_open == "09:30"
        assert settings.regular_close == "16:00"
        assert settings.post_market == "20:00"
        assert settings.learning_window == "16:00-08:00"
    
    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("TRADINGOS_MARKET_HOURS_PRE_MARKET", "05:00")
        settings = MarketHoursSettings()
        assert settings.pre_market == "05:00"


class TestScannerSettings:
    """Test scanner settings."""
    
    def test_defaults(self):
        settings = ScannerSettings()
        assert settings.enabled is True
        assert settings.max_symbols == 500
        assert settings.scan_interval_ms == 1000
        assert len(settings.filters) == 3


class TestMarketDataSettings:
    """Test market data settings."""
    
    def test_defaults(self):
        settings = MarketDataSettings()
        assert settings.primary == "polygon"
        assert settings.fallback == "alpaca"
        assert settings.websocket_reconnect_interval == 5


class TestAppSettings:
    """Test main application settings."""
    
    def test_defaults(self):
        settings = AppSettings()
        assert settings.name == "TradingOS"
        assert settings.environment == "development"
        assert settings.timezone == "America/New_York"
        assert settings.log_level == "INFO"
        
        # Check nested settings exist
        assert settings.market_hours is not None
        assert settings.scanner is not None
        assert settings.market_data is not None
        assert settings.chart_builder is not None
        assert settings.technical_indicators is not None
        assert settings.vision_engine is not None
        assert settings.memory_engine is not None
        assert settings.reasoning_engine is not None
        assert settings.risk_engine is not None
        assert settings.execution_engine is not None
        assert settings.journal is not None
        assert settings.learning is not None
        assert settings.dashboard is not None
        assert settings.logging is not None
        assert settings.model_manager is not None
        assert settings.databases is not None
    
    def test_environment_validation(self):
        with pytest.raises(ValueError):
            AppSettings(environment="invalid")
        
        # Valid environments
        for env in ["development", "paper", "live"]:
            settings = AppSettings(environment=env)
            assert settings.environment == env
    
    def test_yaml_loading(self, tmp_path):
        """Test loading settings from YAML file."""
        yaml_content = """
app:
  name: "TestTradingOS"
  environment: "paper"
  timezone: "America/New_York"

market_hours:
  pre_market: "04:00"
  regular_open: "09:30"
  regular_close: "16:00"

scanner:
  enabled: true
  max_symbols: 100
  scan_interval_ms: 500

risk_engine:
  max_position_pct: 0.1
  max_daily_loss: 0.02
"""
        yaml_file = tmp_path / "settings.yaml"
        yaml_file.write_text(yaml_content)
        
        # This test would require a custom loader - Pydantic Settings
        # loads from env vars, not YAML directly. We'd need a YAML loader
        # or use pydantic-yaml. For now, test env var loading.
    
    def test_env_var_loading(self, monkeypatch):
        """Test loading settings from environment variables."""
        monkeypatch.setenv("TRADINGOS_NAME", "EnvTradingOS")
        monkeypatch.setenv("TRADINGOS_ENVIRONMENT", "paper")
        monkeypatch.setenv("TRADINGOS_SCANNER_MAX_SYMBOLS", "200")
        monkeypatch.setenv("TRADINGOS_RISK_MAX_POSITION_PCT", "0.03")
        
        settings = AppSettings()
        assert settings.name == "EnvTradingOS"
        assert settings.environment == "paper"
        assert settings.scanner.max_symbols == 200
        assert settings.risk_engine.max_position_pct == 0.03


class TestSettingsSingleton:
    """Test global settings singleton."""
    
    def test_get_settings(self):
        reset_settings()
        settings = get_settings()
        assert isinstance(settings, AppSettings)
        assert settings.name == "TradingOS"
    
    def test_singleton_behavior(self):
        reset_settings()
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2
    
    def test_set_settings(self):
        reset_settings()
        custom = AppSettings(name="CustomTradingOS")
        set_settings(custom)
        assert get_settings() is custom
    
    def test_reset_settings(self):
        reset_settings()
        get_settings()  # Creates default
        reset_settings()
        # After reset, next call creates new instance
        s = get_settings()
        assert s.name == "TradingOS"
    
    def test_cached_settings(self):
        reset_settings()
        s1 = get_cached_settings()
        s2 = get_cached_settings()
        assert s1 is s2


class TestModelManagerSettings:
    """Test model manager settings."""
    
    def test_defaults(self):
        settings = ModelManagerSettings()
        assert settings.device == "cuda"
        assert settings.gpu_memory_fraction == 0.85
        assert "vision" in settings.models
        assert "reasoning" in settings.models
        assert "embedding" in settings.models
        assert "speech" in settings.models


class TestDatabaseSettings:
    """Test database settings."""
    
    def test_defaults(self):
        settings = DatabaseSettings()
        assert settings.duckdb_path == "data/tradingos.duckdb"
        assert settings.duckdb_memory_limit == "4GB"
        assert settings.sqlite_path == "data/tradingos.db"
        assert settings.qdrant_path == "data/qdrant"
        assert settings.qdrant_port == 6333


if __name__ == "__main__":
    pytest.main([__file__, "-v"])