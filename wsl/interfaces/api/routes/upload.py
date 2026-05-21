"""
Rotas de upload e download de planilhas.
Toda lógica de negócio é delegada ao ExcelRAGPipeline — esta
camada é responsável apenas por HTTP (validação, streaming, auth).
"""
from __future__ import annotations

import asyncio
import os
import shutil
import stat
import time
from pathlib import Path

from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse

from config import get_settings
from core.logging import get_logger
from interfaces.api.auth import require_auth
from application.container import build_excel_pipeline

logger = get_logger("api.routes.upload")

router = APIRouter()

_ALLOWED_EXT = ".xlsx"
_ALLOWED_MIME = {
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/octet-stream",
}


def br_now() -> datetime:
    try:
        return datetime.now(ZoneInfo("America/Sao_Paulo"))
    except Exception:
        return datetime.now()


# ── Helpers de limpeza ────────────────────────────────────────────────────

def _safe_unlink(path: Path, retries: int = 3, delay: float = 0.4) -> bool:
    for attempt in range(retries + 1):
        try:
            os.chmod(path, stat.S_IWRITE)
            path.unlink(missing_ok=True)
            return True
        except PermissionError:
            if attempt == retries:
                return False
            time.sleep(delay)
        except FileNotFoundError:
            return True
        except Exception:
            if attempt == retries:
                return False
            time.sleep(delay)
    return False


def cleanup_upload_dir(base: Path, keep_xlsx: int, keep_logs: int) -> tuple[int, int]:
    try:
        xlsx = sorted(base.glob("*_respondido.xlsx"), key=lambda p: p.stat().st_mtime, reverse=True)
        logs = sorted(base.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
        removed_x = sum(1 for p in xlsx[keep_xlsx:] if _safe_unlink(p))
        removed_l = sum(1 for p in logs[keep_logs:] if _safe_unlink(p))
        return removed_x, removed_l
    except Exception:
        return 0, 0


def list_recent_files(base: Path, keep_xlsx: int, keep_logs: int):
    xlsx = sorted(base.glob("*_respondido.xlsx"), key=lambda p: p.stat().st_mtime, reverse=True)[:keep_xlsx]
    logs = sorted(base.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)[:keep_logs]
    return xlsx, logs


# ── Rotas ──────────────────────────────────────────────────────────────────

@router.get("/recent.json")
async def recent_json(auth: bool = Depends(require_auth)):
    s = get_settings()
    xlsx, logs = list_recent_files(s.upload_dir, s.keep_xlsx, s.keep_logs)
    return {
        "xlsx": [{"name": f.name, "url": f"/downloads/{f.name}"} for f in xlsx],
        "logs": [{"name": f.name, "url": f"/downloads/{f.name}"} for f in logs],
    }


@router.post("/upload_stream")
async def upload_stream(
    auth: bool = Depends(require_auth),
    file: UploadFile = File(...),
    sheet: str = Form("Seguranca"),
    qcol: str = Form("Pergunta"),
    acol: str = Form("Resposta"),
):
    s = get_settings()
    filename = (file.filename or "").lower()

    if not filename.endswith(_ALLOWED_EXT):
        return JSONResponse(
            status_code=400,
            content={"erro": "Formato inválido", "detalhe": "⚠️ Somente arquivos .xlsx são permitidos."},
        )
    if file.content_type not in _ALLOWED_MIME:
        return JSONResponse(
            status_code=400,
            content={"erro": "MIME inválido", "detalhe": "⚠️ Tipo de arquivo não suportado."},
        )

    ts = br_now().strftime("%Y%m%d_%H%M%S")
    stem = Path(filename).stem
    upload_dir = s.upload_dir
    upload_dir.mkdir(parents=True, exist_ok=True)

    in_path = upload_dir / f"{stem}_{ts}.xlsx"
    out_path = upload_dir / f"{stem}_{ts}_respondido.xlsx"
    log_path = upload_dir / f"{stem}_{ts}.log"

    with in_path.open("wb") as buf:
        shutil.copyfileobj(file.file, buf)

    async def streamer():
        start = br_now()
        yield f"Iniciando às {start.strftime('%Y-%m-%d %H:%M:%S')} (BRT)...\n"

        # Executa o pipeline em subprocess (isolamento de memória para ML)
        excel_rag_path = s.wsl_dir / "excel_rag.py"
        cmd = [
            "python3", str(excel_rag_path),
            "answer",
            "--input", str(in_path),
            "--sheet", sheet,
            "--qcol", qcol,
            "--acol", acol,
            "--output", str(out_path),
        ]
        # Passa apenas variáveis necessárias (evita vazamento de secrets)
        safe_env_keys = {
            "PATH", "HOME", "PYTHONPATH",
            "OLLAMA_URL", "MODEL_NAME", "EMBED_MODEL", "USE_LOCAL_EMBEDDINGS",
            "HF_EMBED_MODEL", "EMBED_BATCH", "COLLECTION_NAME", "KNOWLEDGE_DIR",
            "VECTOR_DB_DIR", "TOP_K", "MIN_SIM", "RERANKER_MODEL",
            "MAX_TOKENS", "NUM_CTX", "TEMP", "TOP_P", "REPEAT_PENALTY",
            "NUM_THREADS", "OLLAMA_CONNECT_TIMEOUT", "OLLAMA_READ_TIMEOUT",
            "CHUNK_SIZE", "CHUNK_OVERLAP", "DOCKER_MODE",
        }
        filtered_env = {k: v for k, v in os.environ.items() if k in safe_env_keys}

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                env=filtered_env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            with open(log_path, "w", encoding="utf-8") as logf:
                while True:
                    line = await proc.stdout.readline()
                    if not line:
                        break
                    text = line.decode(errors="ignore")
                    logf.write(text)
                    logf.flush()
                    yield text

            rc = await proc.wait()
            end = br_now()
            elapsed = (end - start).total_seconds()
            yield f"\n[INFO] Início: {start.strftime('%Y-%m-%d %H:%M:%S')} (BRT)\n"
            yield f"[INFO] Fim:    {end.strftime('%Y-%m-%d %H:%M:%S')} (BRT)\n"
            yield f"[INFO] Tempo total: {elapsed:.2f}s ({elapsed/60:.2f} min)\n"

            if rc == 0:
                yield f"\n[OK] Baixar planilha: /downloads/{out_path.name}\n"
            else:
                yield f"\n[ERRO] Código de saída: {rc}. Veja o log.\n"

        except Exception as exc:
            yield f"\n[EXCEÇÃO] {exc}\n"
        finally:
            removed_x, removed_l = cleanup_upload_dir(upload_dir, s.keep_xlsx, s.keep_logs)
            yield (
                f"\n[CLEANUP] Mantidos últimos {s.keep_xlsx} xlsx e {s.keep_logs} logs. "
                f"Removidos: {removed_x} xlsx / {removed_l} logs.\n"
            )
            yield f"\n[LOG] /downloads/{log_path.name}\n"

    return StreamingResponse(streamer(), media_type="text/plain; charset=utf-8")
