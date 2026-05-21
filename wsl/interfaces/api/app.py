"""
Factory da aplicação FastAPI.
Separa a criação do app da configuração de rotas,
permitindo instanciar o app em testes sem efeitos colaterais.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from config import get_settings
from core.logging import setup_logging, get_logger
from interfaces.api.auth import require_auth
from interfaces.api.routes.upload import router as upload_router, list_recent_files, cleanup_upload_dir

_TEMPLATE_PATH = Path(__file__).parent / "templates" / "index.html"

logger = get_logger("api.app")


def create_app() -> FastAPI:
    setup_logging()
    s = get_settings()

    app = FastAPI(
        title="CelIA",
        description="Agente inteligente para resposta de planilhas de compliance.",
        version="2.0.0",
    )

    # ── Assets (logos) servidos de /assets ────────────────────────────────
    assets_dir = Path("/app") / "assets" if s.docker_mode else Path(__file__).parents[4] / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    # ── Downloads servidos de /downloads ──────────────────────────────────
    upload_dir = s.upload_dir
    upload_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/downloads", StaticFiles(directory=str(upload_dir)), name="downloads")

    # ── Rotas de upload ────────────────────────────────────────────────────
    app.include_router(upload_router)

    # ── Página inicial ─────────────────────────────────────────────────────
    @app.get("/", response_class=HTMLResponse)
    async def index(auth: bool = Depends(require_auth)):
        cleanup_upload_dir(upload_dir, s.keep_xlsx, s.keep_logs)
        xlsx_files, log_files = list_recent_files(upload_dir, s.keep_xlsx, s.keep_logs)

        def li(p: Path) -> str:
            return f"<li><a href='/downloads/{p.name}' target='_blank'>{p.name}</a></li>"

        xlis = "".join(li(f) for f in xlsx_files) or "<li><em>Nenhum arquivo disponível.</em></li>"
        llis = "".join(li(f) for f in log_files) or "<li><em>Nenhum log disponível.</em></li>"

        html = _TEMPLATE_PATH.read_text(encoding="utf-8")
        html = html.replace('<ul id="recent-xlsx"><li><em>Carregando...</em></li></ul>',
                            f"<ul id='recent-xlsx'>{xlis}</ul>")
        html = html.replace('<ul id="recent-logs"><li><em>Carregando...</em></li></ul>',
                            f"<ul id='recent-logs'>{llis}</ul>")
        return HTMLResponse(html)

    logger.info("CelIA API inicializada.")
    return app
