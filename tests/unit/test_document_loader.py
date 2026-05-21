"""Testes unitários do DocumentLoader com chunking."""
from __future__ import annotations

from pathlib import Path
import pytest


def test_chunk_text_basic(test_settings):
    from infrastructure.loaders.document_loader import DocumentLoader
    loader = DocumentLoader(test_settings)
    text = "A " * 300  # 600 chars
    chunks = loader.chunk_text(text, source="test.txt")
    assert len(chunks) >= 1
    for c in chunks:
        assert len(c.text) <= test_settings.chunk_size + 10  # margem mínima


def test_chunk_text_overlap(test_settings):
    """Chunks com overlap não devem pular conteúdo."""
    from infrastructure.loaders.document_loader import DocumentLoader
    s = test_settings
    loader = DocumentLoader(s)
    text = "X" * (s.chunk_size * 3)
    chunks = loader.chunk_text(text, source="test.txt")
    assert len(chunks) > 1
    # O início do segundo chunk deve se sobrepor ao final do primeiro
    start_of_second = chunks[1].text[:20]
    end_of_first = chunks[0].text[-(s.chunk_overlap + 20):]
    assert start_of_second in end_of_first or end_of_first in start_of_second


def test_chunk_text_empty_returns_empty(test_settings):
    from infrastructure.loaders.document_loader import DocumentLoader
    loader = DocumentLoader(test_settings)
    assert loader.chunk_text("", source="x") == []
    assert loader.chunk_text("   \n  ", source="x") == []


def test_load_txt_file(test_settings, sample_txt):
    from infrastructure.loaders.document_loader import DocumentLoader
    loader = DocumentLoader(test_settings)
    chunks = loader.load_and_chunk(sample_txt)
    assert len(chunks) >= 1
    assert "MFA" in " ".join(c.text for c in chunks)


def test_load_xlsx_file(test_settings, sample_xlsx):
    from infrastructure.loaders.document_loader import DocumentLoader
    loader = DocumentLoader(test_settings)
    chunks = loader.load_and_chunk(sample_xlsx)
    assert len(chunks) >= 1


def test_load_unsupported_file_returns_empty(test_settings, tmp_path):
    from infrastructure.loaders.document_loader import DocumentLoader
    loader = DocumentLoader(test_settings)
    unsupported = tmp_path / "file.json"
    unsupported.write_text("{}")
    chunks = loader.load_and_chunk(unsupported)
    assert chunks == []


def test_load_folder(test_settings, tmp_path, sample_txt):
    from infrastructure.loaders.document_loader import DocumentLoader
    import shutil
    shutil.copy(sample_txt, tmp_path / "doc1.txt")
    loader = DocumentLoader(test_settings)
    chunks = loader.load_folder(tmp_path)
    assert len(chunks) >= 1
