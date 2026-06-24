"""Embedding and ChromaDB indexing."""

from __future__ import annotations

import os
from typing import Any

import chromadb
from chromadb.utils import embedding_functions

from app.logger import get_logger

logger = get_logger(__name__)

COLLECTION_MAP = {
    "faq": ["faq"],
    "technical": ["technical troubleshooting", "faq"],
    "billing": ["billing policy", "faq"],
    "account": ["account management", "faq"],
}


def _get_embedding_function() -> Any:
    openai_key = os.getenv("OPENAI_API_KEY")
    force_local = os.getenv("USE_LOCAL_EMBEDDINGS", "").lower() in ("1", "true", "yes")

    if openai_key and not force_local:
        logger.info("embedder_using_openai")
        return embedding_functions.OpenAIEmbeddingFunction(
            api_key=openai_key,
            model_name="text-embedding-3-small",
        )
    logger.info("embedder_using_local_sentence_transformers")
    return embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )


class VectorStore:
    """Wraps ChromaDB with collection-per-document-type indexing."""

    def __init__(self, persist_directory: str | None = None) -> None:
        if persist_directory:
            self.client = chromadb.PersistentClient(path=persist_directory)
        else:
            self.client = chromadb.EphemeralClient()
        self.ef = _get_embedding_function()
        self._collections: dict[str, Any] = {}

    def _get_or_create(self, name: str) -> Any:
        if name not in self._collections:
            self._collections[name] = self.client.get_or_create_collection(
                name=name,
                embedding_function=self.ef,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collections[name]

    def index_chunks(self, chunks: list[dict[str, Any]]) -> None:
        """Index all chunks into appropriate collections."""
        # Group chunks by document for collection routing
        by_doc: dict[str, list[dict]] = {}
        for chunk in chunks:
            doc = chunk["document"].lower()
            by_doc.setdefault(doc, []).append(chunk)

        for doc_name, doc_chunks in by_doc.items():
            collection_name = self._resolve_collection(doc_name)
            collection = self._get_or_create(collection_name)

            ids = [c["chunk_id"] for c in doc_chunks]
            texts = [c["text"] for c in doc_chunks]
            metadatas = [
                {
                    "document": c["document"],
                    "section": c["section"],
                    "chunk_id": c["chunk_id"],
                }
                for c in doc_chunks
            ]

            # Add in batches of 100
            batch_size = 100
            for i in range(0, len(ids), batch_size):
                collection.add(
                    ids=ids[i : i + batch_size],
                    documents=texts[i : i + batch_size],
                    metadatas=metadatas[i : i + batch_size],
                )

            logger.info(
                "chunks_indexed",
                collection=collection_name,
                count=len(doc_chunks),
                document=doc_name,
            )

    def query(self, text: str, collection_names: list[str], top_k: int = 10) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for name in collection_names:
            try:
                col = self._get_or_create(name)
                res = col.query(query_texts=[text], n_results=min(top_k, col.count() or 1))
                for i, doc in enumerate(res["documents"][0]):
                    meta = res["metadatas"][0][i]
                    dist = res["distances"][0][i]
                    results.append(
                        {
                            "chunk_id": meta["chunk_id"],
                            "document": meta["document"],
                            "section": meta["section"],
                            "text": doc,
                            "score": 1.0 - dist,  # cosine distance → similarity
                            "rank": i,
                            "source": "dense",
                        }
                    )
            except Exception as exc:
                logger.warning("vector_query_error", collection=name, error=str(exc))
        return results

    def _resolve_collection(self, doc_name: str) -> str:
        for key in COLLECTION_MAP:
            if key in doc_name:
                return key
        return "general"
