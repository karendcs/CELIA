"""Hierarquia de exceções do domínio CelIA."""
from __future__ import annotations


class CelIAError(Exception):
    """Exceção base de todos os erros do CelIA."""


class EmbeddingError(CelIAError):
    """Falha ao gerar embeddings."""


class LLMError(CelIAError):
    """Falha na comunicação com o LLM."""


class LLMModelNotFoundError(LLMError):
    """Modelo LLM não encontrado no provider."""


class VectorStoreError(CelIAError):
    """Falha em operação no banco vetorial."""


class DocumentLoadError(CelIAError):
    """Falha ao carregar/parsear documento."""


class IngestError(CelIAError):
    """Falha durante o processo de ingestão."""


class AnswerError(CelIAError):
    """Falha ao gerar resposta RAG."""


class AuthenticationError(CelIAError):
    """Credenciais inválidas."""


class FileValidationError(CelIAError):
    """Arquivo enviado não é válido."""
