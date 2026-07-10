"""Public inquiry ingest → CRM leads."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from porterchain_api.config import Settings, get_settings
from porterchain_api.main import create_app


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("PUBLIC_INGEST_API_KEY", "test-ingest-key")
    get_settings.cache_clear()
    app = create_app()
    yield TestClient(app)
    get_settings.cache_clear()


def test_public_inquiry_rejects_wrong_ingest_key(client: TestClient) -> None:
    res = client.post(
        "/v1/public/inquiries",
        headers={"X-Ingest-Key": "wrong-key"},
        json={"email": "ops@example.com", "company_name": "Acme", "intent": "quote"},
    )
    assert res.status_code == 401


def test_public_inquiry_creates_lead(client: TestClient) -> None:
    lead = MagicMock()
    lead.id = "lead-1"
    with patch("porterchain_api.routers.public_inquiries._crm.create_lead", return_value=lead) as create:
        res = client.post(
            "/v1/public/inquiries",
            headers={"X-Ingest-Key": "test-ingest-key"},
            json={
                "email": "ops@example.com",
                "company_name": "Acme Logistics",
                "intent": "quote",
                "form": "contact",
            },
        )
    assert res.status_code == 201
    assert res.json()["id"] == "lead-1"
    create.assert_called_once()
