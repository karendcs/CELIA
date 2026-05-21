"""Testes unitários da configuração centralizada."""
from __future__ import annotations

import os
import pytest
from pathlib import Path


def test_settings_defaults(test_settings):
    assert test_settings.top_k == 2
    assert test_settings.min_sim == 0.0
    assert test_settings.chunk_size == 200
    assert test_settings.chunk_overlap == 20


def test_settings_upload_dir_docker(test_settings):
    """upload_dir deve ser /uploads em modo Docker."""
    from config import Settings
    s = Settings(
        docker_mode=True,
        uploader_password="test-password-safe",
        knowledge_dir=Path("/tmp/knowledge"),
        vector_db_dir=Path("/tmp/chroma"),
    )
    assert s.upload_dir == Path("/uploads")


def test_settings_upload_dir_local(test_settings):
    """upload_dir deve ser o path local fora do Docker."""
    assert test_settings.upload_dir == Path("/mnt/c/IA-Privada/uploads")


def test_settings_password_validator_warns():
    """Deve emitir warning para senhas padrão inseguras."""
    from config import Settings
    import warnings
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        Settings(
            uploader_password="troque123",
            knowledge_dir=Path("/tmp/knowledge"),
            vector_db_dir=Path("/tmp/chroma"),
        )
        assert any("inseguro" in str(warning.message).lower() for warning in w)


def test_settings_singleton_cache():
    """get_settings deve retornar a mesma instância."""
    from config import get_settings
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2
