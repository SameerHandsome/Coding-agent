# app/rag/hybrid_search.py
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    VectorParams,
    Distance,
    SparseVectorParams,
    SparseIndexParams,
    PointStruct,
    SparseVector,
    Prefetch,
    FusionQuery,
    Fusion,
)
from app.core.config import settings
from app.rag.embedder import embedding_model
from typing import List, Dict
import uuid, logging

logger = logging.getLogger(__name__)


class HybridSearcher:
    def __init__(self):
        self.client = AsyncQdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
            timeout=30,
        )
        self.collection = settings.qdrant_collection_name

    async def ensure_collection(self):
        if not await self.client.collection_exists(self.collection):
            await self.client.create_collection(
                collection_name=self.collection,
                vectors_config={"dense": VectorParams(size=384, distance=Distance.COSINE)},
                sparse_vectors_config={
                    "sparse": SparseVectorParams(index=SparseIndexParams(on_disk=False))
                },
            )
            logger.info(f"Created Qdrant collection: {self.collection}")

    async def search(self, query: str, top_k: int = 5) -> List[Dict]:
        dense = embedding_model.embed_dense(query)
        sparse = embedding_model.embed_sparse(query)

        results = await self.client.query_points(
            collection_name=self.collection,
            prefetch=[
                Prefetch(query=dense, using="dense", limit=top_k * 2),
                Prefetch(
                    query=SparseVector(
                        indices=sparse["indices"], values=sparse["values"]
                    ),
                    using="sparse",
                    limit=top_k * 2,
                ),
            ],
            query=FusionQuery(fusion=Fusion.RRF),
            limit=top_k,
        )
        return [pt.payload for pt in results.points if pt.payload]

    async def upsert(self, chunks: List[Dict]) -> None:
        if not chunks:
            return
        points = []
        for c in chunks:
            d = embedding_model.embed_dense(c["text"])
            s = embedding_model.embed_sparse(c["text"])
            points.append(
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector={
                        "dense": d,
                        "sparse": SparseVector(
                            indices=s["indices"], values=s["values"]
                        ),
                    },
                    payload=c["payload"],
                )
            )
        await self.client.upsert(collection_name=self.collection, points=points)


hybrid_searcher = HybridSearcher()
