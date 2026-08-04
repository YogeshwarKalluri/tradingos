"""Gap detection and interpolation for market data."""

from datetime import timedelta

from tradingos.core.logging import get_logger

logger = get_logger(__name__)


class GapDetector:
    """Detect and handle gaps in market data."""

    def __init__(self, max_gap_minutes: int = 5, interpolate_small_gaps: bool = True):
        self.max_gap_minutes = max_gap_minutes
        self.interpolate_small_gaps = interpolate_small_gaps

    def detect_gaps(
        self,
        bars: list[dict],
        timeframe: str,
        expected_interval: timedelta,
    ) -> list[dict]:
        """Detect gaps in bar sequence."""
        if len(bars) < 2:
            return []

        gaps = []
        for i in range(1, len(bars)):
            prev_ts = bars[i - 1]["ts"]
            curr_ts = bars[i]["ts"]
            expected_ts = prev_ts + expected_interval

            if curr_ts > expected_ts:
                gap_minutes = (curr_ts - expected_ts).total_seconds() / 60
                gaps.append({
                    "gap_start": expected_ts,
                    "gap_end": curr_ts,
                    "gap_minutes": gap_minutes,
                    "missing_bars": int(gap_minutes / expected_interval.total_seconds() * 60),
                })

        return gaps

    def interpolate_gaps(
        self,
        bars: list[dict],
        gaps: list[dict],
        expected_interval: timedelta,
    ) -> list[dict]:
        """Interpolate missing bars for small gaps."""
        if not self.interpolate_small_gaps or not gaps:
            return bars

        result = []
        for i, bar in enumerate(bars):
            result.append(bar)

            # Check if there's a gap after this bar
            gap = next((g for g in gaps if g["gap_start"] == bar["ts"] + expected_interval), None)
            if gap and gap["gap_minutes"] <= self.max_gap_minutes and i + 1 < len(bars):
                # Linear interpolation between bar[i] and bar[i+1]
                next_bar = bars[i + 1]
                missing = gap["missing_bars"]
                for m in range(1, missing + 1):
                    ratio = m / (missing + 1)
                    interp_ts = bar["ts"] + expected_interval * m
                    interp_bar = {
                        "ts": interp_ts,
                        "open": bar["open"] + (next_bar["open"] - bar["open"]) * ratio,
                        "high": max(bar["high"], next_bar["high"]),
                        "low": min(bar["low"], next_bar["low"]),
                        "close": bar["close"] + (next_bar["close"] - bar["close"]) * ratio,
                        "volume": 0,  # No volume for interpolated bars
                        "vwap": None,
                        "interpolated": True,
                    }
                    result.append(interp_bar)
                    logger.debug("interpolated_bar", ticker=bar.get("ticker"), ts=interp_ts)

        return result

    def get_expected_interval(self, timeframe: str) -> timedelta:
        """Get expected interval for timeframe."""
        intervals = {
            "1m": timedelta(minutes=1),
            "5m": timedelta(minutes=5),
            "15m": timedelta(minutes=15),
            "1h": timedelta(hours=1),
            "1d": timedelta(days=1),
        }
        return intervals.get(timeframe, timedelta(minutes=1))
