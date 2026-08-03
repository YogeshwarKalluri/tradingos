# TradingOS Architecture Document

## Overview

TradingOS is a personal AI-powered day trading platform specializing in momentum trading. Built as a **modular monolith** running entirely on a local AI workstation (AMD Ryzen 9 9950X, RTX 5080 16GB VRAM, 64GB DDR5, 2TB NVMe).

**Target Latency**: Scanner Event → Decision → Paper Trade in **< 1 second** during market hours.

---

## Core Design Principles

| Principle | Implementation |
|-----------|----------------|
| **Modular Monolith** | Single Python process, independent modules, shared memory, async event bus |
| **Zero Network Hops** | No REST/gRPC between modules; in-process async events only |
| **GPU-First** | Models loaded once at startup, kept in VRAM; zero-copy tensor sharing |
| **Minimal Serialization** | Pydantic models → memoryviews/NumPy views; avoid JSON in hot path |
| **Cache Aggressively** | Pre-computed indicators, chart images, embeddings cached in RAM |
| **Market Hours vs After Hours** | Heavy compute (learning, embeddings, video processing) ONLY after 4 PM ET |

---

## Folder Structure

```
TradingOS/
├── app/                          # Application entry points
│   ├── __init__.py
│   ├── main.py                   # Main entry point
│   ├── cli.py                    # CLI commands
│   └── lifecycle.py              # Startup/shutdown orchestration
│
├── core/                         # Core infrastructure (shared by all modules)
│   ├── __init__.py
│   ├── config.py                 # Configuration management (Pydantic Settings)
│   ├── event_bus.py              # In-process async event bus
│   ├── model_manager.py          # Model abstraction layer
│   ├── registry.py               # Module registry & dependency injection
│   ├── shared_memory.py          # Zero-copy shared memory pools
│   ├── state.py                  # Global application state
│   └── types.py                  # Shared type definitions (events, enums)
│
├── modules/                      # Independent trading modules
│   ├── __init__.py
│   │
│   ├── scanner/                  # Stock screening & detection
│   │   ├── __init__.py
│   │   ├── scanner.py            # Main scanner logic
│   │   ├── sources/              # Data sources (Polygon, Alpaca, Yahoo, etc.)
│   │   ├── filters/              # Momentum/volume/price filters
│   │   └── events.py             # StockDetected, FilterPassed events
│   │
│   ├── market_data/              # Real-time & historical market data
│   │   ├── __init__.py
│   │   ├── provider.py           # Unified data provider interface
│   │   ├── cache.py              # In-memory tick/bar cache
│   │   ├── websocket.py          # WebSocket connection manager
│   │   └── events.py             # TickEvent, BarEvent, QuoteEvent
│   │
│   ├── chart_builder/            # Chart construction & rendering
│   │   ├── __init__.py
│   │   ├── builder.py            # OHLCV → chart tensor
│   │   ├── renderer.py           # GPU-accelerated chart rendering (OpenGL/CUDA)
│   │   ├── timeframes.py         # Multi-timeframe synchronization
│   │   └── events.py             # ChartReady event
│   │
│   ├── technical_indicators/     # Technical analysis computations
│   │   ├── __init__.py
│   │   ├── engine.py             # Vectorized indicator engine (Numba/CUDA)
│   │   ├── indicators/           # Individual indicators (VWAP, RSI, MACD, etc.)
│   │   ├── cache.py              # Pre-computed indicator cache
│   │   └── events.py             # IndicatorsComputed event
│   │
│   ├── vision_engine/            # Chart pattern recognition (AI)
│   │   ├── __init__.py
│   │   ├── detector.py           # Pattern detection pipeline
│   │   ├── models/               # Vision model wrappers
│   │   ├── patterns/             # Pattern definitions & templates
│   │   └── events.py             # PatternDetected event
│   │
│   ├── memory_engine/            # Historical trade similarity search
│   │   ├── __init__.py
│   │   ├── store.py              # Vector store (Qdrant) + metadata (DuckDB)
│   │   ├── embedder.py           # Trade embedding generation
│   │   ├── retrieval.py          # Similarity search & reranking
│   │   └── events.py             # SimilarTradesFound event
│   │
│   ├── reasoning_engine/         # Multi-evidence decision making
│   │   ├── __init__.py
│   │   ├── reasoner.py           # Evidence aggregation & scoring
│   │   ├── models/               # Reasoning model wrappers
│   │   ├── templates/            # Prompt templates for different scenarios
│   │   └── events.py             # TradeDecision event
│   │
│   ├── risk_engine/              # Position sizing & risk management
│   │   ├── __init__.py
│   │   ├── sizer.py              # Kelly/volatility-based sizing
│   │   ├── limits.py             # Portfolio/position/sector limits
│   │   ├── validator.py          # Pre-trade risk checks
│   │   └── events.py             # RiskApproved, RiskRejected events
│   │
│   ├── execution_engine/         # Order management & paper trading
│   │   ├── __init__.py
│   │   ├── executor.py           # Order routing & management
│   │   ├── paper_broker.py       # Paper trading simulator
│   │   ├── live_broker.py        # Live broker interface (Alpaca, IBKR)
│   │   ├── oms.py                # Order management system
│   │   └── events.py             # OrderSubmitted, FillEvent events
│   │
│   ├── journal/                  # Trade logging & analysis
│   │   ├── __init__.py
│   │   ├── recorder.py           # Trade lifecycle recording
│   │   ├── analyzer.py           # Post-trade analysis
│   │   ├── schema.py             # Trade schema (DuckDB)
│   │   └── events.py             # TradeRecorded event
│   │
│   ├── learning/                 # Post-market learning pipeline
│   │   ├── __init__.py
│   │   ├── pipeline.py           # Daily learning orchestration
│   │   ├── video_processor.py    # Educational video → embeddings
│   │   ├── model_evaluator.py    # Model performance evaluation
│   │   ├── knowledge_base.py     # Knowledge graph updates
│   │   ├── report_generator.py   # Daily/weekly reports
│   │   └── scheduler.py          # After-hours cron scheduler
│   │
│   └── dashboard/                # Real-time UI (PyQt6/VisPy)
│       ├── __init__.py
│       ├── app.py                # Main dashboard application
│       ├── widgets/              # Reusable UI components
│       ├── charts/               # Real-time chart widgets
│       ├── panels/               # Scanner, positions, risk panels
│       └── events.py             # UI events
│
├── models/                       # Model definitions & management
│   ├── __init__.py
│   ├── vision/                   # Vision model configs
│   ├── reasoning/                # Reasoning model configs
│   ├── embedding/                # Embedding model configs
│   ├── speech/                   # Speech model configs
│   └── registry.py               # Model registry & versioning
│
├── database/                     # Database layer
│   ├── __init__.py
│   ├── duckdb/                   # Analytics & time-series
│   │   ├── __init__.py
│   │   ├── connection.py         # Connection pool
│   │   ├── schema.py             # Tables & views
│   │   └── queries.py            # Pre-compiled queries
│   │
│   ├── sqlite/                   # Application metadata
│   │   ├── __init__.py
│   │   ├── connection.py
│   │   └── schema.py
│   │
│   └── qdrant/                   # Vector search
│       ├── __init__.py
│       ├── client.py             # Qdrant client wrapper
│       ├── collections.py        # Collection management
│       └── search.py             # Search utilities
│
├── config/                       # Configuration files
│   ├── __init__.py
│   ├── settings.yaml             # Main settings
│   ├── models.yaml               # Model configurations
│   ├── risk.yaml                 # Risk parameters
│   ├── scanner.yaml              # Scanner filters
│   └── logging.yaml              # Logging configuration
│
├── utils/                        # Shared utilities
│   ├── __init__.py
│   ├── time.py                   # Market hours, timezone utilities
│   ├── math.py                   # Financial math helpers
│   ├── gpu.py                    # GPU memory management
│   ├── async_utils.py            # Async helpers
│   └── serialization.py          # Zero-copy serialization
│
├── tests/                        # Test suite
│   ├── __init__.py
│   ├── unit/                     # Unit tests per module
│   ├── integration/              # Integration tests
│   ├── performance/              # Latency benchmarks
│   ├── fixtures/                 # Test data
│   └── conftest.py               # Pytest configuration
│
├── docs/                         # Documentation
│   ├── architecture/             # Architecture decision records
│   ├── api/                      # Internal API docs
│   ├── deployment/               # Deployment guides
│   └── adr/                      # Architecture Decision Records
│
├── scripts/                      # Operational scripts
│   ├── __init__.py
│   ├── setup.py                  # Environment setup
│   ├── download_models.py        # Model downloading
│   ├── benchmark.py              # Performance benchmarking
│   ├── migrate_db.py             # Database migrations
│   └── daily_report.py           # Manual report generation
│
└── assets/                       # Static assets
    ├── icons/
    ├── fonts/
    ├── shaders/                  # GPU shaders for chart rendering
    └── templates/                # Report templates
```

---

## Module Responsibilities & Communication

### Event Flow (Market Hours - Hot Path)

```
┌─────────────┐     StockDetected      ┌──────────────┐
│  Scanner    │ ──────────────────────▶ │ Market Data  │
└─────────────┘                         └──────┬───────┘
                                               │ TickEvent/BarEvent
                                               ▼
┌─────────────┐     ChartReady         ┌──────────────┐
│   Vision    │ ◀────────────────────── │Chart Builder │
└──────┬──────┘                         └──────────────┘
       │ PatternDetected
       ▼
┌─────────────┐     SimilarTradesFound ┌──────────────┐
│  Memory     │ ◀────────────────────── │  Reasoning   │
└──────┬──────┘                         └──────┬───────┘
       │                                      │ TradeDecision
       ▼                                      ▼
┌─────────────┐     RiskApproved       ┌──────────────┐
│    Risk     │ ◀────────────────────── │  Execution   │
└──────┬──────┘                         └──────┬───────┘
       │                                      │ FillEvent
       ▼                                      ▼
┌─────────────┐     TradeRecorded      ┌──────────────┐
│   Journal   │ ◀────────────────────── │  Dashboard   │
└─────────────┘                         └──────────────┘
```

### Event Definitions (core/types.py)

```python
# Core event types - all use __slots__ for memory efficiency
class StockDetected(Event):
    symbol: str
    timestamp: int          # nanoseconds since epoch
    price: float
    volume: int
    scanner_id: str
    metadata: dict

class BarEvent(Event):
    symbol: str
    timeframe: Timeframe
    open: float
    high: float
    low: float
    close: float
    volume: int
    timestamp: int

class ChartReady(Event):
    symbol: str
    timeframe: Timeframe
    chart_tensor: memoryview  # Zero-copy GPU tensor view
    indicators: IndicatorsComputed

class PatternDetected(Event):
    symbol: str
    pattern_type: PatternType
    confidence: float
    bounding_box: tuple
    chart_tensor: memoryview

class SimilarTradesFound(Event):
    symbol: str
    current_setup: TradeSetup
    similar_trades: list[HistoricalTrade]
    similarity_scores: list[float]

class TradeDecision(Event):
    symbol: str
    action: Action  # BUY, SELL, HOLD
    confidence: float
    reasoning: str
    evidence: list[Evidence]
    position_size: float
    stop_loss: float
    take_profit: float

class RiskApproved(Event):
    decision: TradeDecision
    approved_size: float
    risk_metrics: RiskMetrics

class FillEvent(Event):
    order_id: str
    symbol: str
    side: Side
    quantity: float
    price: float
    timestamp: int
```

---

## Event Bus Design (core/event_bus.py)

```python
class EventBus:
    """
    In-process async event bus with zero-copy dispatch.
    - Subscribers: async callbacks
    - No serialization between modules
    - Priority queues for hot-path events
    - Backpressure handling via bounded queues
    """
    
    def __init__(self, max_queue_size: int = 10000):
        self._subscribers: dict[EventType, list[Subscriber]] = defaultdict(list)
        self._queues: dict[EventType, asyncio.Queue] = {}
        self._running = False
    
    def subscribe(self, event_type: type[Event], 
                  callback: Callable[[Event], Awaitable[None]],
                  priority: int = 0) -> Subscription:
        """Register async handler for event type."""
    
    async def publish(self, event: Event) -> None:
        """Publish event to all subscribers (fire-and-forget)."""
    
    async def publish_sync(self, event: Event) -> list[Any]:
        """Publish and await all handlers (for request-response)."""
```

**Performance Characteristics:**
- Dispatch latency: **< 10 µs** per event
- Zero allocations for hot-path events (pre-allocated event objects)
- Backpressure: bounded queues with drop-oldest policy for non-critical events

---

## Model Manager Abstraction (core/model_manager.py)

```python
class ModelManager:
    """
    Abstraction layer for all local AI models.
    - Loads models once at startup into VRAM
    - Provides unified inference interface
    - Supports hot-swapping models without restart
    - Manages GPU memory allocation
    """
    
    def __init__(self, config: ModelConfig):
        self._models: dict[str, BaseModel] = {}
        self._device = "cuda"
        self._stream = torch.cuda.Stream()
    
    def load_vision_model(self, name: str, config: VisionModelConfig) -> VisionModel:
        """Load vision model (e.g., YOLO, custom CNN, ViT)."""
    
    def load_reasoning_model(self, name: str, config: ReasoningModelConfig) -> ReasoningModel:
        """Load reasoning LLM (e.g., Llama-3, Nemotron, Qwen)."""
    
    def load_embedding_model(self, name: str, config: EmbeddingConfig) -> EmbeddingModel:
        """Load embedding model (e.g., BGE, E5, custom)."""
    
    def load_speech_model(self, name: str, config: SpeechConfig) -> SpeechModel:
        """Load speech model (Whisper, Piper, etc.)."""
    
    async def infer_vision(self, input: Tensor, model_name: str) -> VisionOutput:
        """Run vision inference on dedicated CUDA stream."""
    
    async def infer_reasoning(self, prompt: str, model_name: str) -> ReasoningOutput:
        """Run reasoning inference with KV cache optimization."""
    
    def get_gpu_memory_stats(self) -> GPUMemoryStats:
        """Monitor VRAM usage."""
```

**Supported Model Backends:**
- `llama.cpp` (GGUF) - CPU/GPU offloading
- `vLLM` - High-throughput LLM serving
- `TensorRT` - Optimized vision models
- `ONNX Runtime` - Cross-platform inference
- `PyTorch` native - Research/experimental models

---

## Database Design

### DuckDB (Analytics & Time-Series)

**Why DuckDB:**
- Columnar storage → 10-100x faster analytical queries
- Zero-copy NumPy/Pandas integration
- Embedded, no server process
- Excellent for OHLCV, indicators, trade analytics
- Supports parallel query execution

**Schema:**
```sql
-- Market data (partitioned by symbol + date)
CREATE TABLE bars (
    symbol VARCHAR,
    timeframe VARCHAR,
    timestamp BIGINT,
    open DOUBLE,
    high DOUBLE,
    low DOUBLE,
    close DOUBLE,
    volume BIGINT,
    vwap DOUBLE
) PARTITION BY (symbol, date_trunc('day', timestamp));

-- Pre-computed indicators (materialized views)
CREATE TABLE indicators (
    symbol VARCHAR,
    timeframe VARCHAR,
    timestamp BIGINT,
    indicator_name VARCHAR,
    value DOUBLE
);

-- Trade journal
CREATE TABLE trades (
    trade_id UUID PRIMARY KEY,
    symbol VARCHAR,
    entry_time BIGINT,
    exit_time BIGINT,
    side VARCHAR,
    entry_price DOUBLE,
    exit_price DOUBLE,
    quantity DOUBLE,
    pnl DOUBLE,
    setup_type VARCHAR,
    pattern_confidence DOUBLE,
    reasoning TEXT,
    risk_metrics JSON
);
```

### SQLite (Application Metadata)

**Why SQLite:**
- ACID transactions for settings, model configs, user preferences
- Single file, zero config
- WAL mode for concurrent reads

**Schema:**
```sql
CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT, updated_at INTEGER);
CREATE TABLE model_configs (name TEXT PRIMARY KEY, config JSON, version INTEGER);
CREATE TABLE scanner_configs (id TEXT PRIMARY KEY, config JSON, enabled BOOLEAN);
```

### Qdrant (Vector Search)

**Why Qdrant:**
- Native Rust, fast HNSW indexing
- Embedded mode (no separate server)
- Payload filtering + vector search in one query
- Supports quantization (scalar, binary) for memory efficiency
- GPU acceleration via CUDA

**Collections:**
```python
# Trade embeddings collection
COLLECTION_TRADES = {
    "name": "trade_embeddings",
    "vector_size": 1024,  # BGE-large / E5-large
    "distance": "Cosine",
    "hnsw_config": {"m": 16, "ef_construct": 200},
    "quantization": "scalar",  # 4x memory reduction
    "payload_schema": {
        "symbol": "keyword",
        "setup_type": "keyword",
        "entry_time": "integer",
        "pnl": "float",
        "pattern_confidence": "float",
    }
}

# Chart pattern embeddings
COLLECTION_PATTERNS = {
    "name": "pattern_embeddings",
    "vector_size": 512,
    "distance": "Cosine",
    "quantization": "binary",
}
```

---

## Performance Optimizations

### Hot Path (< 1s Target)

| Component | Optimization | Expected Latency |
|-----------|-------------|------------------|
| Scanner → Market Data | Shared memory ring buffer | < 100 µs |
| Market Data → Chart Builder | Pre-allocated GPU tensors | < 5 ms |
| Chart Builder → Vision | CUDA graph capture, TensorRT | < 50 ms |
| Vision → Memory | Async vector search (Qdrant) | < 20 ms |
| Memory → Reasoning | Batched inference, KV cache | < 200 ms |
| Reasoning → Risk | Pre-compiled risk rules | < 5 ms |
| Risk → Execution | Direct function call | < 1 ms |
| **Total** | | **~300 ms** |

### GPU Memory Management

```python
class GPUMemoryPool:
    """Pre-allocated GPU memory pools for zero-copy sharing."""
    
    def __init__(self):
        self._chart_pool: list[Tensor] = []      # Chart tensors (512x512x3)
        self._indicator_pool: list[Tensor] = []  # Indicator tensors
        self._embedding_pool: list[Tensor] = []  # Embedding outputs
    
    def acquire_chart_tensor(self) -> Tensor:
        """Get pre-allocated chart tensor from pool."""
    
    def release_chart_tensor(self, tensor: Tensor) -> None:
        """Return tensor to pool (no deallocation)."""
```

### Caching Strategy

| Cache | Size | TTL | Invalidation |
|-------|------|-----|--------------|
| Market data (ticks) | 100M ticks | Session | Market close |
| Indicators | 10M bars | Session | Recompute on param change |
| Chart images | 10K charts | 5 min | New bar |
| Embeddings | 1M vectors | Permanent | Model version change |
| Model KV cache | Dynamic | Session | Context length limit |

---

## After-Hours Learning Pipeline

```
┌─────────────────┐
│  Daily Scheduler │ (4:00 PM ET)
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│ Import Trades   │────▶│ Process Videos  │
│ (DuckDB → Qdrant)│     │ (Whisper → BGE) │
└─────────────────┘     └────────┬────────┘
         │                       │
         ▼                       ▼
┌─────────────────┐     ┌─────────────────┐
│ Evaluate Models │     │ Update Knowledge│
│ (Backtest, Metrics)│    │ Graph / Reports │
└─────────────────┘     └─────────────────┘
```

**No heavy processing during market hours** - all learning runs 4:00 PM - 8:00 AM ET.

---

## Phased Implementation Roadmap

### Phase 1: Foundation (Weeks 1-3)
- [ ] Project structure & config system
- [ ] Event bus + core types
- [ ] Model manager abstraction
- [ ] DuckDB + SQLite + Qdrant setup
- [ ] Market data provider (Polygon/Alpaca websocket)
- [ ] Basic scanner with 3 filters
- [ ] Unit test framework + CI

### Phase 2: Core Pipeline (Weeks 4-6)
- [ ] Chart builder with GPU rendering
- [ ] Technical indicator engine (Numba/CUDA)
- [ ] Vision engine (pattern detection)
- [ ] Memory engine (embeddings + search)
- [ ] Reasoning engine (evidence aggregation)
- [ ] Risk engine (sizing + limits)
- [ ] Paper execution engine
- [ ] Journal recorder

### Phase 3: Intelligence (Weeks 7-9)
- [ ] Multi-timeframe chart analysis
- [ ] Advanced patterns (VWAP reclaim, ORB, etc.)
- [ ] Reasoning model fine-tuning pipeline
- [ ] Learning pipeline (video → embeddings)
- [ ] Daily report generation
- [ ] Model evaluation framework

### Phase 4: Dashboard & Polish (Weeks 10-12)
- [ ] Real-time PyQt6/VisPy dashboard
- [ ] Scanner panel, chart panel, positions panel
- [ ] Risk monitoring panel
- [ ] Trade review interface
- [ ] Performance profiling & optimization
- [ ] Documentation & ADRs

### Phase 5: Production Hardening (Weeks 13-16)
- [ ] Live broker integration (Alpaca/IBKR)
- [ ] Failover & recovery
- [ ] Comprehensive integration tests
- [ ] Latency benchmarking (< 1s p99)
- [ ] Stress testing (1000+ symbols)
- [ ] Security audit

---

## Architecture Decision Records (ADRs)

| ADR | Title | Status |
|-----|-------|--------|
| 001 | Modular Monolith over Microservices | Accepted |
| 002 | DuckDB for Analytics, SQLite for Metadata | Accepted |
| 003 | Qdrant Embedded for Vector Search | Accepted |
| 004 | Async Event Bus over Direct Calls | Accepted |
| 005 | Model Manager Abstraction | Accepted |
| 006 | GPU-First Chart Rendering | Accepted |
| 007 | Market Hours vs After-Hours Separation | Accepted |
| 008 | Zero-Copy Tensor Sharing | Accepted |

---

## Risk Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| GPU OOM during market hours | Medium | High | Pre-allocated pools, model offloading, memory monitoring |
| Data feed latency spikes | Medium | High | Local cache, multiple provider failover |
| Model hallucination in reasoning | Medium | High | Confidence thresholds, evidence citation, human review |
| Qdrant index corruption | Low | High | Daily backups, WAL, embedded mode durability |
| Overfitting in learning | Medium | Medium | Walk-forward validation, out-of-sample testing |
| Single point of failure | High | High | Checkpointing, fast restart (< 5s), state persistence |

---

## Future Scalability

| Dimension | Current | Target | Path |
|-----------|---------|--------|------|
| Symbols tracked | 500 | 5000 | Partitioned scanners, distributed cache |
| Event throughput | 10K/s | 1M/s | Rust hot-path modules, io_uring |
| Model size | 7B | 70B+ | Multi-GPU, tensor parallelism |
| Latency (p99) | 300ms | 100ms | Custom CUDA kernels, FP8 quantization |
| Data history | 2 years | 10+ years | Tiered storage (NVMe → HDD) |

---

## Configuration Example (config/settings.yaml)

```yaml
app:
  name: "TradingOS"
  environment: "development"  # development, paper, live
  timezone: "America/New_York"
  
market_hours:
  pre_market: "04:00"
  regular_open: "09:30"
  regular_close: "16:00"
  post_market: "20:00"
  learning_window: "16:00-08:00"

scanner:
  enabled: true
  max_symbols: 500
  scan_interval_ms: 1000
  filters:
    - name: "volume_spike"
      min_relative_volume: 2.0
    - name: "price_momentum"
      min_change_pct: 1.5
    - name: "float_filter"
      max_float_m: 50

market_data:
  primary: "polygon"
  fallback: "alpaca"
  websocket:
    reconnect_interval: 5
    max_messages_per_second: 10000
  cache:
    max_ticks_per_symbol: 100000
    max_bars_per_symbol: 10000

chart_builder:
  renderer: "cuda"  # cuda, opengl, cpu
  default_timeframes: ["1m", "5m", "15m", "1h", "1d"]
  chart_resolution: [512, 512]
  gpu_memory_pool_mb: 512

technical_indicators:
  engine: "numba_cuda"
  default_indicators:
    - vwap
    - ema_9
    - ema_20
    - rsi_14
    - macd
    - bollinger_bands
    - atr_14
  cache_size_mb: 1024

vision_engine:
  model: "yolo_v8_custom"
  confidence_threshold: 0.7
  patterns:
    - bull_flag
    - bear_flag
    - cup_handle
    - double_bottom
    - vwap_reclaim
    - opening_range_breakout
  batch_size: 8
  inference_timeout_ms: 50

memory_engine:
  vector_store: "qdrant"
  embedding_model: "bge-large-en-v1.5"
  top_k: 20
  similarity_threshold: 0.75
  rerank: true

reasoning_engine:
  model: "nemotron-3-ultra"
  max_context_tokens: 8192
  temperature: 0.1
  evidence_weights:
    pattern: 0.3
    indicators: 0.2
    historical: 0.3
    volume: 0.2

risk_engine:
  max_position_pct: 0.05
  max_portfolio_risk: 0.02
  max_daily_loss: 0.01
  max_sector_exposure: 0.20
  kelly_fraction: 0.25
  stop_loss_atr_multiple: 2.0

execution_engine:
  mode: "paper"  # paper, live
  paper:
    starting_capital: 100000
    commission_per_share: 0.005
    min_commission: 1.0
    slippage_bps: 5
  live:
    broker: "alpaca"
    api_key_env: "ALPACA_API_KEY"
    secret_env: "ALPACA_SECRET"

journal:
  storage: "duckdb"
  auto_export: true
  export_format: "parquet"

learning:
  enabled: true
  video_sources: []
  model_evaluation:
    metrics: ["sharpe", "sortino", "max_drawdown", "win_rate"]
  report_schedule: "daily"

dashboard:
  enabled: true
  host: "127.0.0.1"
  port: 8080
  update_interval_ms: 100
  theme: "dark"

logging:
  level: "INFO"
  format: "json"
  file: "logs/tradingos.log"
  max_size_mb: 100
  backup_count: 10

model_manager:
  device: "cuda"
  gpu_memory_fraction: 0.85
  models:
    vision:
      name: "yolo_v8_custom"
      path: "models/vision/yolo_v8_custom.engine"
      backend: "tensorrt"
    reasoning:
      name: "nemotron-3-ultra"
      path: "models/reasoning/nemotron-3-ultra.Q4_K_M.gguf"
      backend: "llama_cpp"
      context_size: 8192
      gpu_layers: -1
    embedding:
      name: "bge-large-en-v1.5"
      path: "models/embedding/bge-large-en-v1.5"
      backend: "onnx"
    speech:
      name: "whisper-large-v3"
      path: "models/speech/whisper-large-v3"
      backend: "faster_whisper"
```

---

## Next Steps

1. **Review this architecture** - Challenge assumptions, suggest improvements
2. **Approve or request changes** - Once approved, we proceed to Phase 1 implementation
3. **Set up development environment** - Run `scripts/setup.py`
4. **Download models** - Run `scripts/download_models.py`
5. **Begin Phase 1 implementation**

---

*This architecture is designed for a single-user, local-first, high-performance trading workstation. Every decision optimizes for latency, GPU utilization, and maintainability over distributed systems concerns.*