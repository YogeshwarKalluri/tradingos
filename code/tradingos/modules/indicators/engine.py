"""Indicator Engine - Vectorized technical indicator calculations."""

from typing import Any

import numpy as np
from numba import jit

from tradingos.core.logging import get_logger
from tradingos.modules.indicators.interfaces import IndicatorEngine, IndicatorSnapshot

logger = get_logger(__name__)


@jit(nopython=True)
def _sma(values: np.ndarray, period: int) -> np.ndarray:
    """Simple Moving Average."""
    result = np.full_like(values, np.nan)
    for i in range(period - 1, len(values)):
        result[i] = np.mean(values[i - period + 1:i + 1])
    return result


@jit(nopython=True)
def _ema(values: np.ndarray, period: int) -> np.ndarray:
    """Exponential Moving Average."""
    result = np.full_like(values, np.nan)
    alpha = 2.0 / (period + 1)
    result[period - 1] = np.mean(values[:period])
    for i in range(period, len(values)):
        result[i] = alpha * values[i] + (1 - alpha) * result[i - 1]
    return result


@jit(nopython=True)
def _vwap(
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    volumes: np.ndarray,
) -> np.ndarray:
    """Volume Weighted Average Price."""
    typical_price = (highs + lows + closes) / 3.0
    result = np.full_like(closes, np.nan)
    cum_tpv = 0.0
    cum_vol = 0.0
    for i in range(len(closes)):
        cum_tpv += typical_price[i] * volumes[i]
        cum_vol += volumes[i]
        if cum_vol > 0:
            result[i] = cum_tpv / cum_vol
    return result


@jit(nopython=True)
def _atr(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14) -> np.ndarray:
    """Average True Range."""
    result = np.full_like(closes, np.nan)
    tr = np.zeros_like(closes)

    for i in range(1, len(closes)):
        tr[i] = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1])
        )

    for i in range(period, len(closes)):
        if i == period:
            result[i] = np.mean(tr[1:period + 1])
        else:
            result[i] = (result[i - 1] * (period - 1) + tr[i]) / period

    return result


@jit(nopython=True)
def _rvol(volumes: np.ndarray, period: int = 20) -> np.ndarray:
    """Relative Volume vs moving average."""
    result = np.full_like(volumes, np.nan, dtype=np.float64)
    vol_ma = _sma(volumes.astype(np.float64), period)
    for i in range(period - 1, len(volumes)):
        if vol_ma[i] > 0:
            result[i] = volumes[i] / vol_ma[i]
    return result


@jit(nopython=True)
def _gap_pct(opens: np.ndarray, prev_closes: np.ndarray) -> np.ndarray:
    """Gap percentage from previous close."""
    result = np.full_like(opens, np.nan)
    for i in range(1, len(opens)):
        if prev_closes[i] > 0:
            result[i] = (opens[i] - prev_closes[i]) / prev_closes[i] * 100.0
    return result


@jit(nopython=True)
def _rsi(closes: np.ndarray, period: int = 14) -> np.ndarray:
    """Relative Strength Index."""
    result = np.full_like(closes, np.nan)
    if len(closes) < period + 1:
        return result

    gains = np.zeros_like(closes)
    losses = np.zeros_like(closes)

    for i in range(1, len(closes)):
        diff = closes[i] - closes[i - 1]
        if diff > 0:
            gains[i] = diff
        else:
            losses[i] = -diff

    avg_gain = np.mean(gains[1:period + 1])
    avg_loss = np.mean(losses[1:period + 1])

    if avg_loss == 0:
        result[period] = 100.0
    else:
        rs = avg_gain / avg_loss
        result[period] = 100.0 - (100.0 / (1.0 + rs))

    for i in range(period + 1, len(closes)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0:
            result[i] = 100.0
        else:
            rs = avg_gain / avg_loss
            result[i] = 100.0 - (100.0 / (1.0 + rs))

    return result


class VectorizedIndicatorEngine(IndicatorEngine):
    """High-performance vectorized indicator engine using Numba JIT."""

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.ema_periods = self.config.get("ema_periods", [9, 20, 50, 200])
        self.atr_period = self.config.get("atr_period", 14)
        self.rvol_period = self.config.get("rvol_period", 20)
        self.rsi_period = self.config.get("rsi_period", 14)
        logger.info("indicator_engine_initialized", config=self.config)

    async def calculate(self, bars: dict[str, Any]) -> IndicatorSnapshot:
        """Calculate all indicators for the latest bar across timeframes."""
        # Use 1m bars for primary calculation
        bars_1m = bars.get("bars_1m", [])
        if not bars_1m:
            return IndicatorSnapshot(ticker="", timestamp="")

        # Extract arrays
        n = len(bars_1m)
        opens = np.array([b["open"] for b in bars_1m], dtype=np.float64)
        highs = np.array([b["high"] for b in bars_1m], dtype=np.float64)
        lows = np.array([b["low"] for b in bars_1m], dtype=np.float64)
        closes = np.array([b["close"] for b in bars_1m], dtype=np.float64)
        volumes = np.array([b.get("volume", 0) for b in bars_1m], dtype=np.float64)

        # Get latest values
        latest_idx = n - 1
        ticker = bars_1m[latest_idx].get("ticker", "")
        timestamp = bars_1m[latest_idx].get("ts", "")
        if hasattr(timestamp, "isoformat"):
            timestamp = timestamp.isoformat()

        # VWAP
        vwap_arr = _vwap(highs, lows, closes, volumes)
        vwap = float(vwap_arr[latest_idx]) if not np.isnan(vwap_arr[latest_idx]) else None

        # EMAs
        emas = {}
        for period in self.ema_periods:
            ema_arr = _ema(closes, period)
            val = ema_arr[latest_idx]
            emas[f"ema_{period}"] = float(val) if not np.isnan(val) else None

        # ATR
        atr_arr = _atr(highs, lows, closes, self.atr_period)
        atr = float(atr_arr[latest_idx]) if not np.isnan(atr_arr[latest_idx]) else None

        # RVol
        rvol_arr = _rvol(volumes, self.rvol_period)
        rvol = float(rvol_arr[latest_idx]) if not np.isnan(rvol_arr[latest_idx]) else None

        # Gap %
        prev_closes = np.roll(closes, 1)
        prev_closes[0] = closes[0]
        gap_arr = _gap_pct(opens, prev_closes)
        gap_pct = float(gap_arr[latest_idx]) if not np.isnan(gap_arr[latest_idx]) else None

        # RSI
        rsi_arr = _rsi(closes, self.rsi_period)
        rsi = float(rsi_arr[latest_idx]) if not np.isnan(rsi_arr[latest_idx]) else None

        # Additional indicators
        indicators = {}
        for period in self.ema_periods:
            indicators[f"ema_{period}"] = emas.get(f"ema_{period}")
        indicators["rsi"] = rsi
        indicators["atr_pct"] = (
            atr / closes[latest_idx] * 100
            if atr and closes[latest_idx] > 0
            else None
        )

        return IndicatorSnapshot(
            ticker=ticker,
            timestamp=timestamp,
            vwap=vwap,
            ema_9=emas.get("ema_9"),
            ema_20=emas.get("ema_20"),
            ema_50=emas.get("ema_50"),
            ema_200=emas.get("ema_200"),
            atr=atr,
            rvol=rvol,
            gap_pct=gap_pct,
            indicators=indicators,
        )


def create_indicator_engine(config: dict[str, Any] | None = None) -> IndicatorEngine:
    """Factory function to create indicator engine."""
    return VectorizedIndicatorEngine(config)
