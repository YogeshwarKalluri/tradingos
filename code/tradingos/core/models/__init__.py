"""TradingOS Model Manager - Load, manage, and swap AI models."""

import asyncio
import contextlib
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Optional

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    torch = None
    TORCH_AVAILABLE = False

from tradingos.core.config import ModelManagerConfig, get_config
from tradingos.core.logging import get_logger

if TYPE_CHECKING:
    import torch

logger = get_logger(__name__)


@dataclass
class ModelMetadata:
    """Static model metadata."""
    name: str
    version: str
    architecture: str
    format: str  # tensorrt, onnx, gguf, ct2, pytorch
    vram_mb: int
    input_spec: dict[str, Any]
    output_spec: dict[str, Any]
    tags: list[str] = field(default_factory=list)
    metrics: dict[str, float] = field(default_factory=dict)


class BaseModel(ABC):
    """Abstract base class for all models. Swappable without code changes."""

    @property
    @abstractmethod
    def metadata(self) -> ModelMetadata:
        """Return static model metadata."""
        pass

    @abstractmethod
    def load(self, device: "torch.device", **kwargs) -> None:
        """Load model into VRAM. Called once at startup."""
        pass

    @abstractmethod
    def warmup(self, num_runs: int = 3) -> None:
        """Warm up kernels, allocate workspace. Called after load."""
        pass

    @abstractmethod
    def infer(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """Single inference call. Must be thread-safe."""
        pass

    def infer_batch(self, inputs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Batch inference. Default: loop over infer(). Override for true batching."""
        return [self.infer(inp) for inp in inputs]

    @abstractmethod
    def unload(self) -> None:
        """Free VRAM. Called on swap or shutdown."""
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """Quick sanity check. Used by ModelManager."""
        pass


@dataclass
class ModelRegistryEntry:
    """Model registry entry with loader info."""
    name: str
    loader: str  # module:ClassName
    path: str
    priority: int = 50
    kwargs: dict[str, Any] = field(default_factory=dict)
    version: str = "latest"
    loaded: bool = False
    instance: BaseModel | None = None


class ModelManager:
    """Manages model lifecycle, VRAM budget, and hot-swapping."""

    def __init__(self, config: ModelManagerConfig | None = None):
        self.config = config or get_config().model_manager
        self.registry: dict[str, ModelRegistryEntry] = {}
        self._loaded_models: dict[str, BaseModel] = {}
        self._vram_used_mb = 0
        self._lock = threading.RLock()
        self._health_check_task: asyncio.Task | None = None
        self._running = False

    def register(self, entry: ModelRegistryEntry) -> None:
            """Register a model in the registry."""
            with self._lock:
                self.registry[entry.name] = entry
                vram_str = (
                    str(entry.metadata.vram_mb)
                    if hasattr(entry, "metadata")
                    else "unknown"
                )
                logger.info(
                    "model_registered",
                    name=entry.name,
                    version=entry.version,
                    vram_mb=vram_str,
                )

    def register_from_dict(self, name: str, loader: str, path: str,
                          priority: int = 50, kwargs: dict | None = None,
                          version: str = "latest") -> None:
        """Register model from parameters."""
        entry = ModelRegistryEntry(
            name=name,
            loader=loader,
            path=path,
            priority=priority,
            kwargs=kwargs or {},
            version=version
        )
        self.register(entry)

    def load_registry_yaml(self, path: str) -> None:
        """Load model registry from YAML file."""
        import yaml
        with open(path) as f:
            data = yaml.safe_load(f)

        for name, info in data.get("models", {}).items():
            self.register_from_dict(
                name=name,
                loader=info["loader"],
                path=info["path"],
                priority=info.get("priority", 50),
                kwargs=info.get("kwargs", {}),
                version=info.get("current_version", "latest")
            )

    def _import_loader(self, loader_str: str) -> type[BaseModel]:
        """Import model class from string."""
        module_path, class_name = loader_str.rsplit(":", 1)
        module = __import__(module_path, fromlist=[class_name])
        return getattr(module, class_name)

    def load_model(self, name: str, device: Optional["torch.device"] = None) -> BaseModel:
        """Load a model by name."""
        with self._lock:
            if name in self._loaded_models:
                return self._loaded_models[name]

            if name not in self.registry:
                raise ValueError(f"Model not registered: {name}")

            entry = self.registry[name]

            # Check VRAM budget
            # We need to estimate VRAM - use metadata if available
            estimated_vram = 0
            try:
                model_class = self._import_loader(entry.loader)
                # Create temp instance to get metadata
                temp_instance = model_class()
                estimated_vram = temp_instance.metadata.vram_mb
            except Exception:
                logger.warning("could_not_estimate_vram", model=name)
                estimated_vram = 1024  # Default 1GB

            if self._vram_used_mb + estimated_vram > self.config.vram_budget_mb:
                # Try to evict LRU non-priority models
                self._evict_lru(estimated_vram)

                if self._vram_used_mb + estimated_vram > self.config.vram_budget_mb:
                    raise RuntimeError(
                        f"Insufficient VRAM for {name}: "
                        f"need {estimated_vram}MB, "
                        f"have {self.config.vram_budget_mb - self._vram_used_mb}MB free"
                    )

            # Load model
            if TORCH_AVAILABLE:
                device = device or (
                    torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")
                )
            else:
                device = None
            model_class = self._import_loader(entry.loader)
            model = model_class()
            model.load(device, **entry.kwargs)
            model.warmup(self.config.warmup_runs)

            self._loaded_models[name] = model
            self._vram_used_mb += estimated_vram
            entry.loaded = True
            entry.instance = model

            logger.info(
            "model_loaded", name=name, vram_used_mb=self._vram_used_mb, device=str(device)
        )
            return model

    def unload_model(self, name: str) -> None:
        """Unload a model by name."""
        with self._lock:
            if name not in self._loaded_models:
                return

            model = self._loaded_models[name]
            estimated_vram = model.metadata.vram_mb

            model.unload()
            del self._loaded_models[name]
            self._vram_used_mb -= estimated_vram

            if name in self.registry:
                self.registry[name].loaded = False
                self.registry[name].instance = None

            logger.info("model_unloaded", name=name, vram_used_mb=self._vram_used_mb)

    def get_model(self, name: str) -> BaseModel | None:
        """Get loaded model instance."""
        with self._lock:
            return self._loaded_models.get(name)

    def is_loaded(self, name: str) -> bool:
        """Check if model is loaded."""
        with self._lock:
            return name in self._loaded_models

    def _evict_lru(self, needed_mb: int) -> None:
        """Evict least recently used models to free VRAM."""
        # Sort by priority (lowest first), then by load time
        candidates = [
            (name, entry) for name, entry in self.registry.items()
            if entry.loaded and name in self._loaded_models
        ]
        candidates.sort(key=lambda x: (x[1].priority, 0))  # Priority first

        for name, entry in candidates:
            if self._vram_used_mb + needed_mb <= self.config.vram_budget_mb:
                break
            if entry.priority >= 100:  # Never evict priority 100 (market hours critical)
                continue
            logger.info("evicting_model", name=name, priority=entry.priority)
            self.unload_model(name)

    async def load_market_hours_models(self, device: Optional["torch.device"] = None) -> None:
        """Load all market hours models."""
        logger.info("loading_market_hours_models")
        for name in self.config.market_hours_models:
            try:
                self.load_model(name, device)
            except Exception as e:
                logger.error("failed_to_load_market_model", name=name, error=str(e))
                raise

    async def load_after_hours_models(self, device: Optional["torch.device"] = None) -> None:
        """Load all after hours models."""
        logger.info("loading_after_hours_models")
        # Unload market hours models first (except reasoning_llm if needed)
        for name in list(self._loaded_models.keys()):
            if name not in self.config.after_hours_models and name != "reasoning_llm":
                self.unload_model(name)

        for name in self.config.after_hours_models:
            try:
                self.load_model(name, device)
            except Exception as e:
                logger.error("failed_to_load_after_hours_model", name=name, error=str(e))

    async def unload_all(self) -> None:
        """Unload all models."""
        for name in list(self._loaded_models.keys()):
            self.unload_model(name)

    async def start_health_checks(self) -> None:
        """Start periodic health checks."""
        if self._health_check_task is not None:
            return

        self._running = True
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        logger.info("health_checks_started", interval_sec=self.config.health_check_interval_sec)

    async def stop_health_checks(self) -> None:
        """Stop health checks."""
        self._running = False
        if self._health_check_task:
            self._health_check_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._health_check_task
        logger.info("health_checks_stopped")

    async def _health_check_loop(self) -> None:
        """Periodic health check loop."""
        while self._running:
            await asyncio.sleep(self.config.health_check_interval_sec)

            for name, model in list(self._loaded_models.items()):
                try:
                    healthy = model.health_check()
                    if not healthy:
                        logger.warning("model_unhealthy", name=name)
                        if self.config.auto_recover:
                            logger.info("auto_recovering_model", name=name)
                            self.unload_model(name)
                            self.load_model(name)
                except Exception as e:
                    logger.error("health_check_failed", name=name, error=str(e))

    def get_vram_usage(self) -> dict[str, Any]:
        """Get current VRAM usage."""
        with self._lock:
            return {
                "used_mb": self._vram_used_mb,
                "budget_mb": self.config.vram_budget_mb,
                "free_mb": self.config.vram_budget_mb - self._vram_used_mb,
                "loaded_models": list(self._loaded_models.keys())
            }

    def get_stats(self) -> dict[str, Any]:
        """Get model manager statistics."""
        with self._lock:
            return {
                "vram": self.get_vram_usage(),
                "registered": list(self.registry.keys()),
                "loaded": list(self._loaded_models.keys()),
                "registry_details": {
                    name: {
                        "version": entry.version,
                        "priority": entry.priority,
                        "loaded": entry.loaded,
                        "path": entry.path
                    }
                    for name, entry in self.registry.items()
                }
            }


# Global model manager instance
_model_manager: ModelManager | None = None


def get_model_manager() -> ModelManager:
    """Get global model manager instance."""
    global _model_manager
    if _model_manager is None:
        _model_manager = ModelManager()
    return _model_manager


def set_model_manager(manager: ModelManager) -> None:
    """Set global model manager (for testing)."""
    global _model_manager
    _model_manager = manager
