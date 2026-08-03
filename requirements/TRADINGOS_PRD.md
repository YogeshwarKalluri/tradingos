# TradingOS Product Requirements Document

## Executive Summary

TradingOS is a local AI-powered momentum day trading platform designed to run exclusively on a high-performance workstation (AMD Ryzen 9 9950X, RTX 5080 16GB, 64GB RAM, 2TB NVMe). The platform combines computer vision, historical pattern retrieval, reasoning engines, and continuous learning to assist in identifying, analyzing, and executing high-probability momentum trades.

**This is NOT a trading bot.** This is an AI Trading Intelligence Platform that provides explainable, evidence-based trading decisions.

---

## 1. Problem Statement

Retail momentum traders face several critical challenges:
- Information overload from scanners generating too many candidates
- Inability to quickly analyze chart patterns across multiple timeframes
- Lack of systematic historical comparison for similar setups
- Emotional decision-making under time pressure
- No structured learning from past trades (both personal and educational)
- No quantitative evaluation of pattern recognition accuracy

---

## 2. User Workflow

### Market Hours (9:30 AM - 4:00 PM EST)
1. **Scanner Input** → External scanner feeds candidates via file/API
2. **Market Data Enrichment** → Platform fetches real-time OHLCV, Level 2, news
3. **Chart Generation** → Multi-timeframe charts rendered (1m, 5m, 15m, daily)
4. **Vision Analysis** → AI analyzes charts for patterns (flags, breakouts, VWAP reclaims)
5. **Memory Retrieval** → Similar historical trades fetched from knowledge base
6. **Reasoning Synthesis** → Evidence combined into structured trade thesis
7. **Risk Evaluation** → Position size, stop, target, daily loss limits validated
8. **Decision Output** → Execute / Paper Trade / Reject with full explanation
9. **Journaling** → Every decision (executed or not) logged with reasoning

### After Market Hours (4:00 PM - 9:30 AM EST)
1. **Trade Import** → Today's trades imported from broker/journal
2. **Video Processing** → New Ross Cameron videos auto-processed
3. **Knowledge Extraction** → Trades, patterns, reasoning extracted
4. **Embedding Generation** → Vector embeddings for similarity search
5. **Performance Evaluation** → Precision/recall, calibration, P&L metrics
6. **Model Updates** → Fine-tuning / retraining if warranted
7. **Report Generation** → Daily/weekly/monthly performance reports

---

## 3. Functional Requirements

### 3.1 Scanner Module (FR-001)
- Accept candidates from multiple sources (file watch, REST webhook, IPC)
- Normalize to internal `StockCandidate` schema
- Deduplicate and prioritize by relative volume, gap %, float
- **Latency target**: < 10ms per candidate

### 3.2 Market Data Module (FR-002)
- Local DuckDB cache of OHLCV (1m, 5m, 15m, 1h, daily)
- Real-time WebSocket subscriptions (polygon.io, Alpaca, or IQFeed)
- Level 2 order book snapshot on demand
- News/sentiment integration (Benzinga, Twitter API)
- **Latency target**: < 50ms for cached data, < 200ms for live fetch

### 3.3 Chart Engine (FR-003)
- Generate charts from OHLCV arrays (no external charting library)
- Support: candlestick, volume, VWAP, EMAs (9, 20, 50, 200), ATR bands
- Render to tensor (HWC) for vision model input - **no disk I/O**
- Multi-timeframe composite (4 charts → single 1024x1024 tensor)
- **Latency target**: < 30ms per candidate

### 3.4 Indicator Engine (FR-004)
- Vectorized NumPy/Numba implementations (no TA-Lib dependency)
- Required indicators: VWAP, EMA(9/20/50/200), ATR(14), RVol, Gap%, Float
- Incremental update support for streaming data
- **Latency target**: < 5ms per candidate

### 3.5 Vision Engine (FR-005)
- Local vision model (RTX 5080 optimized): chart pattern classification
- Supported patterns: Bull Flag, Bear Flag, Flat Top Breakout, VWAP Reclaim, High Tight Flag, ABCD, Double Bottom, Cup & Handle
- Output: pattern probabilities + bounding boxes + keypoints
- **Latency target**: < 200ms per candidate (batch=1, model loaded)

### 3.6 Memory Engine (FR-006)
- Qdrant vector database for trade embeddings (local, embedded mode)
- Structured trade metadata in DuckDB (SQL analytics)
- Hybrid search: vector similarity + structured filters (ticker, date, pattern, outcome)
- **Latency target**: < 50ms for top-k retrieval

### 3.7 Reasoning Engine (FR-007)
- Evidence aggregation: vision output + indicators + memory results + market context
- Structured output: `TradeThesis` with confidence, evidence list, risk factors
- Explainable: every claim traced to source (indicator value, similar trade, pattern)
- **Latency target**: < 100ms per candidate

### 3.8 Risk Engine (FR-008)
- Hard rules (non-negotiable): max position size, max daily loss, max drawdown
- Dynamic rules: volatility-adjusted sizing, correlation limits, time-of-day filters
- Pre-trade validation: rejects with specific rule violation
- **Latency target**: < 10ms per candidate

### 3.9 Execution Engine (FR-009)
- Paper trading mode: simulated fills with realistic slippage/model
- Live trading mode: broker API integration (Alpaca, IBKR) - **Phase 7+**
- Order management: bracket orders, trailing stops, partial exits
- **Latency target**: < 100ms order submission

### 3.10 Journal Module (FR-010)
- Immutable append-only log of every decision
- Schema: candidate, thesis, decision, fill, outcome, post-trade analysis
- Queryable via SQL and vector search
- Export for tax/analysis

### 3.11 Video Learning Pipeline (FR-011)
- Input: video files dropped in `knowledge/ross_videos/inbox/`
- Automated: audio extraction → STT → timestamp alignment → frame extraction → OCR → chart detection → trade event extraction → embedding → knowledge base
- Zero manual intervention after initial setup
- **Throughput target**: 1 hour video → processed in < 10 minutes

### 3.12 Evaluation Framework (FR-012)
- **Pattern Detection**: Precision, Recall, F1 per pattern class
- **Calibration**: Reliability diagrams, ECE (Expected Calibration Error)
- **Trading Metrics**: Expectancy, Profit Factor, Max Drawdown, Sharpe, Avg Hold Time
- **System Latency**: Per-stage p50/p95/p99, GPU utilization, memory
- Automated nightly evaluation runs

### 3.13 Dashboard (FR-013)
- Real-time scanner feed with AI analysis
- Chart viewer with vision overlays
- Historical search (similar trades)
- Paper positions & P&L
- Performance analytics
- GPU/system monitoring
- **Tech**: Local web UI (FastAPI + React/HTMX), WebSocket updates

---

## 4. Non-Functional Requirements

| Requirement | Target |
|-------------|--------|
| End-to-end latency (scanner → decision) | < 1 second |
| Market hours uptime | 99.9% |
| Memory usage (idle) | < 8 GB |
| Memory usage (market hours, models loaded) | < 24 GB |
| GPU VRAM usage | < 14 GB (leave 2GB headroom) |
| Disk usage (1 year data) | < 500 GB |
| Model swap time | < 5 seconds |
| Video processing throughput | 6+ hours/hour |

---

## 5. Constraints

- **Hardware**: Single workstation, no cloud inference
- **OS**: Windows 10/11 (primary), Linux compatible
- **Python**: 3.11+ (primary runtime)
- **No microservices**: Modular monolith only
- **No REST internally**: Async event bus (in-process)
- **No Kubernetes/Docker**: Native process management
- **Models**: Local GGUF/ONNX/TensorRT only

---

## 6. Success Metrics

### Trading Performance (Paper → Live)
- Win rate > 55% on paper trades
- Profit factor > 1.5
- Expectancy > $0.50 per $1 risk
- Max drawdown < 5% daily, < 15% monthly

### AI Performance
- Pattern detection F1 > 0.75 per class
- Calibration ECE < 0.05
- Retrieval precision@5 > 0.70

### System Performance
- P99 latency < 1 second (market hours)
- Zero data loss events
- < 1 critical bug per month

---

## 7. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Vision model hallucinates patterns | High | High | High confidence threshold, human review queue, ensemble |
| Overfitting to Ross videos | Medium | High | Strict train/val/test split, out-of-sample evaluation |
| Market data gaps | Medium | Medium | Multiple data sources, gap detection, interpolation flags |
| GPU OOM during market hours | Low | Critical | Model quantization, VRAM budget enforcement, swap policy |
| Regulatory/broker API changes | Low | Medium | Abstract broker interface, paper trading fallback |
| Scope creep | High | High | Phase-gated development, explicit feature rejection |

---

## 8. Out of Scope (Explicitly Deferred)

- Cryptocurrency trading
- Options/derivatives
- Multi-account portfolio management
- Social/trading community features
- Mobile app
- Cloud deployment
- Automated strategy generation (genetic algorithms)
- High-frequency trading (< 1 second hold)
- Fundamental analysis / earnings plays

---

## 9. Acceptance Criteria for MVP (Phase 1-3 Complete)

1. Scanner accepts candidates → produces enriched `StockCandidate`
2. Market data cache serves OHLCV < 50ms
3. Chart engine renders multi-timeframe tensor < 30ms
4. Indicator engine computes all required indicators < 5ms
5. Vision model classifies patterns on test set F1 > 0.70
6. Memory engine retrieves similar trades < 50ms
7. Reasoning engine produces `TradeThesis` with evidence
8. Risk engine rejects invalid trades with specific reason
9. Paper execution simulates fills with slippage model
9. Journal logs all decisions queryable
10. Dashboard displays live scanner + analysis
11. Evaluation framework runs nightly with metrics
12. Video pipeline processes 1 test video end-to-end

---

**Document Version**: 1.0  
**Status**: DRAFT - Requires Human Approval  
**Next Step**: Architecture Review (Phase 2)