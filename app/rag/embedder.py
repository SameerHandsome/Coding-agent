# app/rag/embedder.py
from fastembed import TextEmbedding, SparseTextEmbedding
from typing import List, Dict


class EmbeddingModel:
    def __init__(self):
        self._dense = TextEmbedding("BAAI/bge-small-en-v1.5")
        self._sparse = SparseTextEmbedding("prithivida/Splade_PP_en_v1")

    def embed_dense(self, text: str) -> List[float]:
        return list(self._dense.embed([text]))[0].tolist()

    def embed_sparse(self, text: str) -> Dict:
        s = list(self._sparse.embed([text]))[0]
        return {"indices": s.indices.tolist(), "values": s.values.tolist()}

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [r.tolist() for r in self._dense.embed(texts)]


embedding_model = EmbeddingModel()
