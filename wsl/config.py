"""
Configuração centralizada via Pydantic Settings.
Todas as variáveis de ambiente são declaradas aqui, com tipos e defaults explícitos.
Nenhum outro módulo deve chamar os.getenv() diretamente.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file="settings.env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── LLM ──────────────────────────────────────────────────────────────
    ollama_url: str = Field("http://localhost:11434", alias="OLLAMA_URL")
    model_name: str = Field("llama3:8b", alias="MODEL_NAME")

    # ── Geração ───────────────────────────────────────────────────────────
    max_tokens: int = Field(96, alias="MAX_TOKENS", ge=1)
    num_ctx: int = Field(1024, alias="NUM_CTX", ge=128)
    temperature: float = Field(0.2, alias="TEMP", ge=0.0, le=2.0)
    top_p: float = Field(0.9, alias="TOP_P", ge=0.0, le=1.0)
    repeat_penalty: float = Field(1.1, alias="REPEAT_PENALTY", ge=0.0)
    num_threads: int = Field(0, alias="NUM_THREADS", ge=0)

    # ── Timeouts ──────────────────────────────────────────────────────────
    ollama_connect_timeout: int = Field(10, alias="OLLAMA_CONNECT_TIMEOUT", ge=1)
    ollama_read_timeout: int = Field(1200, alias="OLLAMA_READ_TIMEOUT", ge=1)

    # ── Embeddings ────────────────────────────────────────────────────────
    embed_model: str = Field("nomic-embed-text", alias="EMBED_MODEL")
    use_local_embeddings: bool = Field(True, alias="USE_LOCAL_EMBEDDINGS")
    hf_embed_model: str = Field("intfloat/multilingual-e5-small", alias="HF_EMBED_MODEL")
    embed_batch: int = Field(64, alias="EMBED_BATCH", ge=1)

    # ── RAG ───────────────────────────────────────────────────────────────
    collection_name: str = Field("knowledge_base", alias="COLLECTION_NAME")
    knowledge_dir: Path = Field(Path("./knowledge"), alias="KNOWLEDGE_DIR")
    vector_db_dir: Path = Field(Path("./chroma_store"), alias="VECTOR_DB_DIR")
    top_k: int = Field(6, alias="TOP_K", ge=1)
    min_sim: float = Field(0.35, alias="MIN_SIM", ge=0.0, le=1.0)
    reranker_model: str = Field(
        "cross-encoder/ms-marco-MiniLM-L-6-v2", alias="RERANKER_MODEL"
    )

    # ── Chunking ──────────────────────────────────────────────────────────
    chunk_size: int = Field(1200, alias="CHUNK_SIZE", ge=100)
    chunk_overlap: int = Field(150, alias="CHUNK_OVERLAP", ge=0)

    # ── App / Infra ────────────────────────────────────────────────────────
    docker_mode: bool = Field(False, alias="DOCKER_MODE")
    uploader_user: str = Field("admin", alias="UPLOADER_USER")
    uploader_password: str = Field("changeme", alias="UPLOADER_PASSWORD")

    # ── Cleanup ───────────────────────────────────────────────────────────
    keep_xlsx: int = Field(3, alias="KEEP_XLSX", ge=1)
    keep_logs: int = Field(3, alias="KEEP_LOGS", ge=1)

    @field_validator("uploader_password")
    @classmethod
    def password_not_default(cls, v: str) -> str:
        if v in ("troque123", "changeme", "admin", "password", "123456"):
            import warnings
            warnings.warn(
                "UPLOADER_PASSWORD está usando um valor padrão inseguro. "
                "Defina UPLOADER_PASSWORD no ambiente antes de subir em produção.",
                stacklevel=2,
            )
        return v

    @property
    def upload_dir(self) -> Path:
        if self.docker_mode:
            return Path("/uploads")
        return Path("/mnt/c/IA-Privada") / "uploads"

    @property
    def wsl_dir(self) -> Path:
        if self.docker_mode:
            return Path("/app")
        return Path("/mnt/c/IA-Privada") / "wsl"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Retorna a instância singleton de Settings (cache em memória)."""
    return Settings()
