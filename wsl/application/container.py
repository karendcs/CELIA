"""
Container de dependências (Factory / DI manual).
Centraliza a criação e composição de todos os objetos.
Evita instanciação espalhada pelo código (Composition Root).
"""
from __future__ import annotations

from functools import lru_cache

from config import Settings, get_settings
from infrastructure.embedders.factory import create_embedder
from infrastructure.llm.ollama import OllamaLLM
from infrastructure.vector_store.chroma_repository import ChromaRepository
from infrastructure.loaders.document_loader import DocumentLoader
from application.prompts.rag_prompt import RAGPrompt
from application.services.ingest_service import IngestService
from application.services.answer_service import AnswerService
from application.pipelines.rag_pipeline import ExcelRAGPipeline


def _try_load_reranker(settings: Settings):
    """Carrega o reranker cross-encoder, se disponível."""
    try:
        from sentence_transformers import CrossEncoder
        return CrossEncoder(settings.reranker_model)
    except Exception:
        return None


@lru_cache(maxsize=1)
def _cached_deps(settings_hash: int):
    """
    Cache de dependências pesadas (embedder, reranker).
    O hash garante que mudanças de Settings invalidam o cache.
    """
    s = get_settings()
    embedder = create_embedder(s)
    reranker = _try_load_reranker(s)
    return embedder, reranker


def build_ingest_service(settings: Settings | None = None) -> IngestService:
    s = settings or get_settings()
    embedder, _ = _cached_deps(hash(s.model_dump_json()))
    repository = ChromaRepository(s)
    loader = DocumentLoader(s)
    return IngestService(loader, embedder, repository, s)


def build_answer_service(settings: Settings | None = None) -> AnswerService:
    s = settings or get_settings()
    embedder, reranker = _cached_deps(hash(s.model_dump_json()))
    repository = ChromaRepository(s)
    llm = OllamaLLM(s)
    prompt = RAGPrompt()
    return AnswerService(embedder, repository, llm, prompt, s, reranker)


def build_excel_pipeline(settings: Settings | None = None) -> ExcelRAGPipeline:
    s = settings or get_settings()
    answer_svc = build_answer_service(s)
    return ExcelRAGPipeline(answer_svc, s)
