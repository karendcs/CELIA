"""
Modelos de domínio (DTOs imutáveis).
Sem dependências externas — apenas stdlib.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class DocumentChunk:
    """Unidade atômica de conteúdo após chunking."""

    text: str
    source: str
    chunk_id: str
    chunk_index: int = 0


@dataclass(frozen=True)
class QueryResult:
    """Fragmento recuperado do banco vetorial com score de similaridade."""

    text: str
    source: str
    similarity: float


@dataclass
class AnswerResult:
    """Resultado completo de uma pergunta respondida pelo pipeline RAG."""

    question: str
    answer: str
    sources: list[QueryResult] = field(default_factory=list)
    model: str = ""
    elapsed_seconds: Optional[float] = None
