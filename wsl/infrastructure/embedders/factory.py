"""
Factory de Embedders — Strategy Pattern.
Decide qual implementação usar baseado na configuração,
sem expor detalhes de construção para a camada de aplicação.
"""
from __future__ import annotations

from domain.interfaces import Embedder
from config import Settings
from core.logging import get_logger

logger = get_logger("embedder.factory")


def create_embedder(settings: Settings) -> Embedder:
    """
    Retorna a implementação correta de Embedder conforme configuração.

    - USE_LOCAL_EMBEDDINGS=1 → LocalHFEmbedder (padrão; não requer Ollama)
    - USE_LOCAL_EMBEDDINGS=0 → OllamaEmbedder
    """
    if settings.use_local_embeddings:
        from infrastructure.embedders.local_hf import LocalHFEmbedder
        logger.info("Embedder: LocalHF (%s)", settings.hf_embed_model)
        return LocalHFEmbedder(settings)

    from infrastructure.embedders.ollama import OllamaEmbedder
    logger.info("Embedder: Ollama (%s)", settings.embed_model)
    return OllamaEmbedder(settings)
