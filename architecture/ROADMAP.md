# TradingOS Development Roadmap

## Overview

This document defines the phased implementation roadmap for TradingOS. Each phase must compile and pass tests before proceeding to the next. The roadmap is designed for a single engineer (supported by AI agents) working on a modular monolith.

**Total Estimated Duration**: 26 weeks (6.5 months) to MVP
**Team**: 1 Human (Architect/Lead) + AI Agent Organization

---

## Phase 1: Foundation (Weeks 1-2)

**Goal**: Running skeleton with core infrastructure

### Deliverables

| Component | Specification | Acceptance Criteria |
|-----------|---------------|---------------------|
| **Project Structure** | `code/`, `tests/`, `config/`, `scripts/` | `python -m tradingos --help` works |
| **Config System** | YAML + Pydantic Settings, hot reload | Config changes detected < 1s (dev mode) |
| **Logging** | structlog + orjson, JSONL file + console | Structured logs with trace_id correlation |
| **Event Bus** | asyncio.Queue pub/sub, typed events | 10k events/sec throughput, < 1ms latency |
| **Model Manager** | Load/unload, VRAM budget, health checks | Loads 5 market models < 30s, stays < 14GB |
| **CLI Entry Point** | `tradingos start`, `tradingos eval`, `tradingos video` | All subcommands functional |
| **Health Endpoint** | HTTP `:8080/health` + `/metrics` | Prometheus scrape successful |
| **CI Pipeline** | GitHub Actions: lint, type-check, test | Green on main branch |

### Key Files to Create

```
code/
├── tradingos/
│   ├── __init__.py
│   ├── __main__.py           # CLI entry
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py         # Pydantic Settings
│   │   ├── logging.py        # structlog setup
│   │   ├── events.py         # Event bus + base events
│   │   ├── models/           # ModelManager + BaseModel
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── manager.py
│   │   │   └── registry.yaml
│   │   └── health.py         # /health endpoint
│   └── modules/              # Empty module packages
│       ├── scanner/
│       ├── market/
│       ├── charts/
│       ├── indicators/
│       ├── vision/
│       ├── memory/
│       ├── reasoning/
│       ├── risk/
│       ├── execution/
│       ├── journal/
│       ├── video/
│       └── dashboard/
config/
├── base.yaml
├── development.yaml
└── production.yaml
tests/
├── unit/
│   ├── test_config.py
│   ├── test_events.py
│   └── test_model_manager.py
└── conftest.py
```

### Dependencies (requirements.txt core)
```txt
pydantic>=2.7
pydantic-settings>=2.3
pyyaml>=6.0
structlog>=24.1
orjson>=3.9
prometheus-client>=0.19
fastapi>=0.110
uvicorn>=0.29
python-dotenv>=1.0
```

---

## Phase 2: Data Pipeline (Weeks 3-5)

**Goal**: End-to-end market data ingestion, chart generation, indicators

### Deliverables

| Module | Specification | Acceptance Criteria |
|--------|---------------|---------------------|
| **Scanner** | File watch, webhook, IPC inputs | 1000 candidates/sec, < 10ms each |
| **Market Data** | DuckDB schema, Polygon WS, cache | 1m bars < 50ms, gap detection |
| **Chart Engine** | Numba rendering → CUDA tensor | 4 timeframes → 256x256x3 < 30ms |
| **Indicators** | VWAP, EMA(9,20,50,200), ATR, RVol | All indicators < 5ms, vectorized |
| **Integration** | Scanner → Market → Chart → Indicators | Full pipeline < 100ms per candidate |

### Key Files

```
code/tradingos/modules/
├── scanner/
│   ├── __init__.py
│   ├── interfaces.py       # StockCandidate, ScannerSource
│   ├── sources.py          # FileWatch, Webhook, IPC
│   ├── scanner.py          # Main coordinator
│   └── priority.py         # Scoring algorithm
├── market/
│   ├── __init__.py
│   ├── interfaces.py       # MarketData, DataSource
│   ├── duckdb_store.py     # Schema + CRUD
│   ├── polygon_ws.py       # WebSocket client
│   ├── cache.py            # In-memory hot cache
│   └── gap_detector.py
├── charts/
│   ├── __init__.py
│   ├── interfaces.py       # ChartTensor
│   ├── renderer.py         # Numba + CUDA kernels
│   ├── normalizer.py       # Price/volume normalization
│   └── stacker.py          # Multi-timeframe composition
└── indicators/
    ├── __init__.py
    ├── interfaces.py       # IndicatorSnapshot
    ├── vwap.py
    ├── ema.py
    ├── atr.py
    ├── rvol.py
    └── calculator.py       # Orchestrates all
```

### Database Migration
```sql
-- Run via migration script
CREATE TABLE ohlcv_1m (...);
CREATE TABLE ohlcv_5m (...);
-- ... all market data tables
```

### Tests
- Unit: Each indicator function, renderer, priority scoring
- Integration: Scanner → Market Data → Chart → Indicators flow
- Benchmark: 1000 candidates latency distribution

---

## Phase 3: AI Inference Core (Weeks 6-9)

**Goal**: Vision models running, memory engine operational

### Deliverables

| Module | Specification | Acceptance Criteria |
|--------|---------------|---------------------|
| **Vision Engine** | 3 TensorRT models (pattern, detect, keypoint) | All 3 loaded < 5GB, combined < 120ms |
| **Memory Engine** | Qdrant embedded + DuckDB trades | Top-10 retrieval < 50ms |
| **Embedding** | BGE-large-en-v1.5 ONNX | Text embed < 20ms |
| **Model Manager** | Market hours auto-load, warmup | 5 models loaded by 09:00 ET |

### Key Files

```
code/tradingos/modules/
├── vision/
│   ├── __init__.py
│   ├── interfaces.py       # VisionOutput, DetectedObject, Keypoint
│   ├── pattern_classifier.py
│   ├── object_detector.py
│   ├── keypoint_detector.py
│   ├── engine.py           # Orchestrates all 3
│   └── tensorrt_wrapper.py # Common TRT utilities
├── memory/
│   ├── __init__.py
│   ├── interfaces.py       # HistoricalTrade, SearchQuery
│   ├── qdrant_store.py     # Embedded Qdrant client
│   ├── duckdb_store.py     # Structured trade queries
│   ├── embedder.py         # BGE text + vision features
│   ├── search.py           # Hybrid vector + structured
│   └── reranker.py         # Cross-encoder or heuristic
```

### Model Artifacts Required
```
models/tensorrt/
├── vision_pattern_fp16.engine
├── yolov8n_fp16.engine
└── hrnet_w18_fp16.engine
models/onnx/
└── bge-large-en-v1.5-fp16.onnx
```

### Tests
- Vision: Accuracy on held-out test set (F1 > 0.80 per class)
- Memory: Retrieval precision@5 > 0.70 on labeled pairs
- Latency: All targets met on RTX 5080

---

## Phase 4: Decision Loop (Weeks 10-12)

**Goal**: Reasoning → Risk → Execution → Journal working end-to-end

### Deliverables

| Module | Specification | Acceptance Criteria |
|--------|---------------|---------------------|
| **Reasoning** | Evidence aggregation, TradeThesis | Thesis generated < 100ms, explainable |
| **Risk** | Hard + dynamic rules, config-driven | Rejects invalid trades with specific reason |
| **Execution** | Paper engine with slippage model | Fills simulated, realistic latency |
| **Journal** | Immutable JSONL + DuckDB index | Every decision queryable, traceable |

### Key Files

```
code/tradingos/modules/
├── reasoning/
│   ├── __init__.py
│   ├── interfaces.py       # Evidence, TradeThesis
│   ├── aggregator.py       # Evidence combination
│   ├── confidence.py       # Weighted scoring
│   └── explainer.py        # LLM-assisted text (async)
├── risk/
│   ├── __init__.py
│   ├── interfaces.py       # RiskDecision, RiskRule
│   ├── hard_rules.py       # Config-driven validators
│   ├── dynamic_rules.py    # Volatility, correlation, time
│   └── engine.py           # Rule evaluation
├── execution/
│   ├── __init__.py
│   ├── interfaces.py       # Order, Fill, BrokerAdapter
│   ├── paper_engine.py     # Simulated order book
│   ├── slippage_model.py   # Spread + volatility + size
│   └── order_manager.py    # Bracket orders, lifecycle
└── journal/
    ├── __init__.py
    ├── interfaces.py       # DecisionRecord, OutcomeRecord
    ├── writer.py           # Async JSONL + DuckDB
    ├── reader.py           # Query interface
    └── exporter.py         # CSV, Parquet for analysis
```

### Integration Test
```
Scanner → Market → Chart → Indicators → Vision → Memory → Reasoning → Risk → Execution → Journal
                                                                    ↓
                                                              Dashboard (WS)
```
**Target**: Full pipeline < 500ms per candidate

---

## Phase 5: Observability & Evaluation (Weeks 13-14)

**Goal**: Dashboard, evaluation framework, monitoring

### Deliverables

| Component | Specification | Acceptance Criteria |
|-----------|---------------|---------------------|
| **Dashboard** | FastAPI + HTMX, WebSocket | Real-time scanner, charts, positions |
| **Evaluation** | Nightly automated run | Pattern metrics, calibration, trading metrics |
| **Monitoring** | Prometheus + Grafana | Latency, GPU, P&L dashboards |
| **Alerting** | Latency > 1s, loss > 1%, OOM | Telegram/email alerts |

### Key Files

```
code/tradingos/modules/dashboard/
├── __init__.py
├── app.py              # FastAPI app
├── routes/
│   ├── scanner.py
│   ├── charts.py
│   ├── positions.py
│   ├── performance.py
│   └── search.py
├── templates/          # HTMX partials
├── static/
└── websocket.py        # Real-time updates

evaluations/
├── run_nightly.py
├── pattern_eval.py
├── calibration_eval.py
├── trading_metrics.py
├── system_metrics.py
└── report_generator.py
```

### Dashboard Pages
1. **Scanner** - Live feed with AI analysis badges
2. **Charts** - Multi-timeframe with vision overlays
3. **Positions** - Paper trades with P&L
4. **Search** - Historical trade similarity
5. **Performance** - Daily/weekly/monthly metrics
6. **System** - GPU, latency, model health

---

## Phase 6: Video Learning Pipeline (Weeks 15-18)

**Goal**: Fully automated Ross video processing

### Deliverables

| Stage | Specification | Acceptance Criteria |
|-------|---------------|---------------------|
| **File Watcher** | Inbox → processing queue | Zero manual steps |
| **Audio/STT** | faster-whisper + diarization | > 95% word accuracy |
| **Frames/OCR** | 1fps + chart detection + PaddleOCR | Ticker/price extraction > 90% |
| **Trade Extraction** | LLM + OCR context | Structured trades F1 > 0.85 |
| **Pattern Labeling** | Vision engine on extracted charts | Pattern accuracy > 0.80 |
| **Embedding/KB** | Qdrant + DuckDB insert | End-to-end < 10 min/hour |

### Key Files

```
code/tradingos/modules/video/
├── __init__.py
├── orchestrator.py       # Pipeline coordinator
├── file_watcher.py
├── audio_extractor.py
├── stt_processor.py
├── frame_extractor.py
├── chart_classifier.py
├── chart_detector.py
├── ocr_processor.py
├── timestamp_aligner.py
├── trade_extractor.py
├── pattern_labeler.py
├── outcome_determiner.py
├── embedding_generator.py
└── kb_writer.py
```

### Models Required (After-Hours)
```
models/ct2/whisper-large-v3-ct2-fp16/
models/onnx/mobilenetv3_chart_classify.onnx
models/tensorrt/yolov8n_chart_detect_fp16.engine
models/onnx/paddleocr_v4_fp16.onnx
models/gguf/llama-3.2-3b-instruct-q4_k_m.gguf
```

---

## Phase 7: Live Trading Integration (Weeks 19-21)

**Goal**: Broker connectivity, live execution (OPTIONAL - paper trading MVP first)

### Deliverables

| Component | Specification | Acceptance Criteria |
|-----------|---------------|---------------------|
| **Broker Adapters** | Alpaca, IBKR interfaces | Paper → Live switch via config |
| **Order Routing** | Smart routing, retry logic | 99.9% order acceptance |
| **Position Sync** | Reconcile with broker | Zero drift after 1 hour |
| **Risk Guards** | Pre-trade + real-time | Hard stops enforced at broker |

### Key Files

```
code/tradingos/modules/execution/
├── brokers/
│   ├── __init__.py
│   ├── base.py           # BrokerAdapter ABC
│   ├── alpaca.py
│   └── ibkr.py
├── live_engine.py        # Wraps paper + live
├── position_sync.py
└── risk_guards.py        # Broker-side validation
```

**Note**: Phase 7 is gated behind 30 days of successful paper trading with positive expectancy.

---

## Phase 8: Continuous Learning (Weeks 22-26)

**Goal**: Automated retraining, model improvement, scaling

### Deliverables

| Component | Specification | Acceptance Criteria |
|-----------|---------------|---------------------|
| **Retraining Pipeline** | Weekly vision model update | New model beats production (p<0.05) |
| **Data Curation** | Auto-dedupe, balance, split | Clean dataset ready for training |
| **Experiment Tracking** | Local MLflow-compatible | All experiments reproducible |
| **A/B Testing** | Canary deployment | Safe rollout/rollback |
| **Performance Optimization** | Profile-guided optimization | 20% latency reduction |

---

## Milestone Summary

| Milestone | Target Week | Criteria |
|-----------|-------------|----------|
| **M1: Skeleton Running** | Week 2 | `tradingos start` stays up, health endpoint green |
| **M2: Data Pipeline** | Week 5 | 1000 candidates processed < 100ms each |
| **M3: AI Inference** | Week 9 | Vision F1 > 0.80, Memory P@5 > 0.70 |
| **M4: Decision Loop** | Week 12 | Full pipeline < 500ms, paper trades executing |
| **M5: Dashboard + Eval** | Week 14 | Real-time UI, nightly eval reports |
| **M6: Video Pipeline** | Week 18 | 10 videos processed, trades in KB |
| **M7: Paper Trading Validated** | Week 21 | 30 days positive expectancy |
| **M8: Live Ready** | Week 26 | All systems green, rollback tested |

---

## Resource Allocation (Single Engineer + AI Agents)

| Phase | Human Focus | AI Agents Deployed |
|-------|-------------|-------------------|
| 1 | Architecture, config, CI | Backend Engineer, DevOps |
| 2 | Data pipeline design, integration | Data Engineer, Backend Engineer |
| 3 | Model integration, optimization | Vision Engineer, Performance Engineer |
| 4 | Decision logic, risk rules | Backend Engineer, Quant Researcher |
| 5 | Dashboard UX, eval design | Frontend Engineer, QA Engineer |
| 6 | Pipeline orchestration, quality | Video Engineer, Data Engineer |
| 7 | Broker integration, safety | Backend Engineer, Security Engineer |
| 8 | Training automation, optimization | ML Engineer, Performance Engineer |

---

## Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Vision model accuracy too low | Medium | High | Synthetic data augmentation, ensemble |
| VRAM OOM during market hours | Low | Critical | Strict budget, quantization, swap policy |
| Market data gaps | Medium | Medium | Multi-source, interpolation flags |
| Video pipeline failure rate | High | Medium | Checkpointing, human review queue |
| Scope creep | High | High | Phase gates, explicit rejection log |
| Single point of failure (human) | Medium | High | Document everything, agent handoffs |

---

## Success Metrics (Go/No-Go per Phase)

| Phase | Metric | Threshold |
|-------|--------|-----------|
| 1 | CI green, startup < 10s | PASS |
| 2 | Pipeline latency p99 < 100ms | PASS |
| 3 | Vision macro F1 > 0.80 | PASS |
| 4 | End-to-end p99 < 500ms | PASS |
| 5 | Dashboard loads < 2s, eval runs nightly | PASS |
| 6 | Video trade extraction F1 > 0.85 | PASS |
| 7 | 30 days paper: expectancy > $0.50/$1 risk | PASS |
| 8 | Automated retraining improves model | PASS |

---

**Document Version**: 1.0  
**Status**: DRAFT - Requires Human Approval  
**Next Step**: Risk Assessment Document