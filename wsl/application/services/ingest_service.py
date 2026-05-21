"""
Serviço de ingestão de documentos na base de conhecimento.
Orquestra: DocumentLoader → Embedder → VectorRepository.
"""
from __future__ import annotations

from pathlib import Path

from config import Settings
from core.exceptions import IngestError
from core.logging import get_logger
from domain.interfaces import Embedder, VectorRepository
from infrastructure.loaders import DocumentLoader

logger = get_logger("services.ingest")


class IngestService:
    """
    Responsabilidade única: ingerir documentos de uma pasta na base vetorial.
    Usa injeção de dependência — sem criar instâncias concretas aqui.
    """

    def __init__(
        self,
        loader: DocumentLoader,
        embedder: Embedder,
        repository: VectorRepository,
        settings: Settings,
    ) -> None:
        self._loader = loader
        self._embedder = embedder
        self._repository = repository
        self._batch_size = settings.embed_batch

    def ingest_folder(self, folder: Path) -> int:
        """
        Carrega, chunkeia e armazena todos os documentos da pasta.
        Retorna o número de chunks ingeridos.
        """
        if not folder.exists():
            raise IngestError(f"Pasta de conhecimento não encontrada: {folder}")

        logger.info("Iniciando ingestão: %s", folder)
        chunks = self._loader.load_folder(folder)

        if not chunks:
            logger.warning("Nenhum documento legível encontrado em '%s'.", folder)
            return 0

        logger.info("Gerando embeddings para %d chunks...", len(chunks))
        try:
            # Processa em batches para não sobrecarregar a memória
            for i in range(0, len(chunks), self._batch_size):
                batch = chunks[i : i + self._batch_size]
                embeddings = self._embedder.embed([c.text for c in batch])
                self._repository.add(batch, embeddings)
                logger.info(
                    "Ingerido batch %d/%d (%d chunks)",
                    i // self._batch_size + 1,
                    -(-len(chunks) // self._batch_size),
                    len(batch),
                )
        except Exception as exc:
            raise IngestError(f"Falha durante a ingestão: {exc}") from exc

        logger.info("Ingestão concluída: %d chunks armazenados.", len(chunks))
        return len(chunks)
