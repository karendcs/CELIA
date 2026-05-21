"""Cliente LLM via API do Ollama com retry e fallback de endpoint."""
from __future__ import annotations

from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import Settings
from core.exceptions import LLMError, LLMModelNotFoundError
from core.logging import get_logger

logger = get_logger("llm.ollama")

_RETRY_STATUS = frozenset([502, 503, 504])


class OllamaLLM:
    """
    Encapsula toda a comunicação com o Ollama.
    Tenta /api/generate primeiro; faz fallback para /api/chat se 404.
    """

    def __init__(self, settings: Settings) -> None:
        self._base_url = settings.ollama_url.rstrip("/")
        self._model = settings.model_name
        self._default_max_tokens = settings.max_tokens
        self._options = {
            "num_ctx": settings.num_ctx,
            "temperature": settings.temperature,
            "top_p": settings.top_p,
            "repeat_penalty": settings.repeat_penalty,
        }
        if settings.num_threads > 0:
            self._options["num_thread"] = settings.num_threads

        self._timeout = (settings.ollama_connect_timeout, settings.ollama_read_timeout)
        self._session = self._build_session()

    @staticmethod
    def _build_session() -> requests.Session:
        session = requests.Session()
        adapter = HTTPAdapter(
            max_retries=Retry(
                total=2,
                backoff_factor=2,
                status_forcelist=_RETRY_STATUS,
                allowed_methods=frozenset(["POST", "GET"]),
            )
        )
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def warmup(self) -> None:
        """Carrega o modelo em memória com uma chamada de 1 token."""
        try:
            url = f"{self._base_url}/api/generate"
            payload = {
                "model": self._model,
                "prompt": "ok",
                "options": {"num_predict": 1},
                "stream": False,
            }
            resp = self._session.post(url, json=payload, timeout=self._timeout)
            if resp.ok:
                logger.info("Warmup do modelo '%s' concluído.", self._model)
            else:
                logger.warning(
                    "Warmup falhou (continuando): Ollama retornou %s: %s",
                    resp.status_code,
                    resp.text,
                )
        except Exception as exc:
            logger.warning("Warmup falhou (continuando): %s", exc)

    def generate(self, prompt: str, max_tokens: Optional[int] = None) -> str:
        num_predict = max_tokens if isinstance(max_tokens, int) and max_tokens > 0 else self._default_max_tokens
        options = {**self._options, "num_predict": num_predict}

        # Tentativa 1: /api/generate
        gen_url = f"{self._base_url}/api/generate"
        try:
            resp = self._session.post(
                gen_url,
                json={"model": self._model, "prompt": prompt, "options": options, "stream": False},
                timeout=self._timeout,
            )
        except requests.RequestException as exc:
            raise LLMError(f"Erro de rede ao chamar Ollama: {exc}") from exc

        if resp.status_code == 404:
            return self._generate_via_chat(prompt, options)

        if not resp.ok:
            raise LLMError(f"Ollama /api/generate retornou {resp.status_code}: {resp.text}")

        return (resp.json().get("response") or "").strip()

    def _generate_via_chat(self, prompt: str, options: dict) -> str:
        """Fallback para /api/chat quando /api/generate retorna 404."""
        chat_url = f"{self._base_url}/api/chat"
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": "Responda de forma concisa e objetiva."},
                {"role": "user", "content": prompt},
            ],
            "options": options,
            "stream": False,
        }
        try:
            resp = self._session.post(chat_url, json=payload, timeout=self._timeout)
        except requests.RequestException as exc:
            raise LLMError(f"Erro de rede ao chamar Ollama /api/chat: {exc}") from exc

        if resp.status_code == 404:
            raise LLMModelNotFoundError(
                f"Modelo '{self._model}' não encontrado. "
                "Execute: docker compose exec ollama ollama pull <modelo>"
            )
        if not resp.ok:
            raise LLMError(f"Ollama /api/chat retornou {resp.status_code}: {resp.text}")

        content = (resp.json().get("message") or {}).get("content", "")
        return (content or "").strip()
