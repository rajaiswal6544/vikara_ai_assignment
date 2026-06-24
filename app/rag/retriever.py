"""Hybrid retrieval: dense (ChromaDB) + sparse (BM25) + RRF fusion + cross-encoder re-ranking."""

from __future__ import annotations

import os
from typing import Any

from rank_bm25 import BM25Okapi

from app.logger import get_logger

logger = get_logger(__name__)

# Collection groups for domain routing
DOMAIN_COLLECTIONS: dict[str, list[str]] = {
    "technical": ["technical", "faq", "account"],
    "billing": ["billing", "faq"],
    "account": ["account", "faq", "technical"],
    "general": ["faq", "technical"],
    "triage": ["faq", "technical", "billing", "account"],
}


def _rrf_score(ranks: list[int], k: int = 60) -> float:
    return sum(1.0 / (k + r) for r in ranks)


def _fuse_results(
    dense_results: list[dict],
    sparse_results: list[dict],
) -> list[dict]:
    """Reciprocal Rank Fusion over dense + sparse results."""
    scores: dict[str, dict] = {}

    for rank, item in enumerate(dense_results):
        cid = item["chunk_id"]
        if cid not in scores:
            scores[cid] = {**item, "dense_rank": rank, "sparse_rank": len(dense_results) + 1}
        scores[cid]["dense_rank"] = rank

    for rank, item in enumerate(sparse_results):
        cid = item["chunk_id"]
        if cid not in scores:
            scores[cid] = {**item, "dense_rank": len(sparse_results) + 1, "sparse_rank": rank}
        scores[cid]["sparse_rank"] = rank

    for cid, data in scores.items():
        data["rrf_score"] = _rrf_score([data["dense_rank"], data["sparse_rank"]])

    return sorted(scores.values(), key=lambda x: x["rrf_score"], reverse=True)


class BM25Index:
    """Sparse keyword index over all KB chunks."""

    def __init__(self) -> None:
        self._chunks: list[dict] = []
        self._index: BM25Okapi | None = None

    def build(self, chunks: list[dict]) -> None:
        self._chunks = chunks
        tokenized = [c["text"].lower().split() for c in chunks]
        self._index = BM25Okapi(tokenized)
        logger.info("bm25_index_built", chunk_count=len(chunks))

    def query(self, text: str, top_k: int = 20) -> list[dict]:
        if not self._index or not self._chunks:
            return []
        tokens = text.lower().split()
        scores = self._index.get_scores(tokens)
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)[:top_k]
        results = []
        for rank, (idx, score) in enumerate(ranked):
            chunk = self._chunks[idx].copy()
            chunk["score"] = float(score)
            chunk["rank"] = rank
            chunk["source"] = "sparse"
            results.append(chunk)
        return results


class CrossEncoderReranker:
    """Optional cross-encoder re-ranking. Falls back to RRF order if model unavailable."""

    def __init__(self) -> None:
        self._model = None
        self._available = False
        self._try_load()

    def _try_load(self) -> None:
        if os.getenv("DISABLE_RERANKER", "").lower() in ("1", "true", "yes"):
            logger.info("reranker_disabled_by_env")
            return
        try:
            from sentence_transformers import CrossEncoder  # type: ignore

            self._model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
            self._available = True
            logger.info("cross_encoder_loaded")
        except Exception as exc:
            logger.warning("cross_encoder_unavailable", error=str(exc))

    def rerank(self, query: str, candidates: list[dict], top_k: int = 5) -> list[dict]:
        if not self._available or not self._model:
            return candidates[:top_k]
        pairs = [(query, c["text"]) for c in candidates]
        scores = self._model.predict(pairs)
        ranked = sorted(zip(scores, candidates), key=lambda x: x[0], reverse=True)
        return [item for _, item in ranked[:top_k]]


class RAGPipeline:
    """Orchestrates retrieval: query rewrite → dense + sparse → RRF → re-rank."""

    def __init__(self, vector_store: Any, bm25_index: BM25Index) -> None:
        self.vector_store = vector_store
        self.bm25 = bm25_index
        self.reranker = CrossEncoderReranker()

    async def retrieve(
        self,
        query: str,
        state: Any,
        collections: list[str] | None = None,
        top_k: int = 5,
    ) -> list[dict]:
        if not collections:
            collections = ["technical", "faq"]

        # Resolve collection names from aliases
        resolved: list[str] = []
        for c in collections:
            resolved.extend(DOMAIN_COLLECTIONS.get(c, [c]))
        resolved = list(dict.fromkeys(resolved))  # dedup, preserve order

        dense = self.vector_store.query(query, resolved, top_k=20)
        sparse = self.bm25.query(query, top_k=20)

        fused = _fuse_results(dense, sparse)

        # Filter to only chunks from the desired collections
        filtered = [
            c for c in fused
            if any(col in c.get("document", "").lower() for col in resolved)
               or not dense  # if no dense results, keep all sparse
        ]
        if not filtered:
            filtered = fused  # fall back to all fused

        final = self.reranker.rerank(query, filtered, top_k=top_k)

        logger.info(
            "rag_retrieval",
            trace_id=getattr(state, "trace_id", ""),
            query_len=len(query),
            dense_count=len(dense),
            sparse_count=len(sparse),
            final_count=len(final),
        )
        return final
