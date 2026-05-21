"""Testes unitários do RAGPrompt."""
from __future__ import annotations

import pytest
from domain.models import QueryResult
from application.prompts.rag_prompt import RAGPrompt, PROMPT_VERSION


@pytest.fixture()
def prompt_builder():
    return RAGPrompt()


def test_build_returns_prompt_result(prompt_builder):
    results = [QueryResult(text="Texto A", source="a.txt", similarity=0.9)]
    pr = prompt_builder.build("O que é MFA?", results)
    assert "O que é MFA?" in pr.prompt
    assert "Texto A" in pr.prompt
    assert pr.version == PROMPT_VERSION
    assert pr.context_snippets == 1


def test_build_no_results_shows_no_context(prompt_builder):
    pr = prompt_builder.build("Pergunta?", [])
    assert "nenhum contexto" in pr.prompt.lower()
    assert pr.context_snippets == 0


def test_build_truncates_long_snippet(prompt_builder):
    long_text = "A" * 2000
    results = [QueryResult(text=long_text, source="big.txt", similarity=0.7)]
    pr = prompt_builder.build("Pergunta?", results)
    # O texto no prompt deve estar truncado
    assert len(pr.prompt) < len(long_text) + 500


def test_build_multiple_sources_indexed(prompt_builder):
    results = [
        QueryResult(text="Fonte A", source="a.txt", similarity=0.9),
        QueryResult(text="Fonte B", source="b.txt", similarity=0.8),
    ]
    pr = prompt_builder.build("Pergunta?", results)
    assert "[Fonte 1:" in pr.prompt
    assert "[Fonte 2:" in pr.prompt


def test_prompt_version_is_string():
    assert isinstance(PROMPT_VERSION, str)
    assert len(PROMPT_VERSION) > 0
