"""
Gerenciamento de prompts versionados.
Centralizar prompts aqui facilita versionamento, testes e A/B testing.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

from domain.models import QueryResult


# ── Versão do prompt — incremente ao alterar comportamento ────────────────
PROMPT_VERSION = "v1.1"

# ── Template principal do RAG ─────────────────────────────────────────────
_TEMPLATE = (
    "Você é um assistente especializado em segurança da informação e compliance.\n"
    "Responda em português, de forma objetiva (máximo 5 linhas).\n"
    "Use SOMENTE as informações do CONTEXTO abaixo.\n"
    "Se a informação não estiver no contexto, responda exatamente: "
    "'Informação não encontrada nos documentos internos.'\n\n"
    "[PERGUNTA]\n{question}\n\n"
    "[CONTEXTO]\n{context}\n\n"
    "Cite as fontes no formato [Fonte N] ao final da resposta.\n"
    "Resposta:"
)

# ── Limite de caracteres por snippet de contexto ──────────────────────────
_MAX_SNIPPET_CHARS = 1200


@dataclass(frozen=True)
class PromptResult:
    prompt: str
    version: str
    context_snippets: int


class RAGPrompt:
    """
    Constrói o prompt RAG a partir de uma pergunta e dos resultados da busca vetorial.
    Mantém lógica de formatação de contexto isolada aqui (SRP).
    """

    def build(self, question: str, results: List[QueryResult]) -> PromptResult:
        context = self._build_context(results)
        prompt = _TEMPLATE.format(question=question, context=context)
        return PromptResult(
            prompt=prompt,
            version=PROMPT_VERSION,
            context_snippets=len(results),
        )

    @staticmethod
    def _build_context(results: List[QueryResult]) -> str:
        if not results:
            return "(nenhum contexto disponível)"
        parts: list[str] = []
        for i, r in enumerate(results, 1):
            text = (r.text or "").strip()
            if len(text) > _MAX_SNIPPET_CHARS:
                text = text[:_MAX_SNIPPET_CHARS] + "…"
            parts.append(f"[Fonte {i}: {r.source}]\n{text}")
        return "\n\n".join(parts)
