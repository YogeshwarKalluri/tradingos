"""
Model Manager Abstraction Layer for TradingOS
Provides unified interface for all local AI models with GPU memory management.
"""

from __future__ import annotations
import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Type
from uuid import uuid4

import torch
from pydantic import BaseModel, Field

from core.config import get_settings
from core.types import Event


class ModelBackend(str):
    """Supported model backends."""
    LLAMA_CPP = "llama_cpp"
    VLLM = "vllm"
    TENSORRT = "tensorrt"
    ONNX = "onnx"
    PYTORCH = "pytorch"
    FASTER_WHISPER = "faster_whisper"


@dataclass(slots=True)
class ModelConfig:
    """Base model configuration."""
    name: str
    path: str
    backend: str
    device: str = "cuda"
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class VisionModelConfig(ModelConfig):
    """Vision model configuration."""
    input_size: tuple[int, int] = (512, 512)
    confidence_threshold: float = 0.7
    patterns: List[str] = field(default_factory=list)
    batch_size: int = 8
    inference_timeout_ms: int = 50


@dataclass(slots=True)
class ReasoningModelConfig(ModelConfig):
    """Reasoning LLM configuration."""
    context_size: int = 8192
    gpu_layers: int = -1  # -1 = all layers
    temperature: float = 0.1
    top_p: float = 0.95
    top_k: int = 40
    max_tokens: int = 2048


@dataclass(slots=True)
class EmbeddingModelConfig(ModelConfig):
    """Embedding model configuration."""
    vector_size: int = 1024
    max_sequence_length: int = 512
    batch_size: int = 32
    normalize: bool = True


@dataclass(slots=True)
class SpeechModelConfig(ModelConfig):
    """Speech model configuration."""
    language: str = "en"
    beam_size: int = 5
    temperature: float = 0.0
    vad_filter: bool = True


@dataclass(slots=True)
class GPUMemoryStats:
    """GPU memory statistics."""
    total_vram_mb: float
    allocated_mb: float
    free_mb: float
    utilization_pct: float
    models_loaded: int
    
    @property
    def allocated_pct(self) -> float:
        return (self.allocated_mb / self.total_vram_mb) * 100 if self.total_vram_mb > 0 else 0


class BaseModel(ABC):
    """Abstract base class for all models."""
    
    def __init__(self, config: ModelConfig):
        self.config = config
        self._loaded = False
        self._load_time = 0.0
    
    @property
    def is_loaded(self) -> bool:
        return self._loaded
    
    @property
    def name(self) -> str:
        return self.config.name
    
    @abstractmethod
    async def load(self) -> None:
        """Load model into memory."""
        pass
    
    @abstractmethod
    async def unload(self) -> None:
        """Unload model from memory."""
        pass
    
    @abstractmethod
    async def infer(self, *args, **kwargs) -> Any:
        """Run inference."""
        pass


class VisionModel(BaseModel):
    """Abstract vision model for chart pattern detection."""
    
    @abstractmethod
    async def detect_patterns(
        self, 
        chart_tensor: torch.Tensor,
        timeframe: str
    ) -> List["PatternDetection"]:
        """Detect chart patterns in a chart tensor."""
        pass


class ReasoningModel(BaseModel):
    """Abstract reasoning model for trade decision making."""
    
    @abstractmethod
    async def reason(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """Generate reasoning response."""
        pass
    
    @abstractmethod
    async def reason_with_context(
        self,
        query: str,
        context: List[str],
        system_prompt: Optional[str] = None
    ) -> "ReasoningResult":
        """Generate reasoning with retrieved context."""
        pass


class EmbeddingModel(BaseModel):
    """Abstract embedding model for vector search."""
    
    @abstractmethod
    async def embed_text(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for texts."""
        pass
    
    @abstractmethod
    async def embed_chart(self, chart_tensor: torch.Tensor) -> List[float]:
        """Generate embedding for chart tensor."""
        pass


class SpeechModel(BaseModel):
    """Abstract speech model for audio processing."""
    
    @abstractmethod
    async def transcribe(self, audio_path: str) -> "TranscriptionResult":
        """Transcribe audio to text."""
        pass
    
    @abstractmethod
    async def transcribe_with_timestamps(self, audio_path: str) -> "TranscriptionResult":
        """Transcribe audio with word-level timestamps."""
        pass


@dataclass(slots=True)
class PatternDetection:
    """Pattern detection result."""
    pattern_type: str
    confidence: float
    bounding_box: tuple[int, int, int, int]  # x, y, w, h
    timeframe: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ReasoningResult:
    """Reasoning model output."""
    decision: str
    confidence: float
    reasoning: str
    evidence: List[Dict[str, Any]]
    position_size: float
    stop_loss: float
    take_profit: float
    risk_reward: float


@dataclass(slots=True)
class TranscriptionResult:
    """Speech transcription result."""
    text: str
    segments: List[Dict[str, Any]]  # {text, start, end, confidence}
    language: str
    duration: float


class ModelManager:
    """
    Centralized model manager for all AI models.
    
    Features:
    - Loads models once at startup into VRAM
    - Unified inference interface
    - GPU memory management
    - Model hot-swapping
    - Dedicated CUDA streams for parallel inference
    """
    
    def __init__(self):
        self._models: Dict[str, BaseModel] = {}
        self._configs: Dict[str, ModelConfig] = {}
        self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._vision_stream = torch.cuda.Stream() if torch.cuda.is_available() else None
        self._reasoning_stream = torch.cuda.Stream() if torch.cuda.is_available() else None
        self._embedding_stream = torch.cuda.Stream() if torch.cuda.is_available() else None
        self._speech_stream = torch.cuda.Stream() if torch.cuda.is_available() else None
        self._lock = asyncio.Lock()
        self._initialized = False
    
    @property
    def device(self) -> torch.device:
        return self._device
    
    @property
    def is_cuda_available(self) -> bool:
        return torch.cuda.is_available()
    
    def register_model(self, config: ModelConfig) -> None:
        """Register a model configuration."""
        self._configs[config.name] = config
    
    def get_config(self, name: str) -> Optional[ModelConfig]:
        """Get model configuration by name."""
        return self._configs.get(name)
    
    async def load_vision_model(self, name: str) -> Optional[VisionModel]:
        """Load vision model."""
        async with self._lock:
            if name in self._models:
                return self._models[name]  # type: ignore
            
            config = self._configs.get(name)
            if not config or not config.enabled:
                return None
            
            # Import backend-specific implementation
            if config.backend == ModelBackend.ONNX:
                from core.models.vision.onnx_vision import ONNXVisionModel
                model = ONNXVisionModel(config)
            elif config.backend == ModelBackend.TENSORRT:
                from core.models.vision.tensorrt_vision import TensorRTVisionModel
                model = TensorRTVisionModel(config)
            elif config.backend == ModelBackend.PYTORCH:
                from core.models.vision.pytorch_vision import PyTorchVisionModel
                model = PyTorchVisionModel(config)
            else:
                raise ValueError(f"Unsupported vision backend: {config.backend}")
            
            start = time.time()
            await model.load()
            model._load_time = time.time() - start
            self._models[name] = model
            return model
    
    async def load_reasoning_model(self, name: str) -> Optional[ReasoningModel]:
        """Load reasoning LLM."""
        async with self._lock:
            if name in self._models:
                return self._models[name]  # type: ignore
            
            config = self._configs.get(name)
            if not config or not config.enabled:
                return None
            
            if config.backend == ModelBackend.LLAMA_CPP:
                from core.models.reasoning.llama_cpp_reasoning import LlamaCppReasoningModel
                model = LlamaCppReasoningModel(config)
            elif config.backend == ModelBackend.VLLM:
                from core.models.reasoning.vllm_reasoning import VLLMReasoningModel
                model = VLLMReasoningModel(config)
            elif config.backend == ModelBackend.ONNX:
                from core.models.reasoning.onnx_reasoning import ONNXReasoningModel
                model = ONNXReasoningModel(config)
            else:
                raise ValueError(f"Unsupported reasoning backend: {config.backend}")
            
            start = time.time()
            await model.load()
            model._load_time = time.time() - start
            self._models[name] = model
            return model
    
    async def load_embedding_model(self, name: str) -> Optional[EmbeddingModel]:
        """Load embedding model."""
        async with self._lock:
            if name in self._models:
                return self._models[name]  # type: ignore
            
            config = self._configs.get(name)
            if not config or not config.enabled:
                return None
            
            if config.backend == ModelBackend.ONNX:
                from core.models.embedding.onnx_embedding import ONNXEmbeddingModel
                model = ONNXEmbeddingModel(config)
            elif config.backend == ModelBackend.PYTORCH:
                from core.models.embedding.pytorch_embedding import PyTorchEmbeddingModel
                model = PyTorchEmbeddingModel(config)
            else:
                raise ValueError(f"Unsupported embedding backend: {config.backend}")
            
            start = time.time()
            await model.load()
            model._load_time = time.time() - start
            self._models[name] = model
            return model
    
    async def load_speech_model(self, name: str) -> Optional[SpeechModel]:
        """Load speech model."""
        async with self._lock:
            if name in self._models:
                return self._models[name]  # type: ignore
            
            config = self._configs.get(name)
            if not config or not config.enabled:
                return None
            
            if config.backend == ModelBackend.FASTER_WHISPER:
                from core.models.speech.faster_whisper_speech import FasterWhisperSpeechModel
                model = FasterWhisperSpeechModel(config)
            elif config.backend == ModelBackend.ONNX:
                from core.models.speech.onnx_speech import ONNXSpeechModel
                model = ONNXSpeechModel(config)
            else:
                raise ValueError(f"Unsupported speech backend: {config.backend}")
            
            start = time.time()
            await model.load()
            model._load_time = time.time() - start
            self._models[name] = model
            return model
    
    def get_model(self, name: str) -> Optional[BaseModel]:
        """Get loaded model by name."""
        return self._models.get(name)
    
    async def unload_model(self, name: str) -> bool:
        """Unload a model from memory."""
        async with self._lock:
            model = self._models.pop(name, None)
            if model:
                await model.unload()
                return True
            return False
    
    async def unload_all(self) -> None:
        """Unload all models."""
        async with self._lock:
            for name, model in self._models.items():
                await model.unload()
            self._models.clear()
            torch.cuda.empty_cache()
    
    def get_gpu_memory_stats(self) -> GPUMemoryStats:
        """Get current GPU memory statistics."""
        if not self.is_cuda_available:
            return GPUMemoryStats(
                total_vram_mb=0,
                allocated_mb=0,
                free_mb=0,
                utilization_pct=0,
                models_loaded=len(self._models)
            )
        
        total = torch.cuda.get_device_properties(0).total_memory / 1024**2
        allocated = torch.cuda.memory_allocated() / 1024**2
        free = total - allocated
        
        return GPUMemoryStats(
            total_vram_mb=total,
            allocated_mb=allocated,
            free_mb=free,
            utilization_pct=(allocated / total) * 100 if total > 0 else 0,
            models_loaded=len(self._models)
        )
    
    def get_model_info(self, name: str) -> Optional[Dict[str, Any]]:
        """Get model information."""
        model = self._models.get(name)
        config = self._configs.get(name)
        if not model and not config:
            return None
        
        return {
            "name": name,
            "loaded": name in self._models,
            "config": config.__dict__ if config else None,
            "load_time": model._load_time if model else None,
        }
    
    async def initialize_from_config(self) -> None:
        """Initialize all models from configuration."""
        if self._initialized:
            return
        
        settings = get_settings()
        model_configs = settings.model_manager.models
        
        for model_type, config_dict in model_configs.items():
            config = ModelConfig(**config_dict)
            self.register_model(config)
        
        # Load models in parallel
        tasks = []
        
        # Vision models
        if "vision" in model_configs:
            tasks.append(self.load_vision_model(model_configs["vision"]["name"]))
        
        # Reasoning models
        if "reasoning" in model_configs:
            tasks.append(self.load_reasoning_model(model_configs["reasoning"]["name"]))
        
        # Embedding models
        if "embedding" in model_configs:
            tasks.append(self.load_embedding_model(model_configs["embedding"]["name"]))
        
        # Speech models
        if "speech" in model_configs:
            tasks.append(self.load_speech_model(model_configs["speech"]["name"]))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        self._initialized = True
    
    async def shutdown(self) -> None:
        """Shutdown model manager."""
        await self.unload_all()
        self._initialized = False


# Global model manager instance
_model_manager: Optional[ModelManager] = None


def get_model_manager() -> ModelManager:
    """Get or create the global model manager."""
    global _model_manager
    if _model_manager is None:
        _model_manager = ModelManager()
    return _model_manager


def set_model_manager(manager: ModelManager) -> None:
    """Set the global model manager (for testing)."""
    global _model_manager
    _model_manager = manager


async def shutdown_model_manager() -> None:
    """Shutdown the global model manager."""
    global _model_manager
    if _model_manager:
        await _model_manager.shutdown()
        _model_manager = None