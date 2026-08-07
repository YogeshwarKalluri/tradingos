"""Journal Engine - Trade logging and performance analytics."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import polars as pl

from tradingos.core.logging import get_logger
from tradingos.modules.journal.interfaces import JournalEngine, TradeRecord

logger = get_logger(__name__)


class FileJournalEngine(JournalEngine):
    """File-based trade journal with Polars analytics."""

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.journal_dir = Path(self.config.get("journal_dir", "data/journal"))
        self.journal_dir.mkdir(parents=True, exist_ok=True)
        self.trades_file = self.journal_dir / "trades.parquet"
        self._trades: list[TradeRecord] = []
        self._loaded = False
        logger.info("journal_engine_initialized", dir=str(self.journal_dir))

    async def _load(self) -> None:
        """Load trades from file."""
        if self._loaded:
            return

        if self.trades_file.exists():
            try:
                df = pl.read_parquet(self.trades_file)
                self._trades = [TradeRecord(**row) for row in df.to_dicts()]
                logger.info("journal_loaded", count=len(self._trades))
            except Exception as e:
                logger.warning("journal_load_failed", error=str(e))
                self._trades = []
        self._loaded = True

    async def _save(self) -> None:
        """Save trades to file."""
        if not self._trades:
            return

        df = pl.DataFrame([t.__dict__ for t in self._trades])
        df.write_parquet(self.trades_file)
        logger.debug("journal_saved", count=len(self._trades))

    async def record_trade(self, trade: TradeRecord) -> None:
        """Record a completed trade."""
        await self._load()
        self._trades.append(trade)
        await self._save()
        logger.info("trade_recorded", trade_id=trade.trade_id, ticker=trade.ticker, pnl=trade.pnl)

    async def get_trades(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        ticker: str | None = None,
    ) -> list[TradeRecord]:
        """Get filtered trades."""
        await self._load()

        trades = self._trades

        if start_date:
            trades = [t for t in trades if t.entry_time >= start_date]
        if end_date:
            trades = [t for t in trades if t.entry_time <= end_date]
        if ticker:
            trades = [t for t in trades if t.ticker == ticker]

        return trades

    async def get_performance_stats(self) -> dict[str, Any]:
        """Calculate performance statistics."""
        await self._load()

        if not self._trades:
            return {
                "total_trades": 0,
                "win_rate": 0.0,
                "avg_win": 0.0,
                "avg_loss": 0.0,
                "profit_factor": 0.0,
                "total_pnl": 0.0,
                "max_drawdown": 0.0,
                "sharpe_ratio": 0.0,
            }

        df = pl.DataFrame([t.__dict__ for t in self._trades])

        # Basic stats
        total_trades = len(df)
        wins = df.filter(pl.col("result") == "win")
        losses = df.filter(pl.col("result") == "loss")

        win_rate = len(wins) / total_trades if total_trades > 0 else 0.0
        avg_win = wins["pnl"].mean() if len(wins) > 0 else 0.0
        avg_loss = losses["pnl"].mean() if len(losses) > 0 else 0.0

        total_pnl = df["pnl"].sum()
        gross_profit = wins["pnl"].sum() if len(wins) > 0 else 0.0
        gross_loss = abs(losses["pnl"].sum()) if len(losses) > 0 else 0.0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

        # Daily P&L for Sharpe and drawdown
        df = df.with_columns([
            pl.col("entry_time").str.to_datetime().dt.date().alias("date")
        ])
        daily = df.group_by("date").agg(pl.col("pnl").sum().alias("daily_pnl"))
        daily_pnl = daily["daily_pnl"].to_list()

        # Max drawdown
        running = 0.0
        peak = 0.0
        max_dd = 0.0
        for pnl in daily_pnl:
            running += pnl
            peak = max(peak, running)
            dd = peak - running
            max_dd = max(max_dd, dd)

        # Sharpe ratio (simplified, assuming risk-free = 0)
        if len(daily_pnl) > 1:
            mean_daily = sum(daily_pnl) / len(daily_pnl)
            std_daily = (sum((x - mean_daily) ** 2 for x in daily_pnl) / len(daily_pnl)) ** 0.5
            sharpe = (mean_daily / std_daily * (252 ** 0.5)) if std_daily > 0 else 0.0
        else:
            sharpe = 0.0

        avg_hold = df["hold_time_minutes"].mean()
        if avg_hold is None:
            avg_hold = 0
        return {
            "total_trades": total_trades,
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": win_rate,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "profit_factor": profit_factor,
            "total_pnl": total_pnl,
            "gross_profit": gross_profit,
            "gross_loss": gross_loss,
            "max_drawdown": max_dd,
            "sharpe_ratio": sharpe,
            "avg_hold_time": avg_hold,
        }

    async def get_daily_pnl(self, days: int = 30) -> list[dict[str, Any]]:
        """Get daily P&L for the last N days."""
        await self._load()

        if not self._trades:
            return []

        df = pl.DataFrame([t.__dict__ for t in self._trades])
        df = df.with_columns([
            pl.col("entry_time").str.to_datetime().dt.date().alias("date")
        ])

        # Filter to last N days
        cutoff = datetime.now(UTC).date()
        from datetime import timedelta
        cutoff = cutoff - timedelta(days=days)
        df = df.filter(pl.col("date") >= cutoff)

        daily = df.group_by("date").agg([
            pl.col("pnl").sum().alias("pnl"),
            pl.col("trade_id").count().alias("trades"),
            pl.col("commission").sum().alias("commission"),
        ]).sort("date")

        return daily.to_dicts()


def create_journal_engine(config: dict[str, Any] | None = None) -> JournalEngine:
    """Factory function to create journal engine."""
    return FileJournalEngine(config)
