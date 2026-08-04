"""Tests for TradingOS Core Configuration."""


import pytest
from tradingos.core.config import get_config, reset_config


class TestConfig:
    """Test configuration loading."""

    def test_base_config_loads(self):
        """Test base configuration loads correctly."""
        reset_config()
        config = get_config("development")

        assert config.app.name == "TradingOS"
        assert config.app.version == "0.1.0"
        assert config.market_hours.market_open == "09:30"
        assert config.market_hours.market_close == "16:00"

    def test_development_overrides(self):
        """Test development environment overrides."""
        reset_config()
        config = get_config("development")

        assert config.app.log_level == "DEBUG"
        assert config.logging.level == "DEBUG"
        assert config.model_manager.market_hours_models == []

    def test_production_overrides(self):
        """Test production environment overrides."""
        reset_config()
        config = get_config("production")

        assert config.app.log_level == "INFO"
        assert config.logging.console is False
        assert len(config.model_manager.market_hours_models) == 5

    def test_config_singleton(self):
        """Test config is singleton per environment."""
        reset_config()
        config1 = get_config("development")
        config2 = get_config("development")

        assert config1 is config2

    def test_config_reset(self):
        """Test config reset creates new instance."""
        reset_config()
        config1 = get_config("development")
        reset_config()
        config2 = get_config("development")

        assert config1 is not config2


class TestConfigValidation:
    """Test configuration validation."""

    def test_vram_budget_positive(self):
        """Test VRAM budget is positive."""
        reset_config()
        config = get_config("development")
        assert config.model_manager.vram_budget_mb > 0

    def test_event_bus_queue_size(self):
        """Test event bus queue size."""
        reset_config()
        config = get_config("development")
        assert config.event_bus.queue_size > 0
        assert config.event_bus.worker_count > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
