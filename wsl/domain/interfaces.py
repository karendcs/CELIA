"""
Interfaces (Protocols) do domínio.
Permite inversão de dependência: a camada de aplicação depende
de abstrações, não de implementações concretas.
"""
from __future__ import annotations

from typing import List, Protocol, runtime_checkable

from domain.models import DocumentChunk, QueryResult


@runtime_checkable
class Embedder(Protocol):
    """Contrato para geração de embeddings."""

    def embed(self, texts: List[str]) -> List[List[float]]:
        ...


@runtime_checkable
class LLMClient(Protocol):
    """Contrato para clientes de LLM."""

    def generate(self, prompt: str, max_tokens: int | None = None) -> str:
        ...

    def warmup(self) -> None:
        ...


@runtime_checkable
class VectorRepository(Protocol):
    """Contrato para repositórios de vetores."""

    def add(
        self,
        chunks: List[DocumentChunk],
        embeddings: List[List[float]],
    ) -> None:
        ...

    def query(
        self,
        query_embedding: List[float],
        top_k: int,
        min_similarity: float = 0.0,
    ) -> List[QueryResult]:
        ...

    def count(self) -> int:
        ...
