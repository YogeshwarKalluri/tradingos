# TradingOS Database Design

## Overview

This document specifies the database architecture for TradingOS. The system uses a **dual-database approach** optimized for different access patterns:
- **DuckDB**: OLAP analytics, structured trade data, time-series market data
- **Qdrant (embedded)**: Vector similarity search for historical trade retrieval

No external database servers. Everything runs in-process.

---

## 1. DuckDB Schema

### 1.1 Market Data Tables

```sql
-- 1-minute OHLCV (primary trading resolution)
CREATE TABLE ohlcv_1m (
    ticker VARCHAR NOT NULL,
    ts TIMESTAMP NOT NULL,          -- Bar open time (NYSE timezone)
    open DOUBLE NOT NULL,
    high DOUBLE NOT NULL,
    low DOUBLE NOT NULL,
    close DOUBLE NOT NULL,
    volume BIGINT NOT NULL,
    vwap DOUBLE,                    -- Volume-weighted average price for the bar
    trades INTEGER,                 -- Number of trades in the bar
    interpolated BOOLEAN DEFAULT FALSE,  -- True if bar was filled during gap
    source VARCHAR DEFAULT 'polygon',    -- Data source identifier
    PRIMARY KEY (ticker, ts)
) PARTITION BY (YEAR(ts), MONTH(ts));

-- 5-minute OHLCV (derived from 1m, materialized for speed)
CREATE TABLE ohlcv_5m (
    ticker VARCHAR NOT NULL,
    ts TIMESTAMP NOT NULL,
    open DOUBLE NOT NULL,
    high DOUBLE NOT NULL,
    low DOUBLE NOT NULL,
    close DOUBLE NOT NULL,
    volume BIGINT NOT NULL,
    vwap DOUBLE,
    PRIMARY KEY (ticker, ts)
) PARTITION BY (YEAR(ts), MONTH(ts));

-- 15-minute OHLCV
CREATE TABLE ohlcv_15m (
    ticker VARCHAR NOT NULL,
    ts TIMESTAMP NOT NULL,
    open DOUBLE NOT NULL,
    high DOUBLE NOT NULL,
    low DOUBLE NOT NULL,
    close DOUBLE NOT NULL,
    volume BIGINT NOT NULL,
    vwap DOUBLE,
    PRIMARY KEY (ticker, ts)
) PARTITION BY (YEAR(ts), MONTH(ts));

-- Daily OHLCV (for longer-term context)
CREATE TABLE ohlcv_daily (
    ticker VARCHAR NOT NULL,
    date DATE NOT NULL,
    open DOUBLE NOT NULL,
    high DOUBLE NOT NULL,
    low DOUBLE NOT NULL,
    close DOUBLE NOT NULL,
    volume BIGINT NOT NULL,
    vwap DOUBLE,
    adj_close DOUBLE,               -- Split/dividend adjusted
    PRIMARY KEY (ticker, date)
);

-- Level 2 snapshots (on-demand, not continuous)
CREATE TABLE level2_snapshots (
    snapshot_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticker VARCHAR NOT NULL,
    ts TIMESTAMP NOT NULL,
    bids JSON NOT NULL,             -- [[price, size], ...] top 20
    asks JSON NOT NULL,             -- [[price, size], ...] top 20
    spread DOUBLE,
    bid_volume BIGINT,
    ask_volume BIGINT
);
CREATE INDEX idx_level2_ticker_ts ON level2_snapshots(ticker, ts);

-- News / sentiment
CREATE TABLE news (
    news_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticker VARCHAR,                 -- NULL for market-wide news
    ts TIMESTAMP NOT NULL,
    headline VARCHAR NOT NULL,
    summary TEXT,
    source VARCHAR NOT NULL,        -- 'benzinga', 'twitter', 'sec'
    sentiment_score DOUBLE,         -- -1 to 1
    relevance_score DOUBLE,         -- 0 to 1
    url VARCHAR
);
CREATE INDEX idx_news_ticker_ts ON news(ticker, ts);
CREATE INDEX idx_news_ts ON news(ts);

-- Fundamental / static data
CREATE TABLE fundamentals (
    ticker VARCHAR PRIMARY KEY,
    company_name VARCHAR,
    sector VARCHAR,
    industry VARCHAR,
    market_cap BIGINT,
    shares_outstanding BIGINT,
    float_shares BIGINT,            -- Critical for momentum
    short_interest DOUBLE,          -- % of float
    short_ratio DOUBLE,             -- Days to cover
    avg_volume_30d BIGINT,
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### 1.2 Trade & Journal Tables

```sql
-- Core trade records (paper + live + extracted from videos)
CREATE TABLE trades (
    trade_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Identification
    ticker VARCHAR NOT NULL,
    entry_time TIMESTAMP NOT NULL,
    exit_time TIMESTAMP,
    direction VARCHAR NOT NULL CHECK (direction IN ('LONG', 'SHORT')),
    
    -- Prices
    entry_price DOUBLE NOT NULL,
    exit_price DOUBLE,
    stop_loss DOUBLE NOT NULL,
    target_1 DOUBLE,
    target_2 DOUBLE,
    target_3 DOUBLE,
    
    -- Sizing & P&L
    position_size DOUBLE NOT NULL,      -- Shares
    position_value DOUBLE NOT NULL,     -- $ at entry
    pnl DOUBLE,                         -- Realized P&L
    pnl_pct DOUBLE,                     -- % return on position
    commission DOUBLE DEFAULT 0,
    slippage DOUBLE DEFAULT 0,
    
    -- Pattern & Setup
    pattern VARCHAR,                    -- 'bull_flag', 'vwap_reclaim', etc.
    setup_quality INTEGER CHECK (setup_quality BETWEEN 1 AND 5),
    market_condition VARCHAR,           -- 'trending', 'choppy', 'high_vol', etc.
    
    -- Risk Metrics (at entry)
    risk_per_share DOUBLE NOT NULL,     -- entry - stop
    risk_total DOUBLE NOT NULL,         -- risk_per_share * size
    risk_reward_ratio DOUBLE,           -- (target - entry) / risk_per_share
    position_pct_equity DOUBLE,         -- % of account at risk
    
    -- Hold time
    hold_minutes INTEGER,
    hold_bars_1m INTEGER,
    
    -- Source & Lineage
    source VARCHAR NOT NULL CHECK (source IN ('paper', 'live', 'ross_video', 'manual', 'backtest')),
    video_source VARCHAR,               -- Filename if from video
    video_timestamp DOUBLE,             -- Seconds into video
    trace_id UUID,                      -- Links to journal_decisions
    
    -- Outcome classification
    outcome VARCHAR CHECK (outcome IN ('win', 'loss', 'breakeven', 'open')),
    exit_reason VARCHAR,                -- 'target_hit', 'stop_hit', 'time_exit', 'manual'
    
    -- Metadata
    notes TEXT,
    tags JSON,                          -- Flexible tagging
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_trades_ticker_time ON trades(ticker, entry_time);
CREATE INDEX idx_trades_pattern ON trades(pattern);
CREATE INDEX idx_trades_source ON trades(source);
CREATE INDEX idx_trades_outcome ON trades(outcome);
CREATE INDEX idx_trades_trace ON trades(trace_id);

-- Journal decisions (immutable audit trail)
CREATE TABLE journal_decisions (
    trace_id UUID PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    
    -- Input candidate
    candidate_json JSON NOT NULL,
    
    -- Pipeline outputs (each stage)
    market_data_json JSON,
    chart_tensor_metadata JSON,         -- Shape, dtype, not the tensor itself
    indicators_json JSON,
    vision_output_json JSON,
    memory_results_json JSON,           -- Array of similar trade_ids + scores
    thesis_json JSON,
    risk_decision_json JSON,
    execution_json JSON,                -- Null if rejected
    
    -- Final outcome (filled after trade closes)
    outcome_json JSON,
    post_analysis_json JSON,            -- Lessons learned, mistakes
    
    -- Performance
    pipeline_latency_ms DOUBLE,
    stage_latencies_json JSON,          -- Per-stage breakdown
    
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_journal_ts ON journal_decisions(timestamp);
CREATE INDEX idx_journal_ticker ON journal_decisions((candidate_json->>'ticker'));

-- Video processing log
CREATE TABLE video_processing_log (
    video_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename VARCHAR NOT NULL UNIQUE,
    file_hash VARCHAR(64) NOT NULL,     -- SHA256 for deduplication
    status VARCHAR NOT NULL CHECK (status IN (
        'pending', 'extracting_audio', 'transcribing', 'extracting_frames',
        'detecting_charts', 'ocr', 'extracting_trades', 'embedding', 'completed', 'failed'
    )),
    current_stage VARCHAR,
    progress_pct DOUBLE DEFAULT 0,
    
    -- Timing
    started_at TIMESTAMP,
    stage_started_at TIMESTAMP,
    completed_at TIMESTAMP,
    total_seconds DOUBLE,
    
    -- Results
    duration_seconds DOUBLE,
    trades_extracted INTEGER DEFAULT 0,
    charts_processed INTEGER DEFAULT 0,
    transcripts_chars INTEGER DEFAULT 0,
    embeddings_generated INTEGER DEFAULT 0,
    
    -- Error handling
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    last_retry_at TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_video_status ON video_processing_log(status);
CREATE INDEX idx_video_hash ON video_processing_log(file_hash);
```

### 1.3 Analytics & Aggregation Tables

```sql
-- Daily performance summary (materialized, refreshed nightly)
CREATE TABLE daily_performance (
    date DATE PRIMARY KEY,
    trades_count INTEGER,
    wins INTEGER,
    losses INTEGER,
    breakeven INTEGER,
    gross_pnl DOUBLE,
    net_pnl DOUBLE,
    commission_total DOUBLE,
    slippage_total DOUBLE,
    win_rate DOUBLE,
    avg_win DOUBLE,
    avg_loss DOUBLE,
    profit_factor DOUBLE,
    expectancy DOUBLE,
    max_drawdown DOUBLE,
    max_drawdown_pct DOUBLE,
    sharpe DOUBLE,
    sortino DOUBLE,
    avg_hold_minutes DOUBLE,
    best_trade DOUBLE,
    worst_trade DOUBLE
);

-- Pattern performance (materialized)
CREATE TABLE pattern_performance (
    pattern VARCHAR PRIMARY KEY,
    trades_count INTEGER,
    wins INTEGER,
    losses INTEGER,
    win_rate DOUBLE,
    avg_pnl DOUBLE,
    avg_pnl_pct DOUBLE,
    profit_factor DOUBLE,
    expectancy DOUBLE,
    avg_hold_minutes DOUBLE,
    best_setup_quality_avg DOUBLE,
    last_updated TIMESTAMP DEFAULT NOW()
);

-- Model performance tracking
CREATE TABLE model_performance (
    model_name VARCHAR NOT NULL,
    eval_date DATE NOT NULL,
    dataset VARCHAR NOT NULL,           -- 'train', 'val', 'test', 'paper_live'
    metric_name VARCHAR NOT NULL,       -- 'precision', 'recall', 'f1', 'ece', 'latency_p99'
    metric_value DOUBLE NOT NULL,
    sample_size INTEGER,
    PRIMARY KEY (model_name, eval_date, dataset, metric_name)
);
```

---

## 2. Qdrant Collection Design

### 2.1 Trade Embeddings Collection

```python
# Collection: trade_embeddings
# Vector size: 768 (BGE-large-en-v1.5 text + vision features concatenated)
# Distance: Cosine
# HNSW Index: M=16, ef_construct=200, ef_search=128
# Quantization: Scalar quantization (INT8) for memory efficiency

PAYLOAD_SCHEMA = {
    # Primary identifiers
    "trade_id": "uuid",           # PRIMARY KEY (indexed)
    "trace_id": "uuid",           # Links to journal (indexed)
    
    # Filterable fields (all indexed for fast filtering)
    "ticker": "keyword",          # Exact match
    "pattern": "keyword",         # Exact match: 'bull_flag', 'vwap_reclaim', etc.
    "direction": "keyword",       # 'LONG' or 'SHORT'
    "outcome": "keyword",         # 'win', 'loss', 'breakeven'
    "source": "keyword",          # 'paper', 'live', 'ross_video', 'backtest'
    "market_condition": "keyword", # 'trending_up', 'trending_down', 'choppy', 'high_vol'
    
    # Numeric range filters (all indexed)
    "entry_time": "datetime",     # Range queries
    "exit_time": "datetime",
    "market_cap": "float",        # Dollar value
    "float_shares": "integer",    # Shares
    "rel_volume": "float",        # Relative volume at entry
    "gap_pct": "float",           # Gap percentage
    "setup_quality": "integer",   # 1-5
    "risk_reward_ratio": "float",
    "position_pct_equity": "float",
    "hold_minutes": "integer",
    "pnl_pct": "float",
    
    # Non-filterable metadata (stored but not indexed)
    "entry_price": "float",
    "stop_loss": "float",
    "targets": "float[]",         # Array of targets
    "reasoning_text": "text",     # Human-readable thesis
    "video_source": "keyword",    # Source video filename
    "video_timestamp": "float",   # Seconds into video
    "chart_images": "keyword[]",  # Paths to chart images
    "transcript_segment": "text", # Relevant transcript portion
}

# Payload indexes to create:
# - keyword: ticker, pattern, direction, outcome, source, market_condition, video_source
# - datetime: entry_time, exit_time
# - float: market_cap, float_shares, rel_volume, gap_pct, risk_reward_ratio, pnl_pct
# - integer: setup_quality, hold_minutes
```

### 2.2 Video Segment Embeddings Collection

```python
# Collection: video_segments
# Vector size: 768 (BGE-large-en-v1.5)
# Purpose: Semantic search over Ross video transcripts

PAYLOAD_SCHEMA = {
    "video_id": "uuid",
    "filename": "keyword",
    "segment_id": "integer",      # Sequential within video
    "start_time": "float",        # Seconds
    "end_time": "float",
    "speaker": "keyword",         # 'ross', 'chat', 'alert'
    "text": "text",               # Full transcript segment
    "tickers_mentioned": "keyword[]",
    "patterns_discussed": "keyword[]",
    "trade_events": "keyword[]",  # 'entry', 'exit', 'stop_adjust', 'size_change'
    "chart_frames": "keyword[]",  # Associated frame paths
}
```

---

## 3. Data Flow & ETL

### 3.1 Market Data Ingestion

```
Polygon WebSocket (1m bars)
        │
        ▼
┌───────────────────────┐
│  Ingestion Worker     │  (async, batches of 100)
│  - Validate schema    │
│  - Detect gaps        │
│  - Interpolate if <5m │
│  - Compute VWAP       │
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│  DuckDB Bulk Insert   │  (COPY or batched INSERT)
│  - Partition by month │
│  - Upsert on conflict │
└───────────────────────┘
            │
            ▼
    Materialize 5m/15m
    (async, after 1m commit)
```

**Gap Handling**:
- Missing bars > 5 minutes → `interpolated=true`, linear interpolation
- Missing bars ≤ 5 minutes → forward fill from previous bar
- Emit `DataQualityWarning` event for monitoring

### 3.2 Trade Journal Write Path

```
Trade Decision (trace_id)
        │
        ├─► journal_decisions (async, fire-and-forget)
        │
        └─► If executed: trades table (after fill)
                │
                ├─► Generate embedding (async)
                │       │
                │       ▼
                │  Qdrant upsert (vector + payload)
                │
                └─► Update daily_performance (nightly materialization)
```

### 3.3 Video Processing Write Path

```
Video File
        │
        ▼
video_processing_log (status='pending')
        │
        ▼
Stage 1: Audio Extraction → status='transcribing'
        │
        ▼
Stage 2: STT → transcript segments
        │
        ▼
Stage 3: Frame Extraction → status='detecting_charts'
        │
        ▼
Stage 4: Chart Detection + OCR → chart frames with metadata
        │
        ▼
Stage 5: Trade Extraction (LLM + vision) → structured trades
        │
        ▼
Stage 6: Embedding Generation
        │       ├─► Text embeddings → video_segments collection
        │       └─► Trade embeddings → trade_embeddings collection
        │
        ▼
Stage 7: DuckDB Insert (trades table)
        │
        ▼
video_processing_log (status='completed', trades_extracted=N)
```

---

## 4. Query Patterns & Optimization

### 4.1 Hot Path Queries (Must be < 50ms)

```sql
-- 1. Get OHLCV for chart generation (single ticker, time range)
SELECT ts, open, high, low, close, volume, vwap
FROM ohlcv_1m
WHERE ticker = ? AND ts BETWEEN ? AND ?
ORDER BY ts;

-- 2. Get latest bar for real-time indicator update
SELECT * FROM ohlcv_1m
WHERE ticker = ?
ORDER BY ts DESC LIMIT 1;

-- 3. Get similar trades (vector search in Qdrant, then fetch details)
-- Done via Qdrant API, then:
SELECT * FROM trades WHERE trade_id IN (?, ?, ...);

-- 4. Get fundamentals for candidate enrichment
SELECT * FROM fundamentals WHERE ticker = ?;
```

### 4.2 Analytics Queries (Can be slower, run after hours)

```sql
-- Daily P&L
SELECT date, net_pnl, win_rate, profit_factor, max_drawdown_pct
FROM daily_performance
WHERE date >= ? ORDER BY date;

-- Pattern win rates
SELECT pattern, trades_count, win_rate, avg_pnl, profit_factor
FROM pattern_performance
WHERE trades_count >= 20
ORDER BY profit_factor DESC;

-- Model calibration
SELECT model_name, eval_date, metric_value as ece
FROM model_performance
WHERE metric_name = 'ece' AND dataset = 'test'
ORDER BY eval_date;
```

---

## 5. Maintenance & Operations

### 5.1 Partition Management

```sql
-- Monthly partition maintenance (run 1st of month)
-- DuckDB handles automatically via PARTITION BY
-- But we can manually detach old partitions for archival

-- Archive partitions older than 2 years to Parquet
COPY (SELECT * FROM ohlcv_1m WHERE ts < ?) TO 'archive/ohlcv_1m_YYYY_MM.parquet';
-- Then DELETE from main table
```

### 5.2 Qdrant Maintenance

```python
# Weekly: Optimize HNSW index
qdrant_client.update_collection(
    collection_name="trade_embeddings",
    optimizer_config=OptimizersConfigDiff(
        indexing_threshold=20000,  # Re-index when 20k new vectors
    )
)

# Monthly: Recreate collection with fresh index (if drift detected)
# 1. Scroll all vectors
# 2. Create new collection
# 3. Batch upsert
# 4. Swap alias
```

### 5.3 Backup Strategy

| Data | Frequency | Retention | Location |
|------|-----------|-----------|----------|
| DuckDB file | Daily (snapshot) | 30 days | Local NVMe + Cloud (encrypted) |
| Qdrant data | Weekly | 90 days | Local NVMe |
| Video originals | On ingest | Permanent | Local NVMe (2TB) |
| Model artifacts | On change | Permanent | Local NVMe + Git LFS |
| Config/Secrets | On change | Permanent | Git (encrypted) |

---

## 6. Migration Strategy

```python
# Schema version in DuckDB
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT NOW(),
    description VARCHAR
);

# Migration example (v1 -> v2)
-- Migration: Add 'tags' column to trades
ALTER TABLE trades ADD COLUMN tags JSON DEFAULT '[]'::JSON;
INSERT INTO schema_version (version, description) VALUES (2, 'Add tags column');
```

- Migrations are **additive only** (no destructive changes)
- New columns default to NULL or sensible defaults
- Backfill via separate async job if needed

---

## 7. Performance Targets

| Operation | Target | Notes |
|-----------|--------|-------|
| 1m OHLCV range query (1 day) | < 10ms | Partitioned, indexed |
| Latest bar lookup | < 2ms | Covered by PK |
| Trade insert (DuckDB) | < 5ms | Batched |
| Qdrant vector search (k=10) | < 20ms | HNSW, quantized |
| Qdrant + DuckDB combined | < 50ms | Parallel |
| Daily performance materialization | < 30s | Full scan |
| Video trade insertion (batch) | < 100ms/trade | Bulk embed + insert |

---

**Document Version**: 1.0  
**Status**: DRAFT - Requires Human Approval  
**Next Step**: Video Learning Pipeline Design