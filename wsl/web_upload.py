# web_upload.py â€” entry point FastAPI (wrapper fino).
#
# Mantido para compatibilidade com docker-compose:
#   command: ["uvicorn","web_upload:app","--host","0.0.0.0","--port","8081"]
#
# Toda a lÃ³gica foi movida para interfaces/api/app.py.


from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

# Carrega .env antes de qualquer import de mÃ³dulo interno
load_dotenv(dotenv_path=Path(__file__).with_name("settings.env"), override=False)
load_dotenv(override=False)

from interfaces.api.app import create_app  # noqa: E402

app = create_app()


def br_now() -> datetime:
    try:
        return datetime.now(ZoneInfo("America/Sao_Paulo"))
    except Exception:
        return datetime.now()


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# LEGADO: funÃ§Ãµes mantidas para compatibilidade.
# Use interfaces/api/routes/upload.py para cÃ³digo novo.
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

