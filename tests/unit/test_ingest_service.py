"""Testes unitários do IngestService."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest


def test_ingest_folder_calls_add(test_settings, tmp_path, sample_txt, mock_embedder, mock_repository):
    import shutil
    from infrastructure.loaders.document_loader import DocumentLoader
    from application.services.ingest_service import IngestService

    shutil.copy(sample_txt, tmp_path / "doc.txt")
    loader = DocumentLoader(test_settings)
    svc = IngestService(loader, mock_embedder, mock_repository, test_settings)

    count = svc.ingest_folder(tmp_path)

    assert count > 0
    assert mock_embedder.embed.called
    assert mock_repository.add.called


def test_ingest_empty_folder_returns_zero(test_settings, tmp_path, mock_embedder, mock_repository):
    from infrastructure.loaders.document_loader import DocumentLoader
    from application.services.ingest_service import IngestService

    loader = DocumentLoader(test_settings)
    svc = IngestService(loader, mock_embedder, mock_repository, test_settings)

    count = svc.ingest_folder(tmp_path)

    assert count == 0
    mock_embedder.embed.assert_not_called()
    mock_repository.add.assert_not_called()


def test_ingest_nonexistent_folder_raises(test_settings, mock_embedder, mock_repository):
    from infrastructure.loaders.document_loader import DocumentLoader
    from application.services.ingest_service import IngestService
    from core.exceptions import IngestError

    loader = DocumentLoader(test_settings)
    svc = IngestService(loader, mock_embedder, mock_repository, test_settings)

    with pytest.raises(IngestError, match="não encontrada"):
        svc.ingest_folder(Path("/pasta/inexistente"))
