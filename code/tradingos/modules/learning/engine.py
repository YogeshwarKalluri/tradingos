"""Learning Engine - After-hours model training pipeline."""

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
from sklearn.model_selection import train_test_split

from tradingos.core.logging import get_logger
from tradingos.modules.learning.interfaces import (
    LearningEngine,
    TrainingConfig,
    TrainingResult,
)

logger = get_logger(__name__)


class MLLearningEngine(LearningEngine):
    """ML model training engine for after-hours execution."""

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.models_dir = Path(self.config.get("models_dir", "models"))
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.training_history: list[TrainingResult] = []
        self._load_history()
        logger.info("learning_engine_initialized", models_dir=str(self.models_dir))

    def _load_history(self) -> None:
        """Load training history from disk."""
        history_file = self.models_dir / "training_history.json"
        if history_file.exists():
            try:
                with open(history_file) as f:
                    data = json.load(f)
                self.training_history = [TrainingResult(**r) for r in data]
                logger.info("training_history_loaded", count=len(self.training_history))
            except Exception as e:
                logger.warning("training_history_load_failed", error=str(e))
                self.training_history = []

    def _save_history(self) -> None:
        """Save training history to disk."""
        history_file = self.models_dir / "training_history.json"
        with open(history_file, "w") as f:
            json.dump([r.__dict__ for r in self.training_history], f, default=str)

    async def _prepare_training_data(self, config: TrainingConfig) -> tuple[np.ndarray, np.ndarray]:
        """Prepare training data from journal and market data."""
        # In production, this would query DuckDB for historical trades + market features
        # For now, generate synthetic data for demonstration

        n_samples = 10000
        n_features = len(config.feature_cols)

        # Generate synthetic features
        X = np.random.randn(n_samples, n_features)

        # Generate labels with some signal
        signal = X[:, 0] * 0.3 + X[:, 1] * 0.2
        prob = 1 / (1 + np.exp(-signal))
        y = (np.random.rand(n_samples) < prob).astype(int)

        return X, y

    async def train(self, config: TrainingConfig) -> TrainingResult:
        """Train a model asynchronously."""
        run_id = str(uuid.uuid4())
        started_at = datetime.now(UTC).isoformat()

        result = TrainingResult(
            run_id=run_id,
            config=config,
            metrics={},
            model_path="",
            started_at=started_at,
            status="running",
        )

        self.training_history.append(result)
        self._save_history()

        logger.info("training_started", run_id=run_id, model=config.model_name)

        try:
            # Prepare data
            X, y = await self._prepare_training_data(config)

            # Split
            X_train, X_val, y_train, y_val = train_test_split(
                X, y, test_size=config.validation_split, random_state=42, stratify=y
            )

            # Train model based on type
            if config.model_type == "gradient_boosting":
                model = GradientBoostingClassifier(
                    n_estimators=config.hyperparams.get("n_estimators", 100),
                    learning_rate=config.hyperparams.get("learning_rate", 0.1),
                    max_depth=config.hyperparams.get("max_depth", 3),
                    random_state=42,
                )
            elif config.model_type == "xgboost":
                try:
                    import xgboost as xgb
                    model = xgb.XGBClassifier(
                        n_estimators=config.hyperparams.get("n_estimators", 100),
                        learning_rate=config.hyperparams.get("learning_rate", 0.1),
                        max_depth=config.hyperparams.get("max_depth", 3),
                        random_state=42,
                        eval_metric="logloss",
                    )
                except ImportError:
                    logger.warning("xgboost_not_available_using_gbdt")
                    model = GradientBoostingClassifier(random_state=42)
            else:
                model = GradientBoostingClassifier(random_state=42)

            # Train
            model.fit(X_train, y_train)

            # Evaluate
            y_pred = model.predict(X_val)
            y_proba = model.predict_proba(X_val)[:, 1]

            metrics = {
                "accuracy": float(accuracy_score(y_val, y_pred)),
                "f1_score": float(f1_score(y_val, y_pred)),
                "roc_auc": float(roc_auc_score(y_val, y_proba)),
                "train_samples": len(X_train),
                "val_samples": len(X_val),
            }

            # Save model
            model_path = self.models_dir / f"{config.model_name}_{run_id[:8]}.joblib"
            joblib.dump(model, model_path)

            # Update result
            result.metrics = metrics
            result.model_path = str(model_path)
            result.completed_at = datetime.now(UTC).isoformat()
            result.status = "completed"

            self._save_history()

            logger.info(
                "training_completed",
                run_id=run_id,
                metrics=metrics,
                model_path=str(model_path),
            )

        except Exception as e:
            result.status = "failed"
            result.completed_at = datetime.now(UTC).isoformat()
            result.metrics = {"error": str(e)}
            self._save_history()
            logger.error("training_failed", run_id=run_id, error=str(e))
            raise

        return result

    async def evaluate(self, model_path: str, test_data) -> dict[str, float]:
        """Evaluate a trained model on test data."""
        model = joblib.load(model_path)
        X_test, y_test = test_data

        y_pred = model.predict(X_test)
        y_proba = model.predict_proba(X_test)[:, 1]

        return {
            "accuracy": float(accuracy_score(y_test, y_pred)),
            "f1_score": float(f1_score(y_test, y_pred)),
            "roc_auc": float(roc_auc_score(y_test, y_proba)),
        }

    async def get_training_history(self) -> list[TrainingResult]:
        """Get training history."""
        return self.training_history.copy()

    async def schedule_training(
        self,
        config: TrainingConfig,
        cron: str = "0 2 * * 1-5",
    ) -> str:
        """Schedule recurring training (returns job ID)."""
        # In production, this would integrate with cron/scheduler
        # For now, just log the schedule
        job_id = f"train_{config.model_name}_{uuid.uuid4().hex[:8]}"
        logger.info("training_scheduled", job_id=job_id, cron=cron, config=config.__dict__)
        return job_id


def create_learning_engine(config: dict[str, Any] | None = None) -> LearningEngine:
    """Factory function to create learning engine."""
    return MLLearningEngine(config)
