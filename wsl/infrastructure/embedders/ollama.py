"""Embedder via API do Ollama."""
from __future__ import annotations

from typing import List

import requests

from config import Settings
from core.exceptions import EmbeddingError
from core.logging import get_logger

logger = get_logger("embedder.ollama")


class OllamaEmbedder:
    """Gera embeddings chamando a API /api/embeddings do Ollama."""

    def __init__(self, settings: Settings) -> None:
        self._base_url = settings.ollama_url.rstrip("/")
        self._model = settings.embed_model
        self._timeout = (settings.ollama_connect_timeout, settings.ollama_read_timeout)

    def embed(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        url = f"{self._base_url}/api/embeddings"
        embeddings: list[list[float]] = []
        for text in texts:
            try:
                response = requests.post(
                    url,
                    json={"model": self._model, "input": text},
                    timeout=self._timeout,
                )
            except requests.RequestException as exc:
                raise EmbeddingError(f"Erro de rede ao chamar Ollama embeddings: {exc}") from exc

            if response.status_code == 404:
                raise EmbeddingError(
                    f"Modelo de embedding '{self._model}' não encontrado no Ollama. "
                    "Verifique se foi baixado com 'ollama pull'."
                )
            try:
                response.raise_for_status()
            except requests.HTTPError as exc:
                raise EmbeddingError(f"Ollama retornou erro HTTP: {exc}") from exc

            data = response.json()
            emb = data.get("embedding")
            if not emb:
                raise EmbeddingError(f"Resposta inesperada do Ollama embeddings: {data}")
            embeddings.append(emb)
        return embeddings
