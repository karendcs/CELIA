"""
Serviço de resposta a uma pergunta via pipeline RAG.
Orquestra: Embedder → VectorRepository → Reranker (opcional) → RAGPrompt → LLMClient.
"""
from __future__ import annotations

import time
from typing import List, Optional

from config import Settings
from core.exceptions import AnswerError
from core.logging import get_logger
from domain.interfaces import Embedder, LLMClient, VectorRepository
from domain.models import AnswerResult, QueryResult
from application.prompts import RAGPrompt

logger = get_logger("services.answer")


class AnswerService:
    """
    Responsabilidade única: responder uma pergunta usando RAG.
    O reranker é opcional e injetado como dependência.
    """

    def __init__(
        self,
        embedder: Embedder,
        repository: VectorRepository,
        llm: LLMClient,
        prompt_builder: RAGPrompt,
        settings: Settings,
        reranker: Optional[object] = None,
    ) -> None:
        self._embedder = embedder
        self._repository = repository
        self._llm = llm
        self._prompt = prompt_builder
        self._top_k = settings.top_k
        self._min_sim = settings.min_sim
        self._max_tokens = settings.max_tokens
        self._reranker = reranker

    def answer(self, question: str) -> AnswerResult:
        """Responde uma única pergunta. Levanta AnswerError em caso de falha."""
        start = time.monotonic()
        try:
            # 1. Embed da pergunta
            q_embedding = self._embedder.embed([question])[0]

            # 2. Busca vetorial com filtro de similaridade mínima
            candidates: List[QueryResult] = self._repository.query(
                query_embedding=q_embedding,
                top_k=self._top_k,
                min_similarity=self._min_sim,
            )

            # 3. Reranking opcional (melhora precisão sem custo de LLM)
            ranked = self._rerank(question, candidates) if self._reranker else candidates[: self._top_k]

            # 4. Construção do prompt versionado
            prompt_result = self._prompt.build(question, ranked)

            # 5. Geração da resposta
            answer_text = self._llm.generate(prompt_result.prompt, max_tokens=self._max_tokens)

            elapsed = time.monotonic() - start
            logger.debug(
                "Pergunta respondida em %.2fs | contexto=%d snippets | prompt=%s",
                elapsed,
                prompt_result.context_snippets,
                prompt_result.version,
            )
            return AnswerResult(
                question=question,
                answer=answer_text,
                sources=ranked,
                elapsed_seconds=elapsed,
            )
        except Exception as exc:
            raise AnswerError(f"Falha ao responder '{question[:60]}...': {exc}") from exc

    def _rerank(self, question: str, candidates: List[QueryResult]) -> List[QueryResult]:
        """Reordena candidatos usando cross-encoder, se disponível."""
        try:
            pairs = [(question, c.text) for c in candidates]
            scores = self._reranker.predict(pairs)  # type: ignore[union-attr]
            ranked = sorted(
                zip(scores, candidates),
                key=lambda x: float(x[0]),
                reverse=True,
            )
            return [c for _, c in ranked[: self._top_k]]
        except Exception as exc:
            logger.warning("Reranker falhou, usando ordem original: %s", exc)
            return candidates[: self._top_k]
