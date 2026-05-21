"""
conftest.py — fixtures compartilhadas entre todos os testes.
"""
from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import MagicMock, patch

import openpyxl
import pytest

# ── Settings de teste (sem .env real) ─────────────────────────────────────

@pytest.fixture(scope="session")
def test_settings():
    """Settings com valores padrão seguros para testes."""
    import os
    os.environ.setdefault("UPLOADER_PASSWORD", "test-password-safe")
    from config import Settings
    return Settings(
        ollama_url="http://localhost:11434",
        model_name="test-model",
        max_tokens=32,
        num_ctx=512,
        temperature=0.0,
        top_p=1.0,
        repeat_penalty=1.0,
        num_threads=0,
        ollama_connect_timeout=5,
        ollama_read_timeout=30,
        embed_model="nomic-embed-text",
        use_local_embeddings=False,
        hf_embed_model="test-embed-model",
        embed_batch=4,
        collection_name="test_collection",
        knowledge_dir=Path("/tmp/knowledge"),
        vector_db_dir=Path("/tmp/chroma"),
        top_k=2,
        min_sim=0.0,
        reranker_model="test-reranker",
        chunk_size=200,
        chunk_overlap=20,
        docker_mode=False,
        uploader_user="testuser",
        uploader_password="test-password-safe",
        keep_xlsx=3,
        keep_logs=3,
    )


# ── Mocks de domínio ───────────────────────────────────────────────────────

@pytest.fixture()
def mock_embedder():
    """Embedder que retorna vetores fixos [0.1, 0.2, 0.3]."""
    embedder = MagicMock()
    embedder.embed.side_effect = lambda texts: [[0.1, 0.2, 0.3] for _ in texts]
    return embedder


@pytest.fixture()
def mock_llm():
    """LLM que retorna resposta fixa."""
    llm = MagicMock()
    llm.generate.return_value = "Resposta de teste."
    llm.warmup.return_value = None
    return llm


@pytest.fixture()
def mock_repository():
    """VectorRepository vazio por padrão."""
    from domain.models import QueryResult
    repo = MagicMock()
    repo.count.return_value = 2
    repo.query.return_value = [
        QueryResult(text="Contexto de teste A.", source="fonte_a.txt", similarity=0.9),
        QueryResult(text="Contexto de teste B.", source="fonte_b.txt", similarity=0.8),
    ]
    repo.add.return_value = None
    return repo


# ── Fixtures de arquivos ───────────────────────────────────────────────────

@pytest.fixture()
def sample_xlsx(tmp_path: Path) -> Path:
    """Cria um .xlsx de teste com perguntas e coluna de respostas vazia."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Seguranca"
    ws.append(["Pergunta", "Resposta"])
    ws.append(["O que é MFA?", ""])
    ws.append(["Como proteger dados sensíveis?", ""])
    path = tmp_path / "teste.xlsx"
    wb.save(path)
    return path


@pytest.fixture()
def sample_txt(tmp_path: Path) -> Path:
    """Cria um .txt de teste."""
    path = tmp_path / "knowledge.txt"
    path.write_text(
        "MFA (Multi-Factor Authentication) é um mecanismo de segurança que exige "
        "dois ou mais fatores para autenticação. "
        "Dados sensíveis devem ser criptografados em repouso e em trânsito.",
        encoding="utf-8",
    )
    return path
