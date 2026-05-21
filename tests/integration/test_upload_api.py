"""Testes de integração da API FastAPI."""
from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import MagicMock, patch

import openpyxl
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def api_client(test_settings):
    """Cliente de teste com autenticação configurada."""
    with patch("config.get_settings", return_value=test_settings):
        from interfaces.api.app import create_app
        app = create_app()
    return TestClient(app, auth=(test_settings.uploader_user, test_settings.uploader_password))


@pytest.fixture(scope="module")
def api_client_no_auth(test_settings):
    with patch("config.get_settings", return_value=test_settings):
        from interfaces.api.app import create_app
        app = create_app()
    return TestClient(app, raise_server_exceptions=False)


def test_index_returns_html(api_client):
    resp = api_client.get("/")
    assert resp.status_code == 200
    assert "CelIA" in resp.text
    assert "text/html" in resp.headers["content-type"]


def test_index_requires_auth(api_client_no_auth):
    resp = api_client_no_auth.get("/")
    assert resp.status_code == 401


def test_recent_json_returns_structure(api_client):
    resp = api_client.get("/recent.json")
    assert resp.status_code == 200
    data = resp.json()
    assert "xlsx" in data
    assert "logs" in data
    assert isinstance(data["xlsx"], list)
    assert isinstance(data["logs"], list)


def test_upload_rejects_non_xlsx(api_client):
    fake_csv = io.BytesIO(b"col1,col2\nval1,val2")
    resp = api_client.post(
        "/upload_stream",
        files={"file": ("data.csv", fake_csv, "text/csv")},
        data={"sheet": "Sheet1", "qcol": "Q", "acol": "A"},
    )
    assert resp.status_code == 400
    body = resp.json()
    assert "erro" in body


def test_upload_rejects_wrong_mime(api_client):
    fake_xlsx = io.BytesIO(b"not really xlsx")
    resp = api_client.post(
        "/upload_stream",
        files={"file": ("data.xlsx", fake_xlsx, "text/plain")},
        data={"sheet": "Sheet1", "qcol": "Q", "acol": "A"},
    )
    assert resp.status_code == 400
