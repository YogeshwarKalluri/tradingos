# TradingOS Complete System Architecture

## Overview

This document describes the complete system architecture for TradingOS - a local AI-powered momentum day trading platform. The architecture follows a **modular monolith** pattern with async event-driven communication, optimized for the target hardware (Ryzen 9 9950X, RTX 5080 16GB, 64GB RAM).

---

## 1. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            TRADINGOS PROCESS                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        EVENT BUS (asyncio)                          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│          │                    │                    │                    │   │
│  ┌───────▼───────┐    ┌───────▼───────┐    ┌───────▼───────┐    ┌───────▼───────┐
│  │  SCANNER      │    │  MARKET DATA  │    │  CHART ENGINE │    │  INDICATOR    │
│  │  MODULE       │    │  MODULE       │    │  MODULE       │    │  ENGINE       │
│  └───────┬───────┘    └───────┬───────┘    └───────┬───────┘    └───────┬───────┘
│          │                    │                    │                    │   │
│          └────────────────────┼────────────────────┼────────────────────┘   │
│                               ▼                    ▼                        │
│                    ┌─────────────────────────────────────────────┐         │
│                    │           VISION ENGINE                      │         │
│                    │  (RTX 5080 - TensorRT Optimized Models)     │         │
│                    └─────────────────────┬───────────────────────┘         │
│                                          │                                │
│                    ┌─────────────────────▼───────────────────────┐         │
│                    │           MEMORY ENGINE                      │         │
│                    │  Qdrant (vectors) + DuckDB (structured)     │         │
│                    └─────────────────────┬───────────────────────┘         │
│                                          │                                │
│                    ┌─────────────────────▼───────────────────────┐         │
│                    │           REASONING ENGINE                   │         │
│                    │  Evidence Aggregation → TradeThesis         │         │
│                    └─────────────────────┬───────────────────────┘         │
│                                          │                                │
│                    ┌─────────────────────▼───────────────────────┐         │
│                    │           RISK ENGINE                        │         │
│                    │  Hard Rules + Dynamic Rules → Decision      │         │
│                    └─────────────────────┬───────────────────────┘         │
│                                          │                                │
│          ┌───────────────────────────────┼───────────────────────────────┐│
│          ▼                               ▼                               ▼│
│  ┌───────────────┐              ┌───────────────┐              ┌───────────────┐
│  │  EXECUTION    │              │   JOURNAL     │              │  DASHBOARD    │
│  │  ENGINE       │              │   MODULE      │              │  MODULE       │
│  │  (Paper/Live) │              │  (Immutable)  │              │  (WebSocket)  │
│  └───────────────┘              └───────────────┘              └───────────────┘
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    LEARNING PIPELINE (After Hours)                  │   │
│  │  Video → STT → Frames → OCR → Trade Extraction → Embeddings → KB   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    EVALUATION FRAMEWORK                              │   │
│  │  Pattern Metrics │ Calibration │ Trading Metrics │ System Metrics  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Module Specifications

### 2.1 Core Infrastructure

#### Event Bus (`core/events/`)
- **Implementation**: `asyncio` native with `asyncio.Queue` per subscriber
- **Pattern**: Publish-subscribe with typed events (Pydantic models)
- **No external broker**: In-process, zero-copy where possible
- **Event Types**:
  ```python
  StockDetected(candidate: StockCandidate)
  MarketDataReady(candidate: StockCandidate, data: MarketData)
  ChartReady(candidate: StockCandidate, tensor: ChartTensor)
  VisionResult(candidate: StockCandidate, result: VisionOutput)
  MemoryResults(candidate: StockCandidate, trades: List[HistoricalTrade])
  ThesisReady(candidate: StockCandidate, thesis: TradeThesis)
  RiskDecision(candidate: StockCandidate, decision: RiskDecision)
  OrderSubmitted(order: Order)
  FillReceived(fill: Fill)
  ```

#### Configuration (`core/config/`)
- **Format**: YAML with Pydantic Settings validation
- **Environment-specific**: `config/base.yaml`, `config/development.yaml`, `config/production.yaml`
- **Hot reload**: File watcher with debounced reload (non-market hours only)

#### Logging (`core/logging/`)
- **Structured**: JSON Lines to file + colored console
- **Levels**: TRACE, DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Correlation IDs**: Every event carries `trace_id` for distributed tracing
- **Performance**: `structlog` + `orjson` for speed

#### Model Manager (`core/models/`)
- **Interface**: Abstract base class `BaseModel` with `load()`, `infer()`, `unload()`, `warmup()`
- **Registry**: Model name → (loader_fn, config, metadata)
- **VRAM Budget**: Enforces 14GB limit, auto-unloads LRU models
- **Formats**: GGUF (llama.cpp), ONNX (ORT), TensorRT engines
- **Warmup**: Pre-loads all market-hours models at 9:00 AM

---

### 2.2 Scanner Module (`modules/scanner/`)

```
Scanner Input Sources:
├── File Watch (JSON Lines)
├── REST Webhook (FastAPI endpoint)
├── IPC (named pipe / Unix socket)
└── Manual CLI injection
```

**Flow**:
1. Receive raw candidate → validate schema
2. Deduplicate (ticker + timestamp window)
3. Enrich with static data (float, sector) from local cache
4. Score priority: `RVol * Gap% * (1/Float) * TimeOfDayWeight`
5. Emit `StockDetected` event

**Data Model**:
```python
class StockCandidate:
    ticker: str
    timestamp: datetime
    price: float
    gap_pct: float
    rel_volume: float
    float_shares: int
    source: str
    priority_score: float
    metadata: Dict
```

---

### 2.3 Market Data Module (`modules/market/`)

**Storage**: DuckDB with partitioned tables
```
market_data/
├── ohlcv_1m/     (partitioned by date)
├── ohlcv_5m/
├── ohlcv_15m/
├── ohlcv_1h/
├── ohlcv_daily/
├── level2_snapshots/  (on-demand)
├── news/              (partitioned by date)
└── fundamentals/      (float, shares_outstanding, etc.)
```

**Data Sources** (priority order):
1. Local cache (DuckDB) - < 5ms
2. Polygon.io WebSocket - real-time
3. Alpaca WebSocket - backup
4. IQFeed - tertiary (if available)

**Gap Handling**:
- Detect missing bars > 5 minutes
- Mark as `interpolated=True` in cache
- Emit `DataQualityWarning` event

---

### 2.4 Chart Engine (`modules/charts/`)

**Rendering Pipeline** (CPU → GPU tensor, no disk):
```
OHLCV Arrays (NumPy)
    │
    ├─► Normalize (price → 0-1, volume → 0-1)
    │
    ├─► Multi-timeframe stack: [1m, 5m, 15m, daily] → (4, H, W, 3)
    │       Each: Candlestick (OHLC) + Volume + VWAP + EMA(9,20,50)
    │
    ├─► GPU Transfer (pinned memory → VRAM)
    │
    └─► Output: ChartTensor (torch.Tensor on CUDA, shape [4, 256, 256, 3])
```

**Optimization**:
- Pre-allocated ring buffers for streaming updates
- Numba JIT for coordinate transforms
- Single CUDA kernel for all overlays
- **Target**: < 30ms end-to-end

---

### 2.5 Indicator Engine (`modules/indicators/`)

**All vectorized NumPy/Numba** (no TA-Lib):
```python
# Example: Incremental VWAP
@njit
def update_vwap(cum_pv: float, cum_vol: float, price: float, vol: float) -> Tuple[float, float]:
    return cum_pv + price * vol, cum_vol + vol

# Vectorized batch for historical
def compute_vwap(high, low, close, volume):
    typical = (high + low + close) / 3
    return np.cumsum(typical * volume) / np.cumsum(volume)
```

**Indicators**: VWAP, EMA(9,20,50,200), ATR(14), RSI(14), RVol, Gap%, Float turnover
**Output**: `IndicatorSnapshot` dataclass with all values + metadata

---

### 2.6 Vision Engine (`modules/vision/`)

**Model Strategy**:
| Pattern | Model | Format | VRAM | Latency |
|---------|-------|--------|------|---------|
| Pattern Classification | Custom CNN (EfficientNet-B0) | TensorRT FP16 | ~2GB | ~50ms |
| Object Detection (candles, indicators) | YOLOv8n | TensorRT FP16 | ~1GB | ~30ms |
| Keypoint (support/resistance) | HRNet-W18 | TensorRT FP16 | ~1.5GB | ~40ms |
| **Total** | | | **~4.5GB** | **~120ms** |

**Pipeline**:
```
ChartTensor (4, 256, 256, 3)
    │
    ├─► Pattern Classifier → probs[8 classes]
    │
    ├─► Object Detector → boxes[candles, volume, vwap, emas]
    │
    ├─► Keypoint Detector → keypoints[support, resistance, vwap_touch]
    │
    └─► Post-process → VisionOutput
```

**VisionOutput**:
```python
@dataclass
class VisionOutput:
    pattern_probs: Dict[str, float]  # 8 patterns
    detected_objects: List[DetectedObject]
    keypoints: List[Keypoint]
    confidence: float  # max pattern prob
    inference_ms: float
```

---

### 2.7 Memory Engine (`modules/memory/`)

**Dual Storage**:
```
Qdrant (Embedded)
├── Collection: trade_embeddings (768-dim, HNSW)
│   ├── Vector: Combined embedding (chart + text + indicators)
│   ├── Payload: trade_id, ticker, date, pattern, outcome, metadata
│   └── Filterable fields: ticker, pattern, date_range, outcome, market_cap

DuckDB (Structured)
├── Table: trades (trade_id PK, all structured fields)
├── Table: trade_charts (trade_id, chart_blob_compressed)
└── Table: trade_transcripts (trade_id, transcript_text)
```

**Search Strategy**:
```python
async def search_similar(candidate: StockCandidate, vision: VisionOutput, 
                         indicators: IndicatorSnapshot, k: int = 10) -> List[HistoricalTrade]:
    # 1. Build query embedding from candidate + vision + indicators
    query_vec = embedder.encode([candidate, vision, indicators])
    
    # 2. Vector search with filters
    vector_results = qdrant.search(
        collection="trade_embeddings",
        query_vector=query_vec,
        query_filter=Filter(
            must=[...],  # e.g., same pattern, similar market cap
            should=[...]  # similar RVol, gap%
        ),
        limit=k * 2
    )
    
    # 3. Fetch full records from DuckDB
    trade_ids = [r.id for r in vector_results]
    trades = duckdb.query("SELECT * FROM trades WHERE trade_id IN ?", trade_ids)
    
    # 4. Re-rank with structured similarity
    return rerank(trades, candidate, vision, indicators)[:k]
```

**Latency Target**: < 50ms (vector search ~20ms, DuckDB fetch ~10ms, rerank ~10ms)

---

### 2.8 Reasoning Engine (`modules/reasoning/`)

**Evidence Aggregation**:
```python
@dataclass
class Evidence:
    source: Literal["vision", "indicators", "memory", "market_context", "news"]
    claim: str
    value: Any
    confidence: float
    weight: float

@dataclass
class TradeThesis:
    candidate: StockCandidate
    vision: VisionOutput
    indicators: IndicatorSnapshot
    similar_trades: List[HistoricalTrade]
    evidence: List[Evidence]
    confidence: float  # weighted aggregate
    direction: Literal["LONG", "SHORT", "PASS"]
    entry_zone: Tuple[float, float]
    stop_loss: float
    targets: List[float]
    position_size: float
    risk_factors: List[str]
    reasoning_text: str  # Human-readable explanation
```

**Confidence Calculation**:
```
confidence = weighted_sum(
    vision_confidence * 0.30,
    indicator_confluence * 0.20,
    historical_win_rate * 0.25,
    risk_reward_ratio * 0.15,
    market_context * 0.10
)
```

**No LLM in hot path** - all deterministic. LLM only for `reasoning_text` generation (async, non-blocking).

---

### 2.9 Risk Engine (`modules/risk/`)

**Hard Rules** (Config-driven, non-negotiable):
```yaml
risk:
  hard_rules:
    max_position_pct: 0.10          # 10% of equity per trade
    max_daily_loss_pct: 0.02        # 2% daily loss limit
    max_drawdown_pct: 0.05          # 5% intraday drawdown
    max_open_positions: 3
    min_risk_reward: 1.5
    max_hold_minutes: 240           # 4 hours max
    forbidden_tickers: []           # Hardcoded blocklist
    forbidden_hours: [16, 17, 18]   # No new entries after 4PM
```

**Dynamic Rules**:
- Volatility-adjusted sizing: `size = base_size * (ATR_reference / ATR_current)`
- Correlation limit: max 2 positions in same sector
- Time-of-day: reduce size after 11AM, zero after 2PM
- Daily loss circuit breaker: halt all new entries

**Output**:
```python
@dataclass
class RiskDecision:
    approved: bool
    reason: str  # Specific rule if rejected
    adjusted_size: float
    adjusted_stop: float
    adjusted_targets: List[float]
    warnings: List[str]
```

---

### 2.10 Execution Engine (`modules/execution/`)

**Paper Trading Mode** (MVP):
- Simulated order book with configurable slippage model
- Latency simulation: `base_latency + random(0, 50ms)`
- Slippage: `spread * 0.5 + volatility * size_factor`
- Partial fills for large size relative to volume

**Live Trading Mode** (Phase 7+):
- Abstract `BrokerAdapter` interface
- Implementations: `AlpacaAdapter`, `IBKRAdapter`
- Order types: Market, Limit, Stop, Stop-Limit, Trail
- Bracket orders: Entry + Stop + Target(s)

---

### 2.11 Journal Module (`modules/journal/`)

**Storage**: Append-only JSONL + DuckDB index
```
journal/
├── decisions/      # Every thesis + decision (JSONL, partitioned by date)
├── fills/          # Execution records
├── outcomes/       # Post-trade analysis (filled after close)
└── index.duckdb    # Queryable index
```

**Schema** (Decision Record):
```json
{
  "trace_id": "uuid",
  "timestamp": "ISO8601",
  "candidate": {...},
  "thesis": {...},
  "risk_decision": {...},
  "execution": {...},  // null if rejected
  "outcome": {...},    // null until resolved
  "post_analysis": {...}  // filled after market close
}
```

---

### 2.12 Video Learning Pipeline (`modules/video/`)

```
┌────────────────────────────────────────────────────────────────────────┐
│                    VIDEO PROCESSING PIPELINE                            │
└────────────────────────────────────────────────────────────────────────┘

Input: knowledge/ross_videos/inbox/*.mp4
         │
         ▼
┌────────────────────────────────────────────────────────────────────┐
│ 1. VIDEO PROCESSOR (ffmpeg)                                         │
│    - Extract audio → WAV (16kHz mono)                               │
│    - Extract keyframes @ 1fps → frames/                             │
│    - Detect scene changes (chart vs face vs slides)                 │
└────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────────────────┐
│ 2. SPEECH-TO-TEXT (faster-whisper large-v3, CUDA)                 │
│    - Transcript with word-level timestamps                          │
│    - Speaker diarization (Ross vs chat vs alerts)                   │
└────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────────────────┐
│ 3. TIMESTAMP ALIGNMENT                                              │
│    - Map transcript segments → video timestamps                     │
│    - Identify trade discussion windows                              │
└────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────────────────┐
│ 4. CHART FRAME EXTRACTION                                           │
│    - Classify frames: chart / non-chart (CNN)                       │
│    - Extract chart regions (YOLO)                                   │
│    - OCR: ticker, timeframe, price, indicators (PaddleOCR)          │
└────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────────────────┐
│ 5. TRADE EVENT DETECTION                                            │
│    - Parse transcript for: "buy", "sell", "entry", "exit", "stop"  │
│    - Align with chart frames at same timestamp                      │
│    - Extract: ticker, entry, stop, target, size, reasoning          │
└────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────────────────┐
│ 6. PATTERN LABELING                                                 │
│    - Run Vision Engine on extracted charts                          │
│    - Human review queue for low-confidence                          │
│    - Store: pattern, setup quality, outcome                         │
└────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────────────────┐
│ 7. EMBEDDING GENERATION                                             │
│    - Text embedding: transcript segment (BGE-large-en-v1.5)         │
│    - Chart embedding: Vision Engine features                        │
│    - Combined: weighted concat → 768-dim                            │
└────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────────────────┐
│ 8. KNOWLEDGE BASE INSERT                                            │
│    - Qdrant: vector + payload                                       │
│    - DuckDB: structured trade record                                │
│    - Link to source video + timestamp                               │
└────────────────────────────────────────────────────────────────────┘
```

**Automation**: File watcher on `inbox/` → moves to `processing/` → `done/` or `failed/`

---

### 2.13 Evaluation Framework (`evaluations/`)

**Automated Nightly Run** (after market close):
```python
# evaluations/run_nightly.py
async def run_evaluation():
    # 1. Pattern Detection Metrics
    precision, recall, f1 = evaluate_pattern_detection(ground_truth, predictions)
    
    # 2. Calibration
    ece, reliability_diagram = evaluate_calibration(predictions, outcomes)
    
    # 3. Trading Metrics
    expectancy, pf, max_dd, sharpe = compute_trading_metrics(paper_trades)
    
    # 4. System Metrics
    latencies = collect_latency_percentiles()
    gpu_util = collect_gpu_metrics()
    
    # 5. Persist & Report
    save_results(metrics)
    generate_html_report(metrics)
    alert_if_degraded(metrics)
```

**Metrics Tracked**:
| Category | Metrics |
|----------|---------|
| Pattern Detection | Precision/Recall/F1 per class, Confusion Matrix |
| Calibration | ECE, MCE, Reliability Diagrams, Brier Score |
| Trading | Expectancy, Profit Factor, Win Rate, Avg Win/Loss, Max DD, Sharpe, Sortino |
| System | Latency p50/p95/p99 per stage, GPU%, VRAM%, CPU%, Memory% |

---

### 2.14 Dashboard Module (`modules/dashboard/`)

**Architecture**: FastAPI + HTMX (server-rendered, minimal JS)
- **WebSocket** for real-time updates
- **Endpoints**:
  - `GET /` - Main dashboard
  - `GET /scanner` - Live scanner feed
  - `GET /charts/{ticker}` - Chart with overlays
  - `GET /search` - Historical trade search
  - `GET /positions` - Paper positions
  - `GET /performance` - Analytics
  - `WS /ws` - Real-time events

**No React/SPA complexity** - HTMX fragments swapped via WebSocket

---

## 3. Data Flow Details

### 3.1 Market Hours Hot Path (Scanner → Decision)

```
Scanner Input
     │  (< 10ms)
     ▼
StockDetected Event
     │
     ├─► Market Data Module (parallel)
     │       │  (< 50ms cached)
     │       ▼
     │   MarketDataReady Event
     │
     ├─► Chart Engine (parallel)
     │       │  (< 30ms)
     │       ▼
     │   ChartReady Event
     │
     ├─► Indicator Engine (parallel)
     │       │  (< 5ms)
     │       ▼
     │   IndicatorsReady Event
     │
     ▼ (when all 3 ready)
Vision Engine
     │  (< 200ms)
     ▼
VisionResult Event
     │
     ▼
Memory Engine
     │  (< 50ms)
     ▼
MemoryResults Event
     │
     ▼
Reasoning Engine
     │  (< 100ms)
     ▼
ThesisReady Event
     │
     ▼
Risk Engine
     │  (< 10ms)
     ▼
RiskDecision Event
     │
     ▼
Execution Engine (if approved)
     │  (< 100ms)
     ▼
OrderSubmitted / FillReceived Events
     │
     ▼
Journal Module (async, non-blocking)
```

**Total Target**: < 500ms (well under 1 second budget)

---

### 3.2 After-Hours Learning Pipeline

```
File Watcher (inbox/)
     │
     ▼
VideoProcessor (sequential, one at a time)
     │
     ├─► Audio Extraction (ffmpeg)
     │
     ├─► Frame Extraction (ffmpeg, 1fps)
     │
     ▼
STT Processor (faster-whisper, batched)
     │
     ▼
Timestamp Aligner
     │
     ▼
Chart Frame Classifier + OCR (batched)
     │
     ▼
Trade Event Extractor (LLM-assisted, local)
     │
     ▼
Vision Engine (pattern labeling)
     │
     ▼
Embedding Generator
     │
     ▼
Knowledge Base Writer (Qdrant + DuckDB)
     │
     ▼
Evaluation Update (incremental metrics)
```

---

## 4. Database Design

### 4.1 DuckDB Schema

```sql
-- Market Data
CREATE TABLE ohlcv_1m (
    ticker VARCHAR,
    ts TIMESTAMP,
    open DOUBLE, high DOUBLE, low DOUBLE, close DOUBLE, volume BIGINT,
    vwap DOUBLE,
    interpolated BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (ticker, ts)
) PARTITION BY (YEAR(ts), MONTH(ts));

-- Trades (Structured)
CREATE TABLE trades (
    trade_id UUID PRIMARY KEY,
    ticker VARCHAR,
    entry_time TIMESTAMP,
    exit_time TIMESTAMP,
    direction VARCHAR,  -- LONG/SHORT
    entry_price DOUBLE,
    exit_price DOUBLE,
    stop_loss DOUBLE,
    target_1 DOUBLE,
    target_2 DOUBLE,
    position_size DOUBLE,
    pnl DOUBLE,
    pattern VARCHAR,
    setup_quality INTEGER,  -- 1-5
    market_condition VARCHAR,
    source VARCHAR,  -- 'paper', 'live', 'ross_video'
    video_source VARCHAR,
    video_timestamp DOUBLE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Journal Decisions
CREATE TABLE journal_decisions (
    trace_id UUID PRIMARY KEY,
    timestamp TIMESTAMP,
    candidate_json JSON,
    thesis_json JSON,
    risk_decision_json JSON,
    execution_json JSON,
    outcome_json JSON,
    post_analysis_json JSON
);

-- Video Processing Log
CREATE TABLE video_processing_log (
    video_id UUID PRIMARY KEY,
    filename VARCHAR,
    status VARCHAR,  -- 'pending', 'processing', 'done', 'failed'
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    trades_extracted INTEGER,
    error_message VARCHAR
);
```

### 4.2 Qdrant Collection

```python
# Collection: trade_embeddings
# Vector: 768-dim (BGE-large-en-v1.5 + vision features)
# HNSW Index: M=16, ef_construct=200
# Payload Schema:
{
    "trade_id": "uuid",
    "ticker": "string",
    "entry_time": "datetime",
    "pattern": "string",
    "direction": "string",
    "outcome": "string",  # "win", "loss", "breakeven"
    "pnl": "float",
    "setup_quality": "integer",
    "market_cap": "float",
    "float_shares": "integer",
    "rel_volume": "float",
    "gap_pct": "float",
    "source": "string",
    "video_source": "string",
    "video_timestamp": "float"
}
# Filterable: ticker, pattern, direction, outcome, source, date ranges, numeric ranges
```

---

## 5. AI Model Strategy

### 5.1 Model Registry

| Role | Model | Format | VRAM | Purpose |
|------|-------|--------|------|---------|
| Vision: Pattern Classifier | Custom EfficientNet-B0 | TensorRT FP16 | 2GB | 8-pattern classification |
| Vision: Object Detection | YOLOv8n | TensorRT FP16 | 1GB | Candle/indicator detection |
| Vision: Keypoints | HRNet-W18 | TensorRT FP16 | 1.5GB | S/R, VWAP touch points |
| Embedding: Text | BGE-large-en-v1.5 | ONNX FP16 | 1GB | Transcript/trade embedding |
| Embedding: Chart | Vision features (pooled) | - | 0GB | From vision models |
| Reasoning: Text Gen | Llama-3.2-3B-Instruct | GGUF Q4_K_M | 2GB | Thesis explanation |
| STT | faster-whisper large-v3 | CT2 FP16 | 3GB | Video transcription |
| OCR | PaddleOCR PP-OCRv4 | ONNX FP16 | 0.5GB | Chart text extraction |
| **Total (Market Hours)** | | | **~7.5GB** | **Leaves 8.5GB headroom** |

### 5.2 Model Manager Policies

```yaml
model_manager:
  vram_budget_gb: 14
  market_hours_models:
    - vision_pattern_classifier
    - vision_object_detector
    - vision_keypoints
    - reasoning_text_gen  # kept warm for explanations
  after_hours_models:
    - stt_whisper
    - ocr_paddle
    - embedding_text
  swap_policy: LRU
  warmup_at: "09:00"
  cooldown_at: "16:30"
```

---

## 6. Deployment & Operations

### 6.1 Process Management
- Single Python process (`python -m tradingos`)
- Subprocesses only for: ffmpeg (video), GPU model servers (optional)
- Systemd/Windows Service for auto-start
- Health endpoint: `GET /health` (liveness + readiness)

### 6.2 Market Hours Protocol
```
08:30  Pre-market: Start process, load models, warm caches
09:00  Models fully loaded, warmup complete
09:30  MARKET OPEN - Hot path active
16:00  MARKET CLOSE - Stop accepting new candidates
16:15  Flush journals, compute preliminary metrics
16:30  Unload market-hours models, load after-hours models
17:00  Video processing begins
22:00  Evaluation run, report generation
23:00  Backup, cleanup, prepare for next day
```

### 6.3 Monitoring
- **Prometheus metrics** exposed at `:9090/metrics`
- **Grafana dashboards** for: latency, GPU, trading P&L, model performance
- **Alerts**: Latency > 1s, GPU OOM, Daily loss > 1%, Data gaps

---

## 7. Security

- **No external network access** during market hours (except market data WebSockets)
- **API keys**: Encrypted in config (age/rage), loaded at startup only
- **Broker credentials**: Never logged, memory-only
- **Journal encryption**: Optional AES-256 for PII
- **Code signing**: All dependencies pinned, verified hashes

---

## 8. Development Phases

| Phase | Modules | Duration | Deliverable |
|-------|---------|----------|-------------|
| 1 | Core, Events, Config, Logging, Model Manager | 2 weeks | Running skeleton |
| 2 | Scanner, Market Data, Chart Engine, Indicators | 3 weeks | Data pipeline |
| 3 | Vision Engine (inference only), Memory Engine | 4 weeks | AI inference |
| 4 | Reasoning, Risk, Execution (Paper), Journal | 3 weeks | Decision loop |
| 5 | Dashboard, Evaluation Framework | 2 weeks | Observability |
| 6 | Video Learning Pipeline | 4 weeks | Knowledge base |
| 7 | Live Trading Integration | 3 weeks | Production ready |
| 8 | Continuous Learning, Optimization | Ongoing | Self-improving |

**Total MVP (Phases 1-5)**: ~14 weeks

---

## 9. Key Design Decisions & Trade-offs

| Decision | Rationale | Trade-off |
|----------|-----------|-----------|
| Modular monolith | Low latency, simple deployment, shared memory | Less fault isolation |
| Async event bus | Backpressure handling, decoupling | Complexity in debugging |
| DuckDB + Qdrant | OLAP + Vector in-process, no servers | Single-node only |
| TensorRT on RTX 5080 | 2-5x speedup vs ONNX, FP16 native | Build complexity, version lock |
| No LLM in hot path | Deterministic, fast, explainable | Less "creative" reasoning |
| HTMX dashboard | No SPA complexity, server-rendered | Less interactive |
| Phase-gated development | Prevents scope creep, validates early | Slower initial progress |
| After-hours heavy compute | Market hours guaranteed resources | Delayed model updates |

---

## 10. Risks & Mitigations (Technical)

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Vision model accuracy insufficient | Medium | High | Ensemble, human-in-loop, continuous eval |
| VRAM fragmentation | Low | Critical | Pool allocators, model quantization |
| DuckDB write contention | Low | Medium | Batch writes, WAL mode |
| Event bus backpressure | Medium | High | Bounded queues, drop policies, metrics |
| Video pipeline failures | High | Medium | Checkpointing, retry, dead letter queue |
| Data source API changes | Medium | Medium | Adapter pattern, multiple sources |

---

**Document Version**: 1.0  
**Status**: DRAFT - Requires Human Approval  
**Next Step**: Agent Organization Design