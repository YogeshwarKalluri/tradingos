# TradingOS Model Selection Strategy

## Overview

This document defines the model selection, management, and deployment strategy for TradingOS. The platform uses **specialized models for specialized tasks** - no single giant LLM. Every model is local, optimized for RTX 5080 (16GB VRAM), and swappable without code changes.

---

## 1. Model Registry

### 1.1 Market Hours Models (Always Loaded 9:00-16:30 ET)

| Model | Role | Architecture | Format | VRAM | Latency (batch=1) | Purpose |
|-------|------|--------------|--------|------|-------------------|---------|
| **vision_pattern** | Pattern Classification | EfficientNet-B0 (custom head) | TensorRT FP16 | 2.0 GB | 45 ms | 8-pattern classification |
| **vision_detect** | Object Detection | YOLOv8n | TensorRT FP16 | 1.0 GB | 25 ms | Candle/indicator detection |
| **vision_keypoint** | Keypoint Detection | HRNet-W18 | TensorRT FP16 | 1.5 GB | 35 ms | S/R, VWAP touch points |
| **reasoning_llm** | Thesis Explanation | Llama-3.2-3B-Instruct | GGUF Q4_K_M | 2.0 GB | 150 ms | Human-readable reasoning |
| **embed_text** | Text Embedding | BGE-large-en-v1.5 | ONNX FP16 | 1.0 GB | 20 ms | Transcript/trade embedding |
| **TOTAL** | | | | **7.5 GB** | | **Leaves 8.5 GB headroom** |

### 1.2 After-Hours Models (Loaded 16:30-08:00 ET)

| Model | Role | Architecture | Format | VRAM | Purpose |
|-------|------|--------------|--------|------|---------|
| **stt_whisper** | Speech-to-Text | faster-whisper large-v3 | CT2 FP16 | 3.0 GB | Video transcription |
| **diarization** | Speaker Diarization | pyannote.audio 3.1 | PyTorch FP16 | 1.0 GB | Ross vs chat separation |
| **chart_classify** | Chart Frame Classification | MobileNetV3-small | ONNX FP16 | 0.1 GB | Chart vs non-chart |
| **chart_detect** | Chart Region Detection | YOLOv8n | TensorRT FP16 | 0.5 GB | Chart element detection |
| **ocr_paddle** | OCR | PaddleOCR PP-OCRv4 | ONNX FP16 | 0.5 GB | Text extraction from charts |
| **extract_llm** | Trade Extraction | Llama-3.2-3B-Instruct | GGUF Q4_K_M | 2.0 GB | Structured trade extraction |
| **TOTAL** | | | | **~7.1 GB** | **Can run alongside market models if needed** |

### 1.3 Training/Experimentation Models (On-Demand)

| Model | Role | Architecture | Format | VRAM | Purpose |
|-------|------|--------------|--------|------|---------|
| **vision_train** | Pattern Classifier Training | EfficientNet-B0 | PyTorch FP16/BF16 | 8-10 GB | Fine-tuning |
| **embed_train** | Embedding Fine-tuning | BGE-large-en-v1.5 | PyTorch FP16 | 6-8 GB | Domain adaptation |
| **rl_policy** | RL Policy (future) | Transformer | PyTorch | 4-6 GB | Execution optimization |

---

## 2. Model Interface (Pluggable Architecture)

### 2.1 Base Interface

```python
# core/models/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import torch

@dataclass
class ModelMetadata:
    name: str
    version: str
    architecture: str
    format: str           # 'tensorrt', 'onnx', 'gguf', 'ct2', 'pytorch'
    vram_mb: int
    input_spec: Dict      # {'shape': [1,3,256,256], 'dtype': 'float16', 'layout': 'NCHW'}
    output_spec: Dict
    tags: List[str]       # ['vision', 'market_hours', 'pattern_classification']
    metrics: Dict         # {'accuracy': 0.87, 'latency_p99_ms': 52}

class BaseModel(ABC):
    """All models implement this interface. Swapping requires no code changes."""
    
    @property
    @abstractmethod
    def metadata(self) -> ModelMetadata:
        """Static model info."""
        pass
    
    @abstractmethod
    def load(self, device: torch.device, **kwargs) -> None:
        """Load model into VRAM. Called once at startup."""
        pass
    
    @abstractmethod
    def warmup(self, num_runs: int = 3) -> None:
        """Warm up kernels, allocate workspace. Called after load."""
        pass
    
    @abstractmethod
    def infer(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Single inference call. Must be thread-safe."""
        pass
    
    @abstractmethod
    def infer_batch(self, inputs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Batch inference. Default: loop over infer(). Override for true batching."""
        pass
    
    @abstractmethod
    def unload(self) -> None:
        """Free VRAM. Called on swap or shutdown."""
        pass
    
    @abstractmethod
    def health_check(self) -> bool:
        """Quick sanity check. Used by ModelManager."""
        pass
```

### 2.2 Model Implementations

```python
# core/models/vision_pattern.py
class VisionPatternModel(BaseModel):
    """EfficientNet-B0 pattern classifier, TensorRT FP16."""
    
    @property
    def metadata(self) -> ModelMetadata:
        return ModelMetadata(
            name="vision_pattern",
            version="1.0.0",
            architecture="EfficientNet-B0+CustomHead",
            format="tensorrt",
            vram_mb=2048,
            input_spec={"shape": [1, 3, 256, 256], "dtype": "float16", "layout": "NCHW"},
            output_spec={"pattern_probs": [8], "confidence": [1]},
            tags=["vision", "market_hours", "pattern_classification"],
            metrics={"val_f1": 0.87, "latency_p99_ms": 52}
        )
    
    def load(self, device: torch.device, **kwargs):
        import tensorrt as trt
        engine_path = Path("models/tensorrt/vision_pattern_fp16.engine")
        self.logger = trt.Logger(trt.Logger.WARNING)
        with open(engine_path, "rb") as f:
            runtime = trt.Runtime(self.logger)
            self.engine = runtime.deserialize_cuda_engine(f.read())
        self.context = self.engine.create_execution_context()
        # Allocate buffers
        self.inputs, self.outputs, self.bindings, self.stream = allocate_buffers(self.engine)
    
    def infer(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        # inputs: {"chart_tensor": torch.Tensor [1,3,256,256] on CUDA}
        # Copy to TensorRT buffer, execute, return probs
        ...
```

---

## 3. Model Manager

### 3.1 Responsibilities

- Load/unload models based on schedule and VRAM budget
- Enforce 14GB VRAM limit (2GB headroom for OS/CUDA context)
- LRU eviction when budget exceeded
- Health monitoring and auto-recovery
- Version management and rollback
- Warmup scheduling (9:00 AM market hours models)

### 3.2 Configuration

```yaml
# config/models.yaml
model_manager:
  vram_budget_mb: 14336  # 14 GB
  headroom_mb: 2048      # 2 GB reserved
  
  market_hours:
    start: "09:00"
    end: "16:30"
    timezone: "America/New_York"
    models:
      - vision_pattern
      - vision_detect
      - vision_keypoint
      - reasoning_llm
      - embed_text
  
  after_hours:
    models:
      - stt_whisper
      - diarization
      - chart_classify
      - chart_detect
      - ocr_paddle
      - extract_llm
  
  swap_policy: "lru"           # or 'priority', 'manual'
  warmup_runs: 3
  health_check_interval_sec: 60
  auto_recover: true
  
  model_registry:
    vision_pattern:
      loader: "core.models.vision_pattern:VisionPatternModel"
      path: "models/tensorrt/vision_pattern_fp16.engine"
      priority: 100  # Never evict during market hours
    vision_detect:
      loader: "core.models.vision_detect:VisionDetectModel"
      path: "models/tensorrt/yolov8n_fp16.engine"
      priority: 100
    vision_keypoint:
      loader: "core.models.vision_keypoint:VisionKeypointModel"
      path: "models/tensorrt/hrnet_w18_fp16.engine"
      priority: 100
    reasoning_llm:
      loader: "core.models.reasoning_llm:ReasoningLLM"
      path: "models/gguf/llama-3.2-3b-instruct-q4_k_m.gguf"
      priority: 90
      kwargs:
        n_ctx: 4096
        n_gpu_layers: -1
    embed_text:
      loader: "core.models.embed_text:EmbedTextModel"
      path: "models/onnx/bge-large-en-v1.5-fp16.onnx"
      priority: 90
    stt_whisper:
      loader: "core.models.stt_whisper:STTWhisperModel"
      path: "models/ct2/whisper-large-v3-ct2-fp16"
      priority: 50
    # ... etc
```

### 3.3 Runtime Behavior

```
08:30  Process start
       │
       ├─► Load market_hours models (priority 100 first)
       │     vision_pattern → vision_detect → vision_keypoint
       │     reasoning_llm → embed_text
       │
       ├─► Warmup each (3 runs)
       │
       ├─► Verify VRAM: ~7.5 GB used
       │
       ▼
09:00  MARKET HOURS READY
       │
       ├─► Health check every 60s
       ├─► If VRAM > 14GB: evict LRU (non-priority models first)
       └─► If health check fails: reload model
       │
       ▼
16:30  MARKET CLOSE
       │
       ├─► Unload market_hours models (keep reasoning_llm if needed)
       ├─► Load after_hours models
       ├─► Warmup
       │
       ▼
22:00  Evaluation run (may load training models temporarily)
       │
       ▼
08:00  Next day prep
```

---

## 4. Model Optimization for RTX 5080

### 4.1 TensorRT Optimization Pipeline

```bash
# 1. Export PyTorch → ONNX
python export_onnx.py \
  --model vision_pattern \
  --input_shape 1,3,256,256 \
  --output models/onnx/vision_pattern.onnx

# 2. ONNX → TensorRT FP16 (with timing cache)
trtexec \
  --onnx=models/onnx/vision_pattern.onnx \
  --saveEngine=models/tensorrt/vision_pattern_fp16.engine \
  --fp16 \
  --workspace=4096 \
  --timingCacheFile=models/tensorrt/timing.cache \
  --buildOnly

# 3. Profile
trtexec \
  --loadEngine=models/tensorrt/vision_pattern_fp16.engine \
  --iterations=1000 \
  --warmUp=100
```

### 4.2 Quantization Strategy

| Model | Precision | Rationale |
|-------|-----------|-----------|
| Vision (Pattern/Detect/Keypoint) | FP16 | Accuracy critical, 2x speedup vs FP32 |
| Embeddings | FP16 | Negligible accuracy loss, 2x throughput |
| LLMs (Reasoning/Extraction) | GGUF Q4_K_M | Best quality/size for llama.cpp, 4-bit |
| STT (Whisper) | CT2 FP16 | CTranslate2 optimized, FP16 native |
| OCR | FP16 | PaddleOCR supports FP16, minimal loss |

**INT8 quantization**: Evaluated but rejected for vision models (2-3% accuracy drop). Revisit if VRAM pressure increases.

### 4.3 CUDA Graphs & Kernel Fusion

- Vision models: Enable CUDA Graph capture for fixed-shape inputs
- TensorRT: Automatic kernel fusion via `--fp16` and `--strict-types`
- Custom kernels: Consider for indicator calculations (Numba CUDA)

---

## 5. Model Versioning & Experiment Tracking

### 5.1 Versioning Scheme

```
models/
├── tensorrt/
│   ├── vision_pattern_fp16_v1.0.0.engine
│   ├── vision_pattern_fp16_v1.1.0.engine
│   └── vision_pattern_fp16_latest.engine  → symlink to current
├── onnx/
│   └── bge-large-en-v1.5-fp16.onnx
├── gguf/
│   └── llama-3.2-3b-instruct-q4_k_m.gguf
├── ct2/
│   └── whisper-large-v3-ct2-fp16/
└── registry.yaml  # Maps model_name → version + path
```

### 5.2 Registry Format

```yaml
# models/registry.yaml
models:
  vision_pattern:
    current_version: "1.1.0"
    versions:
      "1.0.0":
        path: "tensorrt/vision_pattern_fp16_v1.0.0.engine"
        metrics: {val_f1: 0.84, latency_p99_ms: 55}
        trained_on: "2025-01-15"
        notes: "Initial release"
      "1.1.0":
        path: "tensorrt/vision_pattern_fp16_v1.1.0.engine"
        metrics: {val_f1: 0.87, latency_p99_ms: 52}
        trained_on: "2025-02-20"
        notes: "Added hard negative mining, 50k more samples"
  
  reasoning_llm:
    current_version: "3.2-3b-q4km"
    versions:
      "3.2-3b-q4km":
        path: "gguf/llama-3.2-3b-instruct-q4_k_m.gguf"
        metrics: {perplexity: 5.2, latency_ms: 150}
        notes: "Default quantization"
```

### 5.3 Experiment Tracking (MLflow-compatible, local)

```python
# experiments/EXP-001_vision_pattern_v1.1.0/
experiment/
├── config.yaml           # Training hyperparameters
├── metrics.json          # Final metrics
├── curves/               # Loss/accuracy plots
├── confusion_matrix.png
├── model_card.md         # Standardized model card
└── artifacts/            # Checkpoints, ONNX export
```

**Model Card Template**:
```markdown
# Model Card: vision_pattern v1.1.0

## Model Details
- Architecture: EfficientNet-B0 + Custom Head (8 classes)
- Training Data: 120k labeled chart images (Ross videos + synthetic)
- Framework: PyTorch 2.3 → ONNX → TensorRT FP16

## Intended Use
- Real-time pattern classification during market hours
- Input: 256x256 RGB chart tensor (4 timeframes stacked)
- Output: 8-class probabilities + confidence

## Metrics (Validation Set, 15k images)
| Class | Precision | Recall | F1 |
|-------|-----------|--------|-----|
| bull_flag | 0.89 | 0.85 | 0.87 |
| vwap_reclaim | 0.91 | 0.88 | 0.89 |
| ... | | | |
| **Macro Avg** | **0.88** | **0.86** | **0.87** |

## Latency (RTX 5080, TensorRT FP16, batch=1)
- p50: 42 ms
- p95: 48 ms
- p99: 52 ms
- VRAM: 2.0 GB

## Limitations
- Trained on 1m/5m/15m/daily composite charts
- May not generalize to tick charts or non-equity assets
- Confidence calibration: ECE = 0.034 (good)

## Ethical Considerations
- No PII in training data
- Financial advice disclaimer required in UI
```

---

## 6. Model Evaluation Framework

### 6.1 Vision Model Evaluation

```python
# evaluations/vision_eval.py
async def evaluate_vision_model(model_name: str, dataset: str = "test"):
    model = ModelManager.get(model_name)
    
    metrics = {
        "per_class": {},      # precision, recall, f1, support
        "macro_avg": {},
        "confusion_matrix": [],
        "calibration": {},    # ECE, MCE, reliability diagram
        "latency": {},        # p50, p95, p99, throughput
        "vram": {}            # peak, average
    }
    
    # Run inference on full dataset
    for batch in dataloader:
        with timer():
            preds = model.infer_batch(batch)
        # Accumulate metrics
    
    # Calibration: bin predictions, compare accuracy vs confidence
    ece = expected_calibration_error(preds, labels)
    
    # Save results
    save_evaluation(model_name, dataset, metrics)
    update_model_performance_table(model_name, metrics)
    
    return metrics
```

### 6.2 LLM Evaluation (Reasoning/Extraction)

```python
# evaluations/llm_eval.py
def evaluate_reasoning_llm():
    # Test cases: known trade scenarios → expected reasoning elements
    test_cases = load_test_cases("evaluations/test_cases/reasoning.jsonl")
    
    for case in test_cases:
        thesis = case["thesis"]
        expected_elements = case["must_mention"]  # ["VWAP", "high RVol", "bull flag"]
        forbidden = case["must_not_mention"]       # ["guaranteed", "certain"]
        
        output = llm.generate(thesis)
        
        score = 0
        for elem in expected_elements:
            if elem.lower() in output.lower():
                score += 1
        for elem in forbidden:
            if elem.lower() in output.lower():
                score -= 2
        
        results.append({"case": case["id"], "score": score, "output": output})
    
    return aggregate(results)
```

### 6.3 Embedding Evaluation

```python
# evaluations/embedding_eval.py
def evaluate_embeddings():
    # Retrieval metrics
    queries = load_queries("evaluations/queries/")
    
    for query in queries:
        results = qdrant.search(query.vector, k=10, filter=query.filter)
        relevant = query.relevant_trade_ids
        
        precision_at_k = {k: precision_at_k(results, relevant, k) for k in [1,3,5,10]}
        recall_at_k = {k: recall_at_k(results, relevant, k) for k in [1,3,5,10]}
        mrr = mean_reciprocal_rank(results, relevant)
    
    # Semantic similarity (STS benchmark style)
    pairs = load_similarity_pairs()
    spearman = spearman_correlation(model_similarity, human_similarity)
    
    return {"retrieval": {...}, "similarity": spearman}
```

---

## 7. Continuous Learning / Retraining Pipeline

### 7.1 Trigger Conditions

- **Scheduled**: Weekly (Sunday) if new data > 1000 trades
- **Performance drift**: ECE > 0.08 or F1 drop > 0.03 vs baseline
- **New pattern discovery**: Manual trigger

### 7.2 Retraining Flow

```
New Trades (paper + video extracted)
        │
        ▼
Data Curation Agent
        │  - Deduplicate
        │  - Balance classes (SMOTE for rare patterns)
        │  - Split: train/val/test (purged, time-aware)
        │
        ▼
Training Job (after hours, GPU)
        │  - Config from experiment tracker
        │  - Mixed precision (BF16 on 5080)
        │  - Gradient accumulation (effective batch 256)
        │  - Early stopping (patience=10)
        │
        ▼
Validation
        │  - Full eval suite
        │  - Compare vs current production model
        │  - Statistical significance test (McNemar)
        │
        ▼
If Better (p < 0.05):
        │
        ├─► Export ONNX
        ├─► Convert TensorRT
        ├─► Register new version
        ├─► Canary deploy (10% traffic)
        └─► Full rollout after 1 day
Else:
        └─► Log, keep current
```

---

## 8. Cost & Resource Estimates

### 8.1 VRAM Budget Summary

| Scenario | Models Loaded | VRAM Used | Headroom |
|----------|---------------|-----------|----------|
| Market Hours | 5 core models | 7.5 GB | 8.5 GB |
| After Hours (video) | 6 video models | 7.1 GB | 8.9 GB |
| Training (vision) | Train + 2 core | 12-14 GB | 2-4 GB |
| Training (LLM LoRA) | Train + 2 core | 10-12 GB | 4-6 GB |

### 8.2 Model Storage

| Model | Format | Size |
|-------|--------|------|
| Vision Pattern (TRT) | .engine | ~40 MB |
| Vision Detect (TRT) | .engine | ~25 MB |
| Vision Keypoint (TRT) | .engine | ~35 MB |
| Reasoning LLM | .gguf | ~2.0 GB |
| Embed Text | .onnx | ~600 MB |
| STT Whisper | CT2 dir | ~3.0 GB |
| OCR | .onnx | ~50 MB |
| **Total** | | **~5.8 GB** |

---

## 9. Rollback Procedure

```bash
# 1. Identify issue (metrics alert, manual observation)
# 2. Check current version
cat models/registry.yaml | grep current_version

# 3. Rollback registry
# Edit registry.yaml: current_version = "previous_version"

# 4. Reload model (ModelManager hot-reload)
curl -X POST http://localhost:8080/admin/models/reload/vision_pattern

# 5. Verify health
curl http://localhost:8080/health/models/vision_pattern

# 6. Monitor metrics for 30 min
```

**Automated rollback**: If health check fails 3x in 5 min → auto-rollback to previous version.

---

## 10. Future Model Candidates

| Model | Purpose | Timeline | Notes |
|-------|---------|----------|-------|
| Vision Transformer (ViT) | Pattern classification | Q2 2025 | Better long-range, more VRAM |
| Llama-3.2-1B | Faster reasoning | Q1 2025 | 4x faster, slight quality drop |
| Phi-3.5-mini | Extraction alternative | Q1 2025 | 3.8B, strong structured output |
| YOLOv10 | Detection upgrade | Q2 2025 | Faster, same accuracy |
| Custom Indicator Net | Learned indicators | Q3 2025 | Replace hand-coded indicators |

---

**Document Version**: 1.0  
**Status**: DRAFT - Requires Human Approval  
**Next Step**: Development Roadmap