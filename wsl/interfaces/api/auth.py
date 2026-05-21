"""Autenticação HTTP Basic para a API."""
from __future__ import annotations

import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from config import get_settings
from core.exceptions import AuthenticationError

_security = HTTPBasic()


def require_auth(credentials: HTTPBasicCredentials = Depends(_security)) -> bool:
    s = get_settings()
    ok_user = secrets.compare_digest(credentials.username.encode(), s.uploader_user.encode())
    ok_pass = secrets.compare_digest(credentials.password.encode(), s.uploader_password.encode())
    if not (ok_user and ok_pass):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas",
            headers={"WWW-Authenticate": "Basic"},
        )
    return True
