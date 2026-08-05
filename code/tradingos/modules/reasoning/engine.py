"""Reasoning Engine - Combines chart, indicators, memory into trade thesis."""

from datetime import UTC, datetime
from typing import Any

from tradingos.core.logging import get_logger
from tradingos.modules.indicators.interfaces import IndicatorSnapshot
from tradingos.modules.memory.interfaces import HistoricalTrade
from tradingos.modules.reasoning.interfaces import ReasoningEngine, TradeThesis
from tradingos.modules.vision.interfaces import VisionOutput

logger = get_logger(__name__)


class CompositeReasoningEngine(ReasoningEngine):
    """Composite reasoning engine that synthesizes multiple evidence sources."""

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.confidence_threshold = self.config.get("confidence_threshold", 0.65)
        self.min_similar_trades = self.config.get("min_similar_trades", 3)
        self.pattern_weights = self.config.get("pattern_weights", {
            "bull_flag": 1.2,
            "flat_top_breakout": 1.1,
            "vwap_reclaim": 1.15,
            "opening_range_breakout": 1.1,
            "double_bottom": 1.05,
            "cup_and_handle": 1.05,
            "no_pattern": 0.5,
        })
        logger.info("reasoning_engine_initialized", config=self.config)

    async def analyze(
        self,
        candidate,
        indicators: IndicatorSnapshot | None,
        vision: VisionOutput | None,
        similar_trades: list[HistoricalTrade] | None,
    ) -> TradeThesis:
        """Synthesize all evidence into a trade thesis."""

        # Extract components
        ticker = candidate.ticker if hasattr(candidate, "ticker") else "UNKNOWN"
        price = candidate.price if hasattr(candidate, "price") else 0.0

        # 1. Pattern confidence from vision
        pattern = "no_pattern"
        pattern_confidence = 0.0
        if vision and vision.patterns:
            pattern = vision.patterns[0]
            pattern_confidence = vision.confidence

        # 2. Technical score from indicators
        tech_score = self._score_indicators(indicators) if indicators else 0.5

        # 3. Historical win rate from similar trades
        hist_win_rate, hist_count = self._analyze_history(similar_trades)

        # 4. Pattern weight
        pattern_weight = self.pattern_weights.get(pattern, 1.0)

        # Combine scores (weighted average)
        weights = {
            "pattern": 0.40,
            "technical": 0.25,
            "historical": 0.35,
        }

        composite = (
            weights["pattern"] * pattern_confidence * pattern_weight +
            weights["technical"] * tech_score +
            weights["historical"] * hist_win_rate
        )

        # Normalize
        composite = min(max(composite, 0.0), 1.0)

        # Direction
        direction = "long" if composite > 0.5 else "short"

        # Entry, stop, target
        entry = price
        atr = indicators.atr if indicators and indicators.atr else price * 0.02
        stop = entry - atr * 1.5 if direction == "long" else entry + atr * 1.5
        target = entry + atr * 3.0 if direction == "long" else entry - atr * 3.0

        # Position size (Kelly-ish)
        position_size = composite * 0.1  # Max 10% per trade

        # Reasoning summary
        reasoning_parts = []
        if vision and vision.patterns:
            reasoning_parts.append(f"Pattern: {pattern} ({pattern_confidence:.0%})")
        if indicators:
            vwap_str = f"VWAP dist: {indicators.vwap:.2f}" if indicators.vwap else ""
            rvol_str = f", RVol: {indicators.rvol:.1f}x" if indicators.rvol else ""
            ind_str = f"{vwap_str}{rvol_str}" if (vwap_str or rvol_str) else "Indicators available"
            reasoning_parts.append(ind_str)
        if hist_count > 0:
            reasoning_parts.append(
                f"Historical: {hist_count} similar, {hist_win_rate:.0%} win rate"
            )

        indicators_used = (
            list(indicators.indicators.keys())
            if indicators and indicators.indicators
            else []
        )
        thesis = TradeThesis(
            ticker=ticker,
            direction=direction,
            confidence=composite,
            entry_price=entry,
            stop_loss=stop,
            target_price=target,
            position_size_pct=position_size,
            pattern=pattern,
            reasoning="; ".join(reasoning_parts),
            similar_trades_count=hist_count,
            historical_win_rate=hist_win_rate,
            indicators_used=indicators_used,
            timestamp=datetime.now(UTC),
        )

        logger.info(
            "thesis_generated",
            ticker=ticker,
            direction=direction,
            confidence=composite,
            pattern=pattern,
        )

        return thesis

    def _score_indicators(self, indicators: IndicatorSnapshot) -> float:
        """Score technical indicators (0-1)."""
        score = 0.5
        factors = 0

        if indicators.vwap:
            # Price relative to VWAP
            pass  # Would need current price

        if indicators.rvol:
            if indicators.rvol >= 2.0:
                score += 0.15
            elif indicators.rvol >= 1.5:
                score += 0.1
            factors += 1

        if indicators.rsi is not None:
            if indicators.rsi < 30:
                score += 0.1  # Oversold bounce
            elif indicators.rsi < 70:
                score += 0.05
            factors += 1

        if indicators.gap_pct is not None:
            if indicators.gap_pct > 3:
                score += 0.1
            elif indicators.gap_pct > 1:
                score += 0.05
            factors += 1

        if indicators.ema_9 and indicators.ema_20:
            if indicators.ema_9 > indicators.ema_20:
                score += 0.1  # Bullish alignment
            factors += 1

        # Normalize
        if factors > 0:
            score = min(max(score, 0.0), 1.0)

        return score

    def _analyze_history(
        self,
        trades: list[HistoricalTrade] | None,
    ) -> tuple[float, int]:
        """Calculate historical win rate from similar trades."""
        if not trades:
            return 0.5, 0

        wins = sum(1 for t in trades if t.result == "win")
        total = len(trades)

        if total < self.min_similar_trades:
            # Not enough samples, return neutral with penalty
            return 0.5 * (total / self.min_similar_trades), total

        return wins / total, total


def create_reasoning_engine(config: dict[str, Any] | None = None) -> ReasoningEngine:
    """Factory function to create reasoning engine."""
    return CompositeReasoningEngine(config)
