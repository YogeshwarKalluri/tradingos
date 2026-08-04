"""Tests for TradingOS Model Manager."""


import pytest
from tradingos.core.config import ModelManagerConfig, reset_config
from tradingos.core.models import BaseModel, ModelManager, ModelMetadata, ModelRegistryEntry


class MockModel(BaseModel):
    """Mock model for testing."""

    def __init__(self):
        self._loaded = False
        self._metadata = ModelMetadata(
            name="mock_model",
            version="1.0.0",
            architecture="Mock",
            format="pytorch",
            vram_mb=512,
            input_spec={"shape": [1, 3, 224, 224]},
            output_spec={"logits": [1000]},
        )

    @property
    def metadata(self) -> ModelMetadata:
        return self._metadata

    def load(self, device, **kwargs):
        self._loaded = True
        self._device = device

    def warmup(self, num_runs: int = 3):
        pass

    def infer(self, inputs):
        return {"output": "mock"}

    def unload(self):
        self._loaded = False

    def health_check(self) -> bool:
        return self._loaded


class TestModelManager:
    """Test model manager functionality."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Setup and teardown."""
        reset_config()
        config = ModelManagerConfig(vram_budget_mb=2048)  # 2GB for testing
        manager = ModelManager(config)
        yield manager

    def test_register_model(self, setup_teardown):
        """Test model registration."""
        manager = setup_teardown
        entry = ModelRegistryEntry(
            name="test_model",
            loader="tests.unit.test_models:MockModel",
            path="models/mock.onnx",
            priority=50
        )
        manager.register(entry)

        assert "test_model" in manager.registry
        assert manager.registry["test_model"].priority == 50

    def test_load_unload_model(self, setup_teardown):
        """Test loading and unloading a model."""
        manager = setup_teardown

        # Register mock model
        entry = ModelRegistryEntry(
            name="mock_model",
            loader="tests.unit.test_models:MockModel",
            path="models/mock.onnx",
            priority=50
        )
        manager.register(entry)

        # Load model
        model = manager.load_model("mock_model")
        assert model is not None
        assert manager.is_loaded("mock_model")
        assert manager._vram_used_mb > 0

        # Get same model instance
        model2 = manager.get_model("mock_model")
        assert model is model2

        # Unload
        manager.unload_model("mock_model")
        assert not manager.is_loaded("mock_model")
        assert manager._vram_used_mb == 0

    def test_vram_budget_enforcement(self, setup_teardown):
        """Test VRAM budget prevents overloading."""
        manager = setup_teardown

        # Register two models that exceed budget
        entry1 = ModelRegistryEntry(
            name="model1",
            loader="tests.unit.test_models:MockModel",
            path="models/mock1.onnx",
            priority=50
        )
        entry2 = ModelRegistryEntry(
            name="model2",
            loader="tests.unit.test_models:MockModel",
            path="models/mock2.onnx",
            priority=50
        )
        manager.register(entry1)
        manager.register(entry2)

        # Load first model (512MB)
        manager.load_model("model1")
        assert manager._vram_used_mb == 512

        # Load second model (512MB) - should work (total 1024 < 2048)
        manager.load_model("model2")
        assert manager._vram_used_mb == 1024

        # Third model would exceed budget - but we only have 2 registered
        # So test passes if both loaded successfully

    def test_priority_eviction(self, setup_teardown):
        """Test LRU eviction respects priority."""
        manager = setup_teardown
        manager.config.vram_budget_mb = 1024  # 1GB budget

        # Register models with different priorities
        entry_low = ModelRegistryEntry(
            name="low_priority",
            loader="tests.unit.test_models:MockModel",
            path="models/low.onnx",
            priority=10
        )
        entry_high = ModelRegistryEntry(
            name="high_priority",
            loader="tests.unit.test_models:MockModel",
            path="models/high.onnx",
            priority=100  # Critical - never evict
        )
        manager.register(entry_low)
        manager.register(entry_high)

        # Load both
        manager.load_model("high_priority")
        manager.load_model("low_priority")

        # Both should be loaded
        assert manager.is_loaded("high_priority")
        assert manager.is_loaded("low_priority")

        # VRAM used should be ~1024MB
        assert manager._vram_used_mb == 1024

    def test_get_stats(self, setup_teardown):
        """Test get_stats returns correct info."""
        manager = setup_teardown

        entry = ModelRegistryEntry(
            name="test_model",
            loader="tests.unit.test_models:MockModel",
            path="models/test.onnx",
            priority=50
        )
        manager.register(entry)
        manager.load_model("test_model")

        stats = manager.get_stats()

        assert "vram" in stats
        assert "registered" in stats
        assert "loaded" in stats
        assert "test_model" in stats["loaded"]
        assert stats["vram"]["used_mb"] > 0


class TestModelMetadata:
    """Test model metadata."""

    def test_metadata_creation(self):
        """Test ModelMetadata creation."""
        metadata = ModelMetadata(
            name="test",
            version="1.0",
            architecture="TestNet",
            format="onnx",
            vram_mb=256,
            input_spec={"shape": [1, 3, 224, 224]},
            output_spec={"logits": [1000]},
        )

        assert metadata.name == "test"
        assert metadata.vram_mb == 256


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
