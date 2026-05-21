"""
Carregador e chunker de documentos.
Aplica chunking com overlap para evitar perda de contexto
entre fragmentos adjacentes.
Formatos suportados: .txt, .md, .pdf, .docx, .csv, .xlsx, .xls
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import List

from config import Settings
from core.exceptions import DocumentLoadError
from core.logging import get_logger
from domain.models import DocumentChunk

logger = get_logger("loaders.document")

_SUPPORTED = {".txt", ".md", ".pdf", ".docx", ".csv", ".xlsx", ".xls"}


class DocumentLoader:
    """Carrega arquivos e os divide em chunks com overlap."""

    def __init__(self, settings: Settings) -> None:
        self._chunk_size = settings.chunk_size
        self._chunk_overlap = settings.chunk_overlap

    # ── Leitura de arquivos ────────────────────────────────────────────────

    def load_file(self, path: Path) -> List[str]:
        """Retorna lista de textos brutos extraídos do arquivo."""
        suffix = path.suffix.lower()
        if suffix not in _SUPPORTED:
            return []
        try:
            return self._read(path, suffix)
        except DocumentLoadError:
            raise
        except Exception as exc:
            logger.warning("Falha ao ler '%s': %s", path, exc)
            raise DocumentLoadError(f"Não foi possível ler '{path}': {exc}") from exc

    def _read(self, path: Path, suffix: str) -> List[str]:
        if suffix in {".txt", ".md"}:
            return [path.read_text(encoding="utf-8", errors="ignore")]

        if suffix == ".pdf":
            return [self._read_pdf(path)]

        if suffix == ".docx":
            return [self._read_docx(path)]

        if suffix == ".csv":
            import pandas as pd
            df = pd.read_csv(path, encoding="utf-8", errors="ignore")
            return [df.to_csv(index=False)]

        # .xlsx / .xls
        import pandas as pd
        df = pd.read_excel(path)
        return [df.to_csv(index=False)]

    @staticmethod
    def _read_pdf(path: Path) -> str:
        from pypdf import PdfReader
        reader = PdfReader(str(path))
        pages: list[str] = []
        for page in reader.pages:
            try:
                text = page.extract_text() or ""
                pages.append(text)
            except Exception as exc:
                logger.debug("Erro ao extrair página do PDF '%s': %s", path, exc)
        return "\n".join(pages)

    @staticmethod
    def _read_docx(path: Path) -> str:
        from docx import Document
        doc = Document(str(path))
        return "\n".join(p.text for p in doc.paragraphs)

    # ── Chunking ──────────────────────────────────────────────────────────

    def chunk_text(self, text: str, source: str) -> List[DocumentChunk]:
        """Divide o texto em chunks com overlap e retorna DocumentChunks."""
        clean = re.sub(r"\s+", " ", text).strip()
        if not clean:
            return []

        size = self._chunk_size
        overlap = self._chunk_overlap
        step = max(1, size - overlap)

        chunks: list[DocumentChunk] = []
        for i, start in enumerate(range(0, len(clean), step)):
            fragment = clean[start : start + size]
            if not fragment.strip():
                continue
            chunk_id = f"{source}#chunk{i}#{abs(hash(fragment))}"
            chunks.append(
                DocumentChunk(
                    text=fragment,
                    source=source,
                    chunk_id=chunk_id,
                    chunk_index=i,
                )
            )
        return chunks

    def load_and_chunk(self, path: Path) -> List[DocumentChunk]:
        """Carrega um arquivo e retorna todos os seus chunks."""
        raw_texts = self.load_file(path)
        chunks: list[DocumentChunk] = []
        for text in raw_texts:
            chunks.extend(self.chunk_text(text, str(path)))
        return chunks

    def load_folder(self, folder: Path) -> List[DocumentChunk]:
        """Carrega e chunkeia todos os documentos suportados em uma pasta."""
        all_chunks: list[DocumentChunk] = []
        for path in sorted(folder.rglob("*")):
            if path.is_file() and path.suffix.lower() in _SUPPORTED:
                try:
                    file_chunks = self.load_and_chunk(path)
                    all_chunks.extend(file_chunks)
                    logger.info("Carregado: %s (%d chunks)", path.name, len(file_chunks))
                except DocumentLoadError as exc:
                    logger.warning("Ignorado '%s': %s", path, exc)
        return all_chunks
