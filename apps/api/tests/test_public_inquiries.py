"""Public inquiry ingest → CRM leads."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from porterchain_api.config import get_settings
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


@pytest.mark.parametrize(
    ("payload", "expected_source", "expected_priority"),
    [
        (
            {
                "email": "ops@example.com",
                "intent": "quote",
                "form": "contact",
                "name": "Pat",
                "message": "Need a quote",
            },
            "website_quote",
            "high",
        ),
        (
            {
                "email": "demo@example.com",
                "intent": "demo",
                "form": "contact",
                "name": "Demo User",
            },
            "website_demo",
            "high",
        ),
        (
            {
                "email": "biz@acme.com",
                "phone": "+1 416-555-0100",
                "intent": "quote",
                "form": "business",
                "message": "Business inquiry",
            },
            "website_business",
            "high",
        ),
        (
            {
                "email": "reader@example.com",
                "form": "newsletter",
                "inquiry_type": "newsletter",
                "message": "Blog newsletter",
            },
            "website_newsletter",
            "low",
        ),
        (
            {
                "email": "sales@example.com",
                "form": "contact",
                "inquiry_type": "sales",
                "name": "Sales Lead",
                "message": "General contact",
            },
            "website_contact",
            "medium",
        ),
        (
            {
                "email": "driver@example.com",
                "phone": "+1 416-555-0199",
                "name": "Alex Driver",
                "intent": "driver_partner",
                "form": "vehicle_partner",
                "message": "Vehicle: van\nService area: GTA",
            },
            "website_driver_partner",
            "high",
        ),
        (
            {
                "email": "partner@example.com",
                "form": "contact",
                "inquiry_type": "partnership",
                "source_page": "vehicle-partner",
                "name": "Fleet Owner",
                "message": "Interested in partnering",
            },
            "website_driver_partner",
            "medium",
        ),
    ],
)
def test_public_inquiry_creates_lead_with_source_and_priority(
    client: TestClient,
    payload: dict,
    expected_source: str,
    expected_priority: str,
) -> None:
    lead = MagicMock()
    lead.id = "lead-1"
    with patch(
        "porterchain_api.routers.public_inquiries._crm.create_lead",
        return_value=lead,
    ) as create:
        res = client.post(
            "/v1/public/inquiries",
            headers={"X-Ingest-Key": "test-ingest-key"},
            json=payload,
        )
    assert res.status_code == 201
    assert res.json()["id"] == "lead-1"
    create.assert_called_once()
    lead_data = create.call_args[0][2]
    assert lead_data["source"] == expected_source
    assert lead_data["priority"] == expected_priority
    assert lead_data["email"] == payload["email"]


def test_public_inquiry_stores_full_phone_in_custom_fields_when_truncated(
    client: TestClient,
) -> None:
    long_phone = "+1 (416) 555-0100 ext. 204 extra digits"
    lead = MagicMock()
    lead.id = "lead-2"
    with patch(
        "porterchain_api.routers.public_inquiries._crm.create_lead",
        return_value=lead,
    ) as create:
        res = client.post(
            "/v1/public/inquiries",
            headers={"X-Ingest-Key": "test-ingest-key"},
            json={
                "email": "ops@example.com",
                "phone": long_phone,
                "form": "business",
                "intent": "quote",
            },
        )
    assert res.status_code == 201
    lead_data = create.call_args[0][2]
    assert lead_data["phone"] == long_phone[:32]
    assert lead_data["custom_fields"]["phone_full"] == long_phone
