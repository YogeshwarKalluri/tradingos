"""
Qdrant Vector Database Connection for TradingOS
Vector search for trade embeddings and chart patterns
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from qdrant_client import QdrantClient, models
from qdrant_client.http.models import Distance, VectorParams, HnswConfigDiff, QuantizationConfig, ScalarQuantization

from core.config import get_settings


@dataclass(slots=True)
class QdrantConfig:
    """Qdrant connection configuration."""
    path: str
    port: int = 6333
    prefer_grpc: bool = False
    timeout: float = 30.0


class QdrantManager:
    """
    Qdrant vector database manager for trading embeddings.
    
    Collections:
    - trade_embeddings: Historical trade vectors for similarity search
    - pattern_embeddings: Chart pattern vectors for visual similarity
    - knowledge_embeddings: General trading knowledge (video lessons, etc.)
    """
    
    def __init__(self, config: QdrantConfig):
        self._config = config
        self._client: Optional[QdrantClient] = None
        self._initialized = False
    
    @property
    def client(self) -> QdrantClient:
        """Get or create Qdrant client."""
        if self._client is None:
            self._client = QdrantClient(
                path=self._config.path,
                port=self._config.port,
                prefer_grpc=self._config.prefer_grpc,
                timeout=self._config.timeout,
            )
        return self._client
    
    def initialize_collections(self) -> None:
        """Create all required collections."""
        if self._initialized:
            return
        
        # Trade embeddings collection
        self._create_trade_embeddings_collection()
        
        # Pattern embeddings collection
        self._create_pattern_embeddings_collection()
        
        # Knowledge embeddings collection
        self._create_knowledge_embeddings_collection()
        
        self._initialized = True
    
    def _create_trade_embeddings_collection(self) -> None:
        """Create collection for trade embeddings."""
        collection_name = "trade_embeddings"
        
        if self.client.collection_exists(collection_name):
            return
        
        self.client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=1024,  # BGE-large / E5-large
                distance=Distance.COSINE,
                hnsw_config=HnswConfigDiff(
                    m=16,
                    ef_construct=200,
                ),
                quantization_config=ScalarQuantization(
                    type="scalar",
                    quantile=0.99,
                    always_ram=True,
                ),
            ),
        )
        
        # Create payload indexes for filtering
        self.client.create_payload_index(
            collection_name=collection_name,
            field_name="symbol",
            field_schema=models.PayloadSchemaType.KEYWORD,
        )
        
        self.client.create_payload_index(
            collection_name=collection_name,
            field_name="setup_type",
            field_schema=models.PayloadSchemaType.KEYWORD,
        )
        
        self.client.create_payload_index(
            collection_name=collection_name,
            field_name="entry_time",
            field_schema=models.PayloadSchemaType.INTEGER,
        )
        
        self.client.create_payload_index(
            collection_name=collection_name,
            field_name="pnl",
            field_schema=models.PayloadSchemaType.FLOAT,
        )
        
        self.client.create_payload_index(
            collection_name=collection_name,
            field_name="pattern_confidence",
            field_schema=models.PayloadSchemaType.FLOAT,
        )
    
    def _create_pattern_embeddings_collection(self) -> None:
        """Create collection for chart pattern embeddings."""
        collection_name = "pattern_embeddings"
        
        if self.client.collection_exists(collection_name):
            return
        
        self.client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=512,  # Pattern embedding size
                distance=Distance.COSINE,
                hnsw_config=HnswConfigDiff(
                    m=16,
                    ef_construct=200,
                ),
                quantization_config=models.BinaryQuantization(
                    binary=models.BinaryQuantizationConfig(
                        always_ram=True,
                    ),
                ),
            ),
        )
        
        # Payload indexes
        self.client.create_payload_index(
            collection_name=collection_name,
            field_name="symbol",
            field_schema=models.PayloadSchemaType.KEYWORD,
        )
        
        self.client.create_payload_index(
            collection_name=collection_name,
            field_name="pattern_type",
            field_schema=models.PayloadSchemaType.KEYWORD,
        )
    
    def _create_knowledge_embeddings_collection(self) -> None:
        """Create collection for general trading knowledge embeddings."""
        collection_name = "knowledge_embeddings"
        
        if self.client.collection_exists(collection_name):
            return
        
        self.client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=1024,
                distance=Distance.COSINE,
                hnsw_config=HnswConfigDiff(
                    m=16,
                    ef_construct=200,
                ),
                quantization_config=ScalarQuantization(
                    type="scalar",
                    quantile=0.99,
                    always_ram=True,
                ),
            ),
        )
        
        self.client.create_payload_index(
            collection_name=collection_name,
            field_name="source_type",
            field_schema=models.PayloadSchemaType.KEYWORD,
        )
        
        self.client.create_payload_index(
            collection_name=collection_name,
            field_name="video_id",
            field_schema=models.PayloadSchemaType.KEYWORD,
        )
        
        self.client.create_payload_index(
            collection_name=collection_name,
            field_name="timestamp",
            field_schema=models.PayloadSchemaType.INTEGER,
        )
    
    # ==================== Trade Embeddings ====================
    
    def upsert_trade_embedding(
        self,
        trade_id: str,
        vector: List[float],
        payload: Dict[str, Any]
    ) -> None:
        """Insert or update a trade embedding."""
        self.client.upsert(
            collection_name="trade_embeddings",
            points=[
                models.PointStruct(
                    id=trade_id,
                    vector=vector,
                    payload=payload,
                )
            ],
        )
    
    def search_similar_trades(
        self,
        vector: List[float],
        top_k: int = 20,
        symbol: Optional[str] = None,
        setup_type: Optional[str] = None,
        min_confidence: float = 0.0,
        min_pnl: Optional[float] = None,
    ) -> List[Tuple[float, Dict[str, Any]]]:
        """Search for similar trades with optional filters."""
        filter_conditions = []
        
        if symbol:
            filter_conditions.append(
                models.FieldCondition(
                    key="symbol",
                    match=models.MatchValue(value=symbol),
                )
            )
        
        if setup_type:
            filter_conditions.append(
                models.FieldCondition(
                    key="setup_type",
                    match=models.MatchValue(value=setup_type),
                )
            )
        
        if min_confidence > 0:
            filter_conditions.append(
                models.FieldCondition(
                    key="pattern_confidence",
                    range=models.Range(gte=min_confidence),
                )
            )
        
        if min_pnl is not None:
            filter_conditions.append(
                models.FieldCondition(
                    key="pnl",
                    range=models.Range(gte=min_pnl),
                )
            )
        
        query_filter = models.Filter(must=filter_conditions) if filter_conditions else None
        
        results = self.client.search(
            collection_name="trade_embeddings",
            query_vector=vector,
            query_filter=query_filter,
            limit=top_k,
            with_payload=True,
            with_vectors=False,
        )
        
        return [(hit.score, hit.payload) for hit in results]
    
    def delete_trade_embedding(self, trade_id: str) -> None:
        """Delete a trade embedding."""
        self.client.delete(
            collection_name="trade_embeddings",
            points_selector=models.PointIdsList(points=[trade_id]),
        )
    
    # ==================== Pattern Embeddings ====================
    
    def upsert_pattern_embedding(
        self,
        pattern_id: str,
        vector: List[float],
        payload: Dict[str, Any]
    ) -> None:
        """Insert or update a pattern embedding."""
        self.client.upsert(
            collection_name="pattern_embeddings",
            points=[
                models.PointStruct(
                    id=pattern_id,
                    vector=vector,
                    payload=payload,
                )
            ],
        )
    
    def search_similar_patterns(
        self,
        vector: List[float],
        top_k: int = 10,
        symbol: Optional[str] = None,
        pattern_type: Optional[str] = None,
    ) -> List[Tuple[float, Dict[str, Any]]]:
        """Search for similar chart patterns."""
        filter_conditions = []
        
        if symbol:
            filter_conditions.append(
                models.FieldCondition(
                    key="symbol",
                    match=models.MatchValue(value=symbol),
                )
            )
        
        if pattern_type:
            filter_conditions.append(
                models.FieldCondition(
                    key="pattern_type",
                    match=models.MatchValue(value=pattern_type),
                )
            )
        
        query_filter = models.Filter(must=filter_conditions) if filter_conditions else None
        
        results = self.client.search(
            collection_name="pattern_embeddings",
            query_vector=vector,
            query_filter=query_filter,
            limit=top_k,
            with_payload=True,
            with_vectors=False,
        )
        
        return [(hit.score, hit.payload) for hit in results]
    
    # ==================== Knowledge Embeddings ====================
    
    def upsert_knowledge_embedding(
        self,
        knowledge_id: str,
        vector: List[float],
        payload: Dict[str, Any]
    ) -> None:
        """Insert or update a knowledge embedding."""
        self.client.upsert(
            collection_name="knowledge_embeddings",
            points=[
                models.PointStruct(
                    id=knowledge_id,
                    vector=vector,
                    payload=payload,
                )
            ],
        )
    
    def search_knowledge(
        self,
        vector: List[float],
        top_k: int = 10,
        source_type: Optional[str] = None,
        video_id: Optional[str] = None,
    ) -> List[Tuple[float, Dict[str, Any]]]:
        """Search for similar knowledge entries."""
        filter_conditions = []
        
        if source_type:
            filter_conditions.append(
                models.FieldCondition(
                    key="source_type",
                    match=models.MatchValue(value=source_type),
                )
            )
        
        if video_id:
            filter_conditions.append(
                models.FieldCondition(
                    key="video_id",
                    match=models.MatchValue(value=video_id),
                )
            )
        
        query_filter = models.Filter(must=filter_conditions) if filter_conditions else None
        
        results = self.client.search(
            collection_name="knowledge_embeddings",
            query_vector=vector,
            query_filter=query_filter,
            limit=top_k,
            with_payload=True,
            with_vectors=False,
        )
        
        return [(hit.score, hit.payload) for hit in results]
    
    def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """Get collection statistics."""
        info = self.client.get_collection(collection_name)
        return {
            "name": collection_name,
            "vectors_count": info.vectors_count,
            "points_count": info.points_count,
            "segments_count": info.segments_count,
            "status": info.status,
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get overall statistics."""
        collections = self.client.get_collections().collections
        return {
            "collections": len(collections),
            "collection_names": [c.name for c in collections],
        }
    
    def close(self) -> None:
        """Close the client connection."""
        if self._client:
            self._client.close()
            self._client = None


# Global manager instance
_qdrant_manager: Optional[QdrantManager] = None


def get_qdrant_manager() -> QdrantManager:
    """Get or create the global Qdrant manager."""
    global _qdrant_manager
    if _qdrant_manager is None:
        settings = get_settings()
        config = QdrantConfig(
            path=settings.databases.qdrant_path,
            port=settings.databases.qdrant_port,
            prefer_grpc=settings.databases.qdrant_prefer_grpc,
        )
        _qdrant_manager = QdrantManager(config)
        _qdrant_manager.initialize_collections()
    return _qdrant_manager


def set_qdrant_manager(manager: QdrantManager) -> None:
    """Set the global Qdrant manager (for testing)."""
    global _qdrant_manager
    _qdrant_manager = manager


def close_qdrant_manager() -> None:
    """Close the global Qdrant manager."""
    global _qdrant_manager
    if _qdrant_manager:
        _qdrant_manager.close()
        _qdrant_manager = None