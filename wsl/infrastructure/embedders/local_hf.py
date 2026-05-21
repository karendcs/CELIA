"""Embedder local via Sentence-Transformers (sem Ollama)."""
from __future__ import annotations

from typing import List

from config import Settings
from core.exceptions import EmbeddingError
from core.logging import get_logger

logger = get_logger("embedder.local_hf")


class LocalHFEmbedder:
    """
    Gera embeddings localmente usando um modelo HuggingFace.
    Não requer conectividade com Ollama.
    """

    def __init__(self, settings: Settings) -> None:
        self._batch_size = settings.embed_batch
        model_name = settings.hf_embed_model
        logger.info("Carregando modelo de embeddings: %s", model_name)
        try:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(model_name)
        except Exception as exc:
            raise EmbeddingError(
                f"Falha ao carregar modelo de embeddings '{model_name}': {exc}"
            ) from exc

    def embed(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        try:
            embeddings: list[list[float]] = []
            for i in range(0, len(texts), self._batch_size):
                batch = texts[i : i + self._batch_size]
                vecs = self._model.encode(
                    batch,
                    normalize_embeddings=True,
                    convert_to_numpy=True,
                )
                embeddings.extend(v.tolist() for v in vecs)
            return embeddings
        except Exception as exc:
            raise EmbeddingError(f"Falha ao gerar embeddings: {exc}") from exc
