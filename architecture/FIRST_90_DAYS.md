# TradingOS First 90-Day Implementation Plan

## Overview

This document provides a detailed, week-by-week execution plan for the first 90 days (Phases 1-5) of TradingOS development. This covers the MVP: a working paper trading platform with AI analysis, dashboard, and evaluation framework.

**Goal**: End-to-end paper trading system processing scanner candidates in < 500ms with explainable AI decisions.

---

## Week 1-2: Phase 1 - Foundation

### Week 1: Project Setup & Core Infrastructure

#### Day 1-2: Repository & Environment
- [ ] Initialize `code/tradingos/` package structure
- [ ] Configure `pyproject.toml` with dependencies, build system
- [ ] Set up `config/base.yaml`, `development.yaml`, `production.yaml`
- [ ] Configure Pydantic Settings with validation
- [ ] Set up structlog + orjson logging with trace_id correlation
- [ ] Create `Makefile` / `scripts/` for common commands

#### Day 3-4: Event Bus & Config
- [ ] Implement `core/events.py` - asyncio pub/sub with typed events
- [ ] Define base events: `StockDetected`, `MarketDataReady`, `ChartReady`, etc.
- [ ] Implement config hot-reload (file watcher, debounced)
- [ ] Unit tests: event publishing, subscription, config reload

#### Day 5: Model Manager Skeleton
- [ ] Implement `BaseModel` abstract interface
- [ ] Implement `ModelManager` with VRAM budget tracking
- [ ] Model registry YAML loading
- [ ] Health check endpoint (`/health`, `/metrics`)
- [ ] Integration test: load dummy model, verify VRAM accounting

#### Deliverables Week 1
- `python -m tradingos --help` works
- `python -m tradingos start` stays running, health endpoint responds
- All unit tests pass (`pytest tests/unit -v`)
- CI pipeline green on GitHub Actions

### Week 2: CLI, CI/CD & Documentation

#### Day 1-2: CLI Commands
- [ ] `tradingos start` - main process
- [ ] `tradingos eval` - run evaluation
- [ ] `tradingos video` - process video
- [ ] `tradingos migrate` - database migrations
- [ ] `tradingos shell` - IPython with app context

#### Day 3-4: CI/CD Pipeline
- [ ] GitHub Actions: lint (ruff), type-check (mypy), test (pytest)
- [ ] Pre-commit hooks: ruff, mypy, black
- [ ] Dependency scanning (pip-audit)
- [ ] Build verification

#### Day 5: Documentation & Handoff
- [ ] `docs/architecture/phase1_foundation.md`
- [ ] `docs/runbooks/startup_shutdown.md`
- [ ] `memory/agent_handoffs/backend_engineer_context.md`
- [ ] Update project memory with decisions

#### Phase 1 Gate Review
- [ ] Hermes review: Architecture compliance, test coverage > 80%
- [ ] Performance: Startup < 10s, health check < 100ms
- [ ] **GO/NO-GO Decision**

---

## Week 3-5: Phase 2 - Data Pipeline

### Week 3: Market Data & Scanner

#### Day 1-2: DuckDB Schema & Migrations
- [ ] Create all market data tables (ohlcv_1m, 5m, 15m, daily)
- [ ] Create fundamentals table
- [ ] Migration system with version tracking
- [ ] Connection pooling, WAL mode

#### Day 3-4: Polygon WebSocket Client
- [ ] Async WebSocket with auto-reconnect
- [ ] Subscription management (ticker lists)
- [ ] Message parsing → DuckDB bulk insert
- [ ] Gap detection & interpolation logic
- [ ] Backfill historical data script

#### Day 5: Scanner Module
- [ ] File watcher source (JSON Lines)
- [ ] Webhook source (FastAPI endpoint)
- [ ] IPC source (named pipe)
- [ ] Deduplication (ticker + 5min window)
- [ ] Priority scoring algorithm
- [ ] `StockDetected` event emission

### Week 4: Chart Engine & Indicators

#### Day 1-2: Chart Renderer (Numba + CUDA)
- [ ] OHLCV normalization (price → 0-1, volume → 0-1)
- [ ] Candlestick rendering kernel
- [ ] Overlay kernels: VWAP, EMA(9,20,50), volume bars
- [ ] Multi-timeframe stacker (1m, 5m, 15m, daily → 4×256×256×3)
- [ ] CUDA tensor output (pinned memory → VRAM)

#### Day 3-4: Indicator Engine
- [ ] Vectorized VWAP (incremental + batch)
- [ ] Vectorized EMA (9, 20, 50, 200)
- [ ] Vectorized ATR(14), RSI(14)
- [ ] Relative Volume (vs 20-day avg)
- [ ] Gap%, Float turnover
- [ ] `IndicatorSnapshot` dataclass output

#### Day 5: Integration & Benchmarks
- [ ] Scanner → Market Data → Chart → Indicators flow
- [ ] Latency benchmarks (target: < 100ms total)
- [ ] Unit tests for each indicator
- [ ] Integration test with synthetic data

### Week 5: Data Quality & Hardening

#### Day 1-2: Data Validation
- [ ] OHLCV sanity checks (high ≥ low, volume ≥ 0)
- [ ] Timestamp continuity verification
- [ ] Interpolation flags on all gap-filled bars
- [ ] Data quality metrics in Prometheus

#### Day 3-4: Multi-Source Resilience
- [ ] Alpaca WebSocket backup client
- [ ] Source priority failover
- [ ] Cache TTL management (1s for 1m bars)
- [ ] Stale data detection

#### Day 5: Phase 2 Gate Review
- [ ] 1000 candidates processed end-to-end
- [ ] Latency p99 < 100ms
- [ ] Zero data loss in 24h soak test
- [ ] **GO/NO-GO Decision**

---

## Week 6-9: Phase 3 - AI Inference Core

### Week 6: Vision Engine - Model Preparation

#### Day 1-2: Model Conversion Pipeline
- [ ] PyTorch → ONNX export scripts for all 3 vision models
- [ ] ONNX → TensorRT FP16 conversion (trtexec)
- [ ] Timing cache for fast rebuilds
- [ ] Verify output parity (PyTorch vs TRT)

#### Day 3-4: TensorRT Wrappers
- [ ] Common `TRTEngine` base class
- [ ] Buffer allocation (pinned host + device)
- [ ] CUDA Graph capture for fixed shapes
- [ ] Async inference with streams

#### Day 5: Vision Model Integration
- [ ] `VisionPatternModel` - EfficientNet-B0 classifier
- [ ] `VisionDetectModel` - YOLOv8n detector
- [ ] `VisionKeypointModel` - HRNet-W18 keypoints
- [ ] ModelManager registration with priority=100

### Week 7: Vision Engine - Orchestration

#### Day 1-2: Vision Engine Module
- [ ] `VisionEngine` class coordinating all 3 models
- [ ] Input: `ChartTensor` → Output: `VisionOutput`
- [ ] Post-processing: NMS, confidence thresholding
- [ ] Pattern probability calibration (temperature scaling)

#### Day 3-4: Accuracy Validation
- [ ] Create test set (2000 labeled charts)
- [ ] Run evaluation: per-class precision/recall/F1
- [ ] Confusion matrix analysis
- [ ] Target: Macro F1 > 0.80

#### Day 5: Latency Optimization
- [ ] Profile each model (NCU/NSight)
- [ ] Optimize batch=1 latency
- [ ] Target: Combined < 120ms
- [ ] VRAM verification: < 5GB total

### Week 8: Memory Engine

#### Day 1-2: Qdrant Embedded Setup
- [ ] Embedded Qdrant in-process
- [ ] Collection creation with HNSW config
- [ ] Payload schema with all filterable fields
- [ ] Scalar quantization (INT8) for memory

#### Day 3-4: DuckDB Trade Store
- [ ] Trades table CRUD operations
- [ ] Hybrid search: vector → filter → fetch → rerank
- [ ] Time-range queries for regime analysis
- [ ] Batch insert for video pipeline

#### Day 5: Embedding Generation
- [ ] `EmbedTextModel` - BGE-large-en-v1.5 ONNX
- [ ] Vision feature extraction (pooled backbone)
- [ ] Combined embedding: 0.6×text + 0.4×vision
- [ ] L2 normalization

### Week 9: Memory Integration & Phase 3 Gate

#### Day 1-2: Memory Search Pipeline
- [ ] `search_similar(candidate, vision, indicators, k=10)`
- [ ] Structured filters: pattern, ticker, date range, outcome
- [ ] Re-ranking with heuristic (recency, similarity, outcome)
- [ ] Latency target: < 50ms

#### Day 3-4: End-to-End AI Flow
- [ ] Chart → Vision → Memory → Results
- [ ] Synthetic candidate test
- [ ] Verify similar trades retrieved make sense

#### Day 5: Phase 3 Gate Review
- [ ] Vision Macro F1 > 0.80 on held-out test
- [ ] Memory Precision@5 > 0.70 on labeled pairs
- [ ] Combined Vision+Memory latency p99 < 200ms
- [ ] VRAM stable at ~7.5GB for 24h
- [ ] **GO/NO-GO Decision**

---

## Week 10-12: Phase 4 - Decision Loop

### Week 10: Reasoning Engine

#### Day 1-2: Evidence Aggregation
- [ ] `Evidence` dataclass (source, claim, value, confidence, weight)
- [ ] Vision evidence: pattern probs, keypoints
- [ ] Indicator evidence: VWAP dist, EMA alignment, RVol
- [ ] Memory evidence: similar trades stats, win rate
- [ ] Market context: trend, volatility, time of day

#### Day 3-4: Confidence Scoring
- [ ] Weighted aggregation formula
- [ ] Dynamic weights based on data quality
- [ ] Calibration: map raw score → calibrated probability
- [ ] `TradeThesis` output with all fields

#### Day 5: LLM Explainer (Async)
- [ ] `ReasoningLLM` - Llama-3.2-3B GGUF
- [ ] Prompt template for thesis → explanation
- [ ] Async generation (non-blocking)
- [ ] Fallback template if LLM unavailable

### Week 11: Risk Engine & Execution

#### Day 1-2: Risk Engine
- [ ] Hard rules from config (YAML-driven)
- [ ] Dynamic rules: vol-adjusted sizing, correlation, time-of-day
- [ ] `RiskDecision` with specific rejection reasons
- [ ] Circuit breakers: daily loss, drawdown, position limits

#### Day 3-4: Paper Execution Engine
- [ ] Simulated order book with level-1 data
- [ ] Slippage model: spread × 0.5 + volatility × size_factor
- [ ] Latency simulation: base + random(0, 50ms)
- [ ] Partial fill logic for large orders
- [ ] Bracket order management (entry + stop + targets)

#### Day 5: Integration - Reasoning → Risk → Execution
- [ ] Full decision flow test
- [ ] Verify rejections logged with reasons
- [ ] Verify paper fills generate journal entries

### Week 12: Journal & Phase 4 Gate

#### Day 1-2: Journal Module
- [ ] Async JSONL writer (batched, buffered)
- [ ] DuckDB index for querying
- [ ] Immutable append-only design
- [ ] Query API: by ticker, date, outcome, trace_id

#### Day 3-4: End-to-End Pipeline Test
- [ ] Scanner → Market → Chart → Indicators → Vision → Memory → Reasoning → Risk → Execution → Journal
- [ ] 100 synthetic candidates
- [ ] Latency profiling per stage
- [ ] Target: p99 < 500ms

#### Day 5: Phase 4 Gate Review
- [ ] Full pipeline p99 < 500ms
- [ ] Risk engine rejects invalid trades correctly
- [ ] Paper fills realistic (slippage, partial)
- [ ] Journal queryable with trace_id correlation
- [ ] **GO/NO-GO Decision**

---

## Week 13-14: Phase 5 - Dashboard & Evaluation

### Week 13: Dashboard (FastAPI + HTMX)

#### Day 1-2: Core Dashboard
- [ ] FastAPI app with lifespan (startup/shutdown)
- [ ] WebSocket manager for real-time updates
- [ ] HTMX base template + partial rendering
- [ ] Static assets (CSS, minimal JS)

#### Day 3-4: Dashboard Pages
- [ ] **Scanner**: Live feed with AI badges (pattern, confidence, risk)
- [ ] **Charts**: Multi-timeframe Canvas rendering + vision overlays
- [ ] **Positions**: Paper trades with real-time P&L
- [ ] **Search**: Historical trade similarity (ticker, pattern, date)

#### Day 5: Performance & Polish
- [ ] WebSocket message batching (100ms)
- [ ] Chart rendering optimization (offscreen canvas)
- [ ] Mobile-responsive layout
- [ ] Error boundaries + loading states

### Week 14: Evaluation Framework

#### Day 1-2: Pattern Detection Evaluation
- [ ] Ground truth dataset (500 labeled charts)
- [ ] Precision/Recall/F1 per class
- [ ] Confusion matrix visualization
- [ ] Calibration: ECE, reliability diagrams

#### Day 3-4: Trading Metrics Evaluation
- [ ] Paper trade analysis: expectancy, PF, DD, Sharpe
- [ ] Calibration: predicted prob vs actual win rate
- [ ] Latency percentiles per stage (p50/p95/p99)
- [ ] GPU utilization tracking

#### Day 5: Nightly Automation & Gate Review
- [ ] `evaluations/run_nightly.py` - scheduled via cron
- [ ] HTML report generation
- [ ] Alert on metric degradation
- [ ] Phase 5 Gate: Dashboard loads < 2s, eval runs automatically
- [ ] **MVP COMPLETE - GO/NO-GO FOR PAPER TRADING VALIDATION**

---

## 90-Day Summary

| Phase | Weeks | Key Deliverable | Gate Criteria |
|-------|-------|-----------------|---------------|
| 1: Foundation | 1-2 | Running skeleton, CI/CD | Startup < 10s, tests pass |
| 2: Data Pipeline | 3-5 | Market data → charts → indicators | 1000 candidates < 100ms |
| 3: AI Inference | 6-9 | Vision + Memory engines | Vision F1 > 0.80, Mem P@5 > 0.70 |
| 4: Decision Loop | 10-12 | Reasoning → Risk → Execution → Journal | E2E < 500ms |
| 5: Dashboard + Eval | 13-14 | Real-time UI, nightly eval | Dashboard < 2s, eval automated |

---

## Resource Allocation (Per Week)

| Week | Human Focus | AI Agents Active |
|------|-------------|------------------|
| 1-2 | Architecture, core infra, CI | Backend, DevOps |
| 3-5 | Data pipeline, integration | Data Engineer, Backend |
| 6-9 | Model integration, optimization | Vision, Performance |
| 10-12 | Decision logic, risk, execution | Backend, Quant Researcher |
| 13-14 | Dashboard UX, eval design | Frontend, QA |

---

## Risk Mitigation During 90 Days

| Risk | Early Warning | Contingency |
|------|---------------|-------------|
| Vision accuracy low | Week 7 eval F1 < 0.70 | Add synthetic data, ensemble, extend Phase 3 |
| Latency > target | Week 5/9/12 benchmarks | Profile, optimize, drop non-critical features |
| VRAM pressure | nvidia-smi > 13GB | Quantize, reduce batch, CPU fallback |
| Scope creep | New features requested | Phase gate enforcement, rejection log |
| Single engineer bottleneck | Velocity < planned | Reduce scope, extend timeline |

---

## Success Definition (End of 90 Days)

**MVP Complete When**:
1. ✅ Scanner accepts candidates → produces decisions in < 500ms p99
2. ✅ Vision model classifies 8 patterns with Macro F1 > 0.80
3. ✅ Memory engine retrieves relevant historical trades (P@5 > 0.70)
4. ✅ Reasoning engine produces explainable `TradeThesis`
5. ✅ Risk engine enforces hard limits with specific rejections
6. ✅ Paper execution simulates realistic fills
7. ✅ Journal captures every decision immutably
8. ✅ Dashboard shows live scanner, charts, positions, search
9. ✅ Nightly evaluation runs automatically with HTML reports
10. ✅ System stable for 5 consecutive market days

**Next Phase**: 30-day paper trading validation (Phase 7 gate)

---

**Document Version**: 1.0  
**Status**: DRAFT - Requires Human Approval  
**Next Step**: Push all architecture documents to GitHub