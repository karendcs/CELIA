"""
Repositório ChromaDB — implementa VectorRepository do domínio.
Repository Pattern: isola todos os detalhes do ChromaDB aqui.
"""
from __future__ import annotations

from typing import List

import chromadb
from chromadb.config import Settings as ChromaSettings

from config import Settings
from core.exceptions import VectorStoreError
from core.logging import get_logger
from domain.models import DocumentChunk, QueryResult

logger = get_logger("vector_store.chroma")


class ChromaRepository:
    """Persiste e recupera embeddings via ChromaDB com distância cosine."""

    def __init__(self, settings: Settings) -> None:
        persist_dir = str(settings.vector_db_dir)
        collection_name = settings.collection_name
        try:
            self._client = chromadb.Client(
                ChromaSettings(
                    persist_directory=persist_dir,
                    is_persistent=True,
                    anonymized_telemetry=False,
                )
            )
            self._collection = self._client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info(
                "ChromaDB inicializado: dir=%s, collection=%s", persist_dir, collection_name
            )
        except Exception as exc:
            raise VectorStoreError(f"Falha ao inicializar ChromaDB: {exc}") from exc

    def add(self, chunks: List[DocumentChunk], embeddings: List[List[float]]) -> None:
        if not chunks:
            return
        try:
            self._collection.add(
                documents=[c.text for c in chunks],
                metadatas=[{"source": c.source} for c in chunks],
                ids=[c.chunk_id for c in chunks],
                embeddings=embeddings,
            )
            logger.info("Adicionados %d chunks ao ChromaDB.", len(chunks))
        except Exception as exc:
            raise VectorStoreError(f"Falha ao adicionar chunks: {exc}") from exc

    def query(
        self,
        query_embedding: List[float],
        top_k: int,
        min_similarity: float = 0.0,
    ) -> List[QueryResult]:
        total = self.count()
        if total == 0:
            return []

        n_results = min(top_k * 2, total)
        try:
            res = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as exc:
            raise VectorStoreError(f"Falha ao consultar ChromaDB: {exc}") from exc

        docs = res.get("documents", [[]])[0]
        metas = res.get("metadatas", [[]])[0]
        dists = res.get("distances", [[]])[0]

        results: list[QueryResult] = []
        for doc, meta, dist in zip(docs, metas, dists):
            similarity = 1.0 - float(dist)
            if similarity >= min_similarity and (doc or "").strip():
                results.append(
                    QueryResult(
                        text=doc,
                        source=meta.get("source", ""),
                        similarity=similarity,
                    )
                )
        return results

    def count(self) -> int:
        try:
            return self._collection.count()
        except Exception:
            return 0
