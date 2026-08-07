"""Learning Engine interfaces - After-hours model training pipeline."""

from dataclasses import dataclass
from typing import Any


@dataclass
class TrainingSample:
    """Single training sample from historical data."""
    ticker: str
    timestamp: str
    features: dict[str, float]
    label: float  # 1 for win, 0 for loss, 0.5 for breakeven
    horizon_minutes: int
    market_regime: str | None = None


@dataclass
class TrainingConfig:
    """Configuration for training run."""
    model_name: str
    model_type: str  # xgboost, lightgbm, neural_net
    feature_cols: list[str]
    label_col: str = "label"
    train_start: str | None = None
    train_end: str | None = None
    validation_split: float = 0.2
    hyperparams: dict[str, Any] = None

    def __post_init__(self):
        if self.hyperparams is None:
            self.hyperparams = {}


@dataclass
class TrainingResult:
    """Result of a training run."""
    run_id: str
    config: TrainingConfig
    metrics: dict[str, float]
    model_path: str
    started_at: str
    completed_at: str | None = None
    status: str = "running"  # running, completed, failed


class LearningEngine:
    """Base class for model training pipeline."""

    async def train(self, config: TrainingConfig) -> TrainingResult:
        raise NotImplementedError

    async def evaluate(self, model_path: str, test_data) -> dict[str, float]:
        raise NotImplementedError

    async def get_training_history(self) -> list[TrainingResult]:
        raise NotImplementedError

    async def schedule_training(
        self,
        config: TrainingConfig,
        cron: str = "0 2 * * 1-5",  # 2 AM weekdays
    ) -> str:
        raise NotImplementedError
