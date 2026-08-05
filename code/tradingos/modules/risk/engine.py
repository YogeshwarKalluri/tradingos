"""Risk Engine - Position sizing, stop loss, daily loss limits."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from tradingos.core.logging import get_logger
from tradingos.modules.reasoning.interfaces import TradeThesis
from tradingos.modules.risk.interfaces import RiskDecisionResult, RiskEngine

logger = get_logger(__name__)


@dataclass
class RiskLimits:
    """Risk limits configuration."""
    max_position_pct: float = 0.10      # Max 10% per position
    max_daily_loss_pct: float = 0.02    # Max 2% daily loss
    max_drawdown_pct: float = 0.05      # Max 5% drawdown
    max_open_positions: int = 5         # Max concurrent positions
    max_sector_exposure_pct: float = 0.20  # Max 20% per sector
    min_risk_reward: float = 1.5        # Min 1.5:1 risk/reward
    max_correlation: float = 0.7        # Max correlation between positions


class RiskEngineImpl(RiskEngine):
    """Risk management engine with pre-trade checks and position limits."""

    def __init__(
        self,
        config: dict[str, Any] | None = None,
        account_equity: float = 100_000.0,
    ):
        self.config = config or {}
        self.limits = RiskLimits(**self.config.get("limits", {}))
        self.account_equity = account_equity
        self.daily_pnl = 0.0
        self.open_positions: dict[str, dict] = {}
        self.trade_history: list[dict] = []
        self.peak_equity = account_equity
        logger.info("risk_engine_initialized", limits=self.limits.__dict__)

    async def evaluate(self, thesis: TradeThesis) -> RiskDecisionResult:
        """Evaluate a trade thesis against risk rules."""

        # Check if we have capacity for new position
        if len(self.open_positions) >= self.limits.max_open_positions:
            return RiskDecisionResult(
                approved=False,
                reason=f"Max open positions reached ({self.limits.max_open_positions})",
                risk_score=1.0,
            )

        # Check daily loss limit
        if self.daily_pnl <= -self.account_equity * self.limits.max_daily_loss_pct:
            return RiskDecisionResult(
                approved=False,
                reason=f"Daily loss limit exceeded ({self.daily_pnl:.2f})",
                risk_score=1.0,
            )

        # Check max drawdown
        current_drawdown = (self.peak_equity - self.account_equity) / self.peak_equity
        if current_drawdown >= self.limits.max_drawdown_pct:
            return RiskDecisionResult(
                approved=False,
                reason=f"Max drawdown exceeded ({current_drawdown:.1%})",
                risk_score=1.0,
            )

        # Check position size
        position_value = thesis.entry_price * thesis.position_size_pct * self.account_equity
        max_position_value = self.account_equity * self.limits.max_position_pct
        if position_value > max_position_value:
            return RiskDecisionResult(
                approved=False,
                reason=(
                    f"Position size exceeds limit "
                    f"({position_value:.0f} > {max_position_value:.0f})"
                ),
                risk_score=0.8,
            )

        # Check risk/reward ratio
        risk = abs(thesis.entry_price - thesis.stop_loss)
        reward = abs(thesis.target_price - thesis.entry_price)
        if risk > 0:
            rr = reward / risk
            if rr < self.limits.min_risk_reward:
                return RiskDecisionResult(
                    approved=False,
                    reason=f"Risk/reward too low ({rr:.2f} < {self.limits.min_risk_reward})",
                    risk_score=0.7,
                )

        # Check confidence threshold
        if thesis.confidence < 0.55:
            return RiskDecisionResult(
                approved=False,
                reason=f"Confidence too low ({thesis.confidence:.0%})",
                risk_score=0.6,
            )

        # Check correlation with existing positions
        correlation_risk = self._check_correlation(thesis.ticker)
        if correlation_risk:
            return RiskDecisionResult(
                approved=False,
                reason=correlation_risk,
                risk_score=0.7,
            )

        # All checks passed - approve with position sizing
        approved_size = self._calculate_position_size(thesis)

        return RiskDecisionResult(
            approved=True,
            reason="Risk checks passed",
            risk_score=1.0 - thesis.confidence,
            adjusted_size_pct=approved_size,
            stop_loss=thesis.stop_loss,
            target_price=thesis.target_price,
            max_loss_usd=(
                approved_size
                * self.account_equity
                * abs(thesis.entry_price - thesis.stop_loss)
                / thesis.entry_price
            ),
        )

    def _check_correlation(self, ticker: str) -> str | None:
        """Check correlation with existing positions."""
        # Simplified: check sector overlap
        # In production, would use actual correlation matrix
        sector_map = {
            "AAPL": "tech", "MSFT": "tech", "NVDA": "tech", "GOOGL": "tech",
            "TSLA": "auto", "F": "auto", "GM": "auto",
            "JPM": "finance", "BAC": "finance", "GS": "finance",
            "XOM": "energy", "CVX": "energy",
        }
        ticker_sector = sector_map.get(ticker, "other")

        sector_exposure = sum(
            1 for pos in self.open_positions.values()
            if sector_map.get(pos.get("ticker", ""), "other") == ticker_sector
        )

        if sector_exposure >= 2:
            return f"Sector exposure limit reached for {ticker_sector}"

        return None

    def _calculate_position_size(self, thesis: TradeThesis) -> float:
        """Calculate Kelly-adjusted position size."""
        # Kelly fraction: f = (bp - q) / b
        # where b = reward/risk, p = win probability, q = 1-p
        risk = abs(thesis.entry_price - thesis.stop_loss)
        reward = abs(thesis.target_price - thesis.entry_price)

        if risk == 0:
            return 0.0

        b = reward / risk
        p = thesis.confidence  # Use confidence as win probability proxy
        q = 1 - p

        kelly = (b * p - q) / b
        kelly = max(0, min(kelly, 1))  # Clamp to [0, 1]

        # Apply safety factor (half-Kelly)
        size = kelly * 0.5

        # Cap at max position limit
        size = min(size, self.limits.max_position_pct)

        return size

    async def on_fill(self, fill_event) -> None:
        """Update state on order fill."""
        ticker = fill_event.ticker
        qty = fill_event.qty
        price = fill_event.price
        side = fill_event.side

        if side == "buy":
            if ticker not in self.open_positions:
                self.open_positions[ticker] = {
                    "ticker": ticker,
                    "qty": 0,
                    "avg_price": 0.0,
                    "side": "long",
                }
            pos = self.open_positions[ticker]
            total_cost = pos["qty"] * pos["avg_price"] + qty * price
            pos["qty"] += qty
            pos["avg_price"] = total_cost / pos["qty"]
        else:  # sell
            if ticker in self.open_positions:
                pos = self.open_positions[ticker]
                pos["qty"] -= qty
                if pos["qty"] <= 0:
                    del self.open_positions[ticker]

    async def on_position_closed(self, ticker: str, pnl: float) -> None:
        """Update state when position is closed."""
        self.daily_pnl += pnl
        self.account_equity += pnl
        self.peak_equity = max(self.peak_equity, self.account_equity)
        self.trade_history.append({
            "ticker": ticker,
            "pnl": pnl,
            "timestamp": datetime.now(UTC).isoformat(),
        })

    async def reset_daily(self) -> None:
        """Reset daily counters (call at market open)."""
        self.daily_pnl = 0.0

    def get_risk_metrics(self) -> dict[str, Any]:
        """Get current risk metrics."""
        return {
            "account_equity": self.account_equity,
            "daily_pnl": self.daily_pnl,
            "daily_pnl_pct": self.daily_pnl / self.account_equity if self.account_equity else 0,
            "open_positions": len(self.open_positions),
            "max_positions": self.limits.max_open_positions,
            "current_drawdown_pct": (self.peak_equity - self.account_equity) / self.peak_equity,
            "max_drawdown_pct": self.limits.max_drawdown_pct,
        }


def create_risk_engine(
    config: dict[str, Any] | None = None,
    account_equity: float = 100_000.0,
) -> RiskEngine:
    """Factory function to create risk engine."""
    return RiskEngineImpl(config, account_equity)
