"""Memory Engine - Vector similarity search using Qdrant embedded."""

import uuid
from datetime import datetime
from typing import Any

import numpy as np
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from tradingos.core.logging import get_logger
from tradingos.modules.memory.interfaces import HistoricalTrade, MemoryEngine

logger = get_logger(__name__)


COLLECTION_NAME = "historical_trades"
VECTOR_SIZE = 384  # Default embedding size


class QdrantMemoryEngine(MemoryEngine):
    """Qdrant-based vector memory for historical trade similarity search."""

    def __init__(
        self,
        path: str = "data/qdrant",
        vector_size: int = VECTOR_SIZE,
        collection_name: str = COLLECTION_NAME,
    ):
        self.path = path
        self.vector_size = vector_size
        self.collection_name = collection_name
        self.client: AsyncQdrantClient | None = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize Qdrant client and collection."""
        if self._initialized:
            return

        self.client = AsyncQdrantClient(path=self.path)

        # Create collection if not exists
        collections = await self.client.get_collections()
        if self.collection_name not in [c.name for c in collections.collections]:
            await self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size,
                    distance=Distance.COSINE,
                ),
            )
            logger.info("qdrant_collection_created", name=self.collection_name)

        self._initialized = True
        logger.info("memory_engine_initialized", path=self.path)

    async def add_trade(self, trade: HistoricalTrade) -> str:
        """Add a historical trade to the vector store."""
        await self.initialize()

        # Generate embedding from trade features
        embedding = self._trade_to_embedding(trade)

        point_id = str(uuid.uuid4())
        point = PointStruct(
            id=point_id,
            vector=embedding.tolist(),
            payload={
                "ticker": trade.ticker,
                "entry_price": trade.entry_price,
                "exit_price": trade.exit_price,
                "side": trade.side,
                "pattern": trade.pattern,
                "setup_quality": trade.setup_quality,
                "hold_time_minutes": trade.hold_time_minutes,
                "pnl_pct": trade.pnl_pct,
                "result": trade.result,
                "entry_time": (
                    trade.entry_time.isoformat()
                    if isinstance(trade.entry_time, datetime)
                    else trade.entry_time
                ),
                "exit_time": (
                    trade.exit_time.isoformat()
                    if isinstance(trade.exit_time, datetime)
                    else trade.exit_time
                ),
                "indicators": trade.indicators,
                "chart_embedding": trade.chart_embedding,
            },
        )

        await self.client.upsert(
            collection_name=self.collection_name,
            points=[point],
        )

        logger.debug("trade_added", trade_id=point_id, ticker=trade.ticker)
        return point_id

    async def search_similar(
        self,
        query_embedding: np.ndarray,
        limit: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[HistoricalTrade]:
        """Search for similar historical trades."""
        await self.initialize()

        # Build filter
        filter_obj = None
        if filters:
            conditions = []
            for key, value in filters.items():
                conditions.append(
                    FieldCondition(key=key, match=MatchValue(value=value))
                )
            if conditions:
                filter_obj = Filter(must=conditions)

        # Search
        results = await self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding.tolist(),
            limit=limit,
            query_filter=filter_obj,
            with_payload=True,
        )

        # Convert to HistoricalTrade objects
        trades = []
        for hit in results:
            payload = hit.payload
            trade = HistoricalTrade(
                id=str(hit.id),
                ticker=payload.get("ticker", ""),
                entry_price=payload.get("entry_price", 0.0),
                exit_price=payload.get("exit_price", 0.0),
                side=payload.get("side", ""),
                pattern=payload.get("pattern"),
                setup_quality=payload.get("setup_quality"),
                hold_time_minutes=payload.get("hold_time_minutes"),
                pnl_pct=payload.get("pnl_pct", 0.0),
                result=payload.get("result", ""),
                entry_time=payload.get("entry_time", ""),
                exit_time=payload.get("exit_time", ""),
                indicators=payload.get("indicators", {}),
                chart_embedding=payload.get("chart_embedding"),
            )
            trades.append(trade)

        logger.debug("similar_trades_found", count=len(trades))
        return trades

    async def get_stats(self) -> dict[str, Any]:
        """Get memory engine statistics."""
        await self.initialize()

        info = await self.client.get_collection(self.collection_name)

        return {
            "collection": self.collection_name,
            "vectors_count": info.vectors_count,
            "points_count": info.points_count,
            "vector_size": self.vector_size,
            "status": info.status,
        }

    def _trade_to_embedding(self, trade: HistoricalTrade) -> np.ndarray:
        """Convert trade to embedding vector.

        In production, this would use a trained embedding model.
        For now, create a feature vector from trade attributes.
        """
        features = []

        # Numerical features
        features.append(trade.entry_price)
        features.append(trade.exit_price)
        features.append(trade.pnl_pct)
        features.append(trade.hold_time_minutes or 0)
        features.append(trade.setup_quality or 0.5)

        # One-hot encoded features
        features.append(1.0 if trade.side == "long" else 0.0)
        features.append(1.0 if trade.side == "short" else 0.0)

        # Pattern encoding (simple hash-based)
        pattern_hash = hash(trade.pattern or "") % 1000 / 1000.0
        features.append(pattern_hash)

        # Result encoding
        result_map = {"win": 1.0, "loss": 0.0, "breakeven": 0.5}
        features.append(result_map.get(trade.result, 0.5))

        # Indicators
        if trade.indicators:
            features.append(trade.indicators.get("vwap_dist", 0))
            features.append(trade.indicators.get("rvol", 1))
            features.append(trade.indicators.get("rsi", 50))
            features.append(trade.indicators.get("atr_pct", 0))
        else:
            features.extend([0, 1, 50, 0])

        # Pad or truncate to vector_size
        embedding = np.array(features, dtype=np.float32)
        if len(embedding) < self.vector_size:
            embedding = np.pad(embedding, (0, self.vector_size - len(embedding)))
        else:
            embedding = embedding[:self.vector_size]

        # Normalize
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm

        return embedding

    async def close(self) -> None:
        """Close the Qdrant client."""
        if self.client:
            await self.client.close()
            self.client = None
            self._initialized = False


class MockMemoryEngine(MemoryEngine):
    """Mock memory engine for development/testing."""

    def __init__(self, **kwargs):
        self.trades: list[HistoricalTrade] = []
        logger.info("mock_memory_engine_initialized")

    async def initialize(self) -> None:
        pass

    async def add_trade(self, trade: HistoricalTrade) -> str:
        trade.id = str(uuid.uuid4())
        self.trades.append(trade)
        return trade.id

    async def search_similar(
        self,
        query_embedding: np.ndarray,
        limit: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[HistoricalTrade]:
        # Return random subset for testing
        import random
        return random.sample(self.trades, min(limit, len(self.trades)))

    async def get_stats(self) -> dict[str, Any]:
        return {
            "collection": "mock",
            "trades_count": len(self.trades),
        }

    async def close(self) -> None:
        pass


def create_memory_engine(use_mock: bool = True, **kwargs) -> MemoryEngine:
    """Factory function to create memory engine."""
    if use_mock:
        return MockMemoryEngine(**kwargs)
    return QdrantMemoryEngine(**kwargs)
