# TradingOS Video Learning Pipeline Design

## Overview

This document specifies the fully automated pipeline for extracting trading knowledge from Ross Cameron educational videos. The pipeline runs **after market hours only** and requires zero manual intervention after initial setup.

**Input**: Video files dropped into `knowledge/ross_videos/inbox/`
**Output**: Structured trades in knowledge base (DuckDB + Qdrant) with embeddings

---

## 1. Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        VIDEO LEARNING PIPELINE                                   │
└─────────────────────────────────────────────────────────────────────────────────┘

knowledge/ross_videos/inbox/*.mp4
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 1. FILE WATCHER & ORCHESTRATOR                                                   │
│    - Watch inbox/ for new files                                                 │
│    - Compute SHA256, check duplicates                                           │
│    - Move to processing/                                                        │
│    - Create video_processing_log entry                                          │
│    - Launch pipeline stages sequentially (one video at a time)                  │
└─────────────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 2. AUDIO EXTRACTION (ffmpeg)                                                     │
│    Input: video.mp4                                                             │
│    Output: audio.wav (16kHz, mono, PCM)                                         │
│    Command: ffmpeg -i video.mp4 -vn -acodec pcm_s16le -ar 16000 -ac 1 audio.wav │
│    Duration: ~30s per hour of video                                             │
└─────────────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 3. SPEECH-TO-TEXT (faster-whisper large-v3, CUDA)                              │
│    Model: large-v3 (1550M params, ~3GB VRAM, CT2 FP16)                          │
│    Output: segments with word-level timestamps                                  │
│    {                                                                             │
│      "start": 123.45, "end": 128.90,                                            │
│      "text": "I'm buying AAPL here at 150.25",                                  │
│      "words": [{"word": "I'm", "start": 123.45, "end": 123.67, "prob": 0.99},  │
│                ...]                                                             │
│    }                                                                            │
│    Diarization: pyannote.audio (separate Ross vs chat vs alerts)                │
│    Duration: ~2-3 min per hour of video (batched, GPU)                          │
└─────────────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 4. FRAME EXTRACTION (ffmpeg)                                                     │
│    - Extract 1 FPS keyframes → frames/frame_%06d.jpg                            │
│    - Also extract I-frames for higher quality at scene changes                  │
│    - Total: ~3600 frames per hour                                               │
│    Duration: ~10s per hour                                                       │
└─────────────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 5. CHART FRAME CLASSIFICATION (CNN)                                             │
│    Model: MobileNetV3-small (ONNX, FP16, ~5MB, <10ms/frame)                    │
│    Classes: [chart, thinkorswim_chart, trader_view, face, slides, other]       │
│    Output: chart_frames.json with timestamps & paths                            │
│    Filter: Keep only 'chart' and 'thinkorswim_chart' frames                     │
│    Duration: ~30s per hour (batched)                                            │
└─────────────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 6. CHART REGION DETECTION & OCR                                                 │
│    ┌─────────────────────────────────────────────────────────────────────────┐   │
│    │ 6a. Chart Region Detection (YOLOv8n, TensorRT)                          │   │
│    │     Detect: [candle_area, volume_area, indicator_panels, ticker_bar,    │   │
│    │            timeframe_bar, price_scale, time_scale, vwap_line, ema_lines]│   │
│    └─────────────────────────────────────────────────────────────────────────┘   │
│    ┌─────────────────────────────────────────────────────────────────────────┐   │
│    │ 6b. OCR (PaddleOCR PP-OCRv4, ONNX)                                      │   │
│    │     Regions: ticker_bar → ticker, timeframe_bar → timeframe,            │   │
│    │              price_scale → price levels, indicator_panels → values      │   │
│    │     Output per frame:                                                    │   │
│    │     {                                                                    │   │
│    │       "timestamp": 1234.5,                                              │   │
│    │       "ticker": "AAPL",                                                 │   │
│    │       "timeframe": "1m",                                                │   │
│    │       "price": 150.25,                                                  │   │
│    │       "vwap": 149.80,                                                   │   │
│    │       "ema9": 149.50, "ema20": 148.90,                                  │   │
│    │       "volume": 125000,                                                 │   │
│    │       "indicators": {"rsi": 65, "macd": "0.12"}                         │   │
│    │     }                                                                    │   │
│    └─────────────────────────────────────────────────────────────────────────┘   │
│    Duration: ~1-2 min per hour (batched)                                        │
└─────────────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 7. TIMESTAMP ALIGNMENT                                                           │
│    - Map transcript segments → video timestamps                                 │
│    - Map chart frames → video timestamps                                        │
│    - Find overlaps: transcript trade talk + chart showing same ticker           │
│    - Output: aligned_segments.json                                              │
│    {                                                                             │
│      "segment_id": 42,                                                          │
│      "start": 1230.0, "end": 1260.0,                                            │
│      "transcript": "I'm buying AAPL here at 150.25, stop at 149.50",           │
│      "ticker": "AAPL",                                                          │
│      "chart_frames": [frame_1230.jpg, frame_1231.jpg, ...],                    │
│      "ocr_data": [{...}, {...}]                                                 │
│    }                                                                            │
└─────────────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 8. TRADE EVENT EXTRACTION (LLM-Assisted)                                        │
│    Model: Llama-3.2-3B-Instruct (GGUF Q4_K_M, local)                            │
│    Prompt: Structured extraction from transcript + OCR context                  │
│    ┌─────────────────────────────────────────────────────────────────────────┐   │
│    │ SYSTEM: Extract trade events from Ross Cameron video segment.           │   │
│    │ Output JSON only.                                                       │   │
│    │                                                                          │   │
│    │ TRANSCRIPT: "I'm buying AAPL here at 150.25, stop at 149.50,           │   │
│    │            targeting 152. Position size 1000 shares."                   │   │
│    │                                                                          │   │
│    │ OCR_CONTEXT: ticker=AAPL, price=150.25, vwap=149.80, ema9=149.50       │   │
│    │                                                                          │   │
│    │ OUTPUT:                                                                 |   │
│    │ {                                                                      │   │
│    │   "events": [                                                          │   │
│    │     {                                                                  │   │
│    │       "type": "ENTRY",                                                 │   │
│    │       "ticker": "AAPL",                                                │   │
│    │       "price": 150.25,                                                 │   │
│    │       "size": 1000,                                                    │   │
│    │       "direction": "LONG",                                             │   │
│    │       "stop": 149.50,                                                  │   │
│    │       "targets": [152.00],                                             │   │
│    │       "reasoning": "Breakout above VWAP with high relative volume",    │   │
│    │       "confidence": 0.92                                               │   │
│    │     }                                                                  │   │
│    │   ]                                                                    │   │
│    │ }                                                                      │   │
│    └─────────────────────────────────────────────────────────────────────────┘   │
│    Duration: ~30s per hour (batched, parallel segments)                         │
└─────────────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 9. PATTERN LABELING (Vision Engine)                                             │
│    - Run Vision Engine (pattern classifier) on chart frames at entry            │
│    - Get pattern probabilities: bull_flag=0.72, vwap_reclaim=0.15, ...         │
│    - Assign primary pattern = argmax                                            │
│    - Flag low confidence (< 0.6) for human review queue                         │
└─────────────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 10. OUTCOME DETERMINATION                                                        │
│    - If video shows exit: extract exit price, reason, P&L                       │
│    - If not shown: query historical data (DuckDB) for ticker + entry time       │
│      → Simulate to next stop/target/time exit                                   │
│    - Label: win / loss / breakeven / unknown                                    │
└─────────────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 11. EMBEDDING GENERATION                                                         │
│    ┌─────────────────────────────────────────────────────────────────────────┐   │
│    │ 11a. Text Embedding (BGE-large-en-v1.5, ONNX FP16)                     │   │
│    │     Input: transcript_segment + reasoning + pattern + outcome          │   │
│    │     Output: 1024-dim → project to 768-dim                              │   │
│    └─────────────────────────────────────────────────────────────────────────┘   │
│    ┌─────────────────────────────────────────────────────────────────────────┐   │
│    │ 11b. Chart Embedding (Vision Engine pooled features)                    │   │
│    │     Input: ChartTensor at entry → Vision backbone → global avg pool    │   │
│    │     Output: 512-dim → project to 768-dim                               │   │
│    └─────────────────────────────────────────────────────────────────────────┘   │
│    ┌─────────────────────────────────────────────────────────────────────────┐   │
│    │ 11c. Combined Embedding                                                  │   │
│    │     combined = 0.6 * text_emb + 0.4 * chart_emb                        │   │
│    │     L2 normalize                                                        │   │
│    └─────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 12. KNOWLEDGE BASE INSERT                                                        │
│    ┌─────────────────────────────────────────────────────────────────────────┐   │
│    │ DuckDB: trades table                                                    │   │
│    │   - All structured fields                                               │   │
│    │   - source='ross_video'                                                 │   │
│    │   - video_source, video_timestamp                                       │   │
│    │   - setup_quality from pattern confidence                               │   │
│    └─────────────────────────────────────────────────────────────────────────┘   │
│    ┌─────────────────────────────────────────────────────────────────────────┐   │
│    │ Qdrant: trade_embeddings collection                                     │   │
│    │   - Vector: combined embedding                                          │   │
│    │   - Payload: all filterable fields                                      │   │
│    └─────────────────────────────────────────────────────────────────────────┘   │
│    ┌─────────────────────────────────────────────────────────────────────────┐   │
│    │ Qdrant: video_segments collection                                       │   │
│    │   - Vector: text embedding of transcript segment                        │   │
│    │   - Payload: segment metadata                                           │   │
│    └─────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 13. COMPLETION & CLEANUP                                                         │
│    - Update video_processing_log: status='completed', trades_extracted=N       │
│    - Move video to done/                                                        │
│    - Delete intermediate frames (keep charts)                                   │
│    - Emit VideoProcessed event for evaluation update                            │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Stage Specifications

### 2.1 Models Used in Pipeline

| Stage | Model | Format | VRAM | Latency (per hour video) |
|-------|-------|--------|------|--------------------------|
| STT | faster-whisper large-v3 | CT2 FP16 | 3GB | 2-3 min |
| Diarization | pyannote.audio | PyTorch | 1GB | 1 min |
| Chart Classifier | MobileNetV3-small | ONNX FP16 | 0.1GB | 30s |
| Chart Detector | YOLOv8n | TensorRT FP16 | 0.5GB | 1 min |
| OCR | PaddleOCR PP-OCRv4 | ONNX FP16 | 0.5GB | 1 min |
| Trade Extractor | Llama-3.2-3B-Instruct | GGUF Q4_K_M | 2GB | 30s |
| Pattern Labeler | Vision Engine (shared) | TensorRT | 4.5GB | 10s |
| Text Embedder | BGE-large-en-v1.5 | ONNX FP16 | 1GB | 10s |
| **Peak VRAM** | | | **~12GB** | |

**Pipeline runs sequentially** (one video at a time) to stay within VRAM budget.

### 2.2 Data Structures

```python
# Intermediate representations (saved as JSON for debugging/reprocessing)

@dataclass
class TranscriptSegment:
    segment_id: int
    start: float
    end: float
    text: str
    words: List[WordTimestamp]
    speaker: str  # 'ross', 'chat', 'alert'
    confidence: float

@dataclass
class ChartFrame:
    frame_id: int
    timestamp: float
    path: str
    ocr_data: OCRData
    chart_regions: List[ChartRegion]

@dataclass
class OCRData:
    ticker: Optional[str]
    timeframe: Optional[str]
    price: Optional[float]
    vwap: Optional[float]
    ema9: Optional[float]
    ema20: Optional[float]
    volume: Optional[int]
    indicators: Dict[str, float]

@dataclass
class AlignedSegment:
    segment_id: int
    start: float
    end: float
    transcript: str
    speaker: str
    ticker: Optional[str]
    chart_frames: List[ChartFrame]
    trade_events: List[TradeEvent]

@dataclass
class TradeEvent:
    event_id: str
    type: Literal["ENTRY", "EXIT", "STOP_ADJUST", "SIZE_CHANGE", "TARGET_UPDATE"]
    ticker: str
    timestamp: float
    price: Optional[float]
    size: Optional[float]
    direction: Optional[Literal["LONG", "SHORT"]]
    stop: Optional[float]
    targets: List[float]
    reasoning: str
    confidence: float
    pattern: Optional[str]  # Filled by pattern labeler
    outcome: Optional[Literal["win", "loss", "breakeven", "unknown"]]
```

---

## 3. Error Handling & Resilience

### 3.1 Retry Policy

| Stage | Max Retries | Backoff | Failure Action |
|-------|-------------|---------|----------------|
| Audio Extraction | 2 | 5s | Mark video failed |
| STT | 2 | 10s | Mark video failed |
| Frame Extraction | 1 | 5s | Mark video failed |
| Chart Classification | 1 | 5s | Skip frame |
| OCR | 1 | 5s | Skip frame |
| Trade Extraction | 2 | 10s | Mark segment failed |
| Embedding | 1 | 5s | Mark video failed |
| KB Insert | 3 | 5s | Alert, keep in processing/ |

### 3.2 Checkpointing

Each stage writes output to `processing/<video_id>/stage_N_output.json`
- Allows resume from failure point
- Enables debugging without re-running full pipeline
- Automatic cleanup on success (keep only final outputs)

### 3.3 Human Review Queue

Low-confidence items queued for review:
- Pattern confidence < 0.6
- Trade extraction confidence < 0.7
- OCR ticker detection failed
- Outcome unknown

Review UI: Simple web interface showing video clip + extracted data + edit capability

---

## 4. Quality Assurance

### 4.1 Validation Rules

```python
def validate_trade(trade: ExtractedTrade) -> List[ValidationError]:
    errors = []
    
    # Required fields
    if not trade.ticker or not re.match(r'^[A-Z]{1,5}$', trade.ticker):
        errors.append("Invalid ticker")
    if trade.entry_price is None or trade.entry_price <= 0:
        errors.append("Invalid entry price")
    if trade.stop_loss is None or trade.stop_loss <= 0:
        errors.append("Invalid stop loss")
    if trade.direction not in ("LONG", "SHORT"):
        errors.append("Invalid direction")
    
    # Logic checks
    if trade.direction == "LONG":
        if trade.stop_loss >= trade.entry_price:
            errors.append("LONG stop must be below entry")
        if trade.targets and any(t <= trade.entry_price for t in trade.targets):
            errors.append("LONG targets must be above entry")
    else:  # SHORT
        if trade.stop_loss <= trade.entry_price:
            errors.append("SHORT stop must be above entry")
        if trade.targets and any(t >= trade.entry_price for t in trade.targets):
            errors.append("SHORT targets must be below entry")
    
    # Risk/reward sanity
    if trade.stop_loss and trade.targets:
        risk = abs(trade.entry_price - trade.stop_loss)
        reward = min(abs(t - trade.entry_price) for t in trade.targets)
        if reward / risk < 0.5:
            errors.append(f"Poor R:R {reward/risk:.2f}")
    
    return errors
```

### 4.2 Ground Truth Evaluation

- Maintain `evaluations/ground_truth/` with manually labeled videos
- Run pipeline on ground truth monthly
- Measure: Extraction precision/recall, pattern accuracy, price accuracy
- Target: > 85% trade extraction F1, > 80% pattern accuracy

---

## 5. Automation & Scheduling

### 5.1 File Watcher (Continuous)

```python
# Runs as background task in main process
async def video_file_watcher():
    inbox = Path("knowledge/ross_videos/inbox")
    while True:
        for video_path in inbox.glob("*.mp4"):
            if not is_processing(video_path):
                await queue_video(video_path)
        await asyncio.sleep(10)  # Check every 10s
```

### 5.2 Pipeline Scheduler (After Hours Only)

```python
# Only runs 16:30 - 08:00 ET
async def pipeline_scheduler():
    while True:
        now = datetime.now(ET)
        if is_market_hours(now):
            await sleep_until(market_close + 30min)
            continue
        
        if video_queue and gpu_available():
            video = video_queue.pop(0)
            await run_pipeline(video)
        else:
            await asyncio.sleep(60)
```

### 5.3 Monitoring

- **Prometheus metrics**: `video_pipeline_duration_seconds`, `video_pipeline_trades_extracted`, `video_pipeline_errors_total`
- **Alerts**: Pipeline stuck > 2 hours, failure rate > 20%, VRAM OOM
- **Dashboard**: Processing queue, current stage, throughput

---

## 6. Storage Layout

```
knowledge/
└── ross_videos/
    ├── inbox/              # Drop new videos here
    ├── processing/         # Active processing (one subdir per video)
    │   └── <video_id>/
    │       ├── audio.wav
    │       ├── transcript.json
    │       ├── frames/
    │       ├── chart_frames.json
    │       ├── aligned_segments.json
    │       ├── trade_events.json
    │       └── embeddings.npy
    ├── done/               # Successfully processed
    │   └── <video_id>.mp4
    ├── failed/             # Failed after retries
    │   └── <video_id>.mp4
    ├── charts/             # Extracted chart images (kept permanently)
    │   └── <trade_id>/
    │       ├── entry_chart.jpg
    │       └── exit_chart.jpg
    └── review_queue/       # Human review needed
        └── <review_id>.json
```

---

## 7. Performance Targets

| Metric | Target |
|--------|--------|
| End-to-end (1 hour video) | < 10 minutes |
| Peak VRAM usage | < 12 GB |
| Disk temp usage (1 hour) | < 5 GB |
| Trade extraction F1 (eval) | > 0.85 |
| Pattern accuracy (eval) | > 0.80 |
| Price extraction MAE | < $0.05 |
| Automation rate (no review) | > 90% |

---

## 8. Future Enhancements

1. **Multi-speaker attribution**: Better diarization for Ross vs guests
2. **Chart reconstruction**: Rebuild OHLCV from chart images for backtesting
3. **Incremental learning**: Fine-tune extractor on review corrections
4. **Cross-video linking**: Identify same trade discussed across videos
5. **Real-time mode**: Process live stream segments (future)

---

**Document Version**: 1.0  
**Status**: DRAFT - Requires Human Approval  
**Next Step**: Model Selection Strategy