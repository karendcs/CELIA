"""Testes unitários do AnswerService."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from domain.models import QueryResult


def _build_service(test_settings, mock_embedder, mock_repository, mock_llm, reranker=None):
    from application.prompts.rag_prompt import RAGPrompt
    from application.services.answer_service import AnswerService
    return AnswerService(
        embedder=mock_embedder,
        repository=mock_repository,
        llm=mock_llm,
        prompt_builder=RAGPrompt(),
        settings=test_settings,
        reranker=reranker,
    )


def test_answer_returns_result(test_settings, mock_embedder, mock_repository, mock_llm):
    svc = _build_service(test_settings, mock_embedder, mock_repository, mock_llm)
    result = svc.answer("O que é MFA?")

    assert result.question == "O que é MFA?"
    assert result.answer == "Resposta de teste."
    assert result.elapsed_seconds is not None
    mock_embedder.embed.assert_called_once_with(["O que é MFA?"])
    mock_llm.generate.assert_called_once()


def test_answer_uses_repository_query(test_settings, mock_embedder, mock_repository, mock_llm):
    svc = _build_service(test_settings, mock_embedder, mock_repository, mock_llm)
    svc.answer("Pergunta qualquer")

    mock_repository.query.assert_called_once()
    call_kwargs = mock_repository.query.call_args.kwargs
    assert "query_embedding" in call_kwargs
    assert "top_k" in call_kwargs


def test_answer_with_empty_repository(test_settings, mock_embedder, mock_llm):
    from domain.models import QueryResult
    repo = MagicMock()
    repo.count.return_value = 0
    repo.query.return_value = []

    svc = _build_service(test_settings, mock_embedder, repo, mock_llm)
    result = svc.answer("Pergunta?")

    # Mesmo sem contexto, deve responder (prompt inclui "nenhum contexto disponível")
    assert result.answer == "Resposta de teste."


def test_answer_llm_error_raises_answer_error(test_settings, mock_embedder, mock_repository):
    from core.exceptions import AnswerError, LLMError
    llm = MagicMock()
    llm.generate.side_effect = LLMError("LLM offline")

    svc = _build_service(test_settings, mock_embedder, mock_repository, llm)

    with pytest.raises(AnswerError):
        svc.answer("Pergunta que vai falhar")


def test_answer_with_reranker(test_settings, mock_embedder, mock_repository, mock_llm):
    reranker = MagicMock()
    reranker.predict.return_value = [0.9, 0.5]

    svc = _build_service(test_settings, mock_embedder, mock_repository, mock_llm, reranker=reranker)
    result = svc.answer("Pergunta com reranker")

    assert result.answer == "Resposta de teste."
    reranker.predict.assert_called_once()
