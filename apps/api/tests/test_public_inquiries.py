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
                "email": "sales@example.com",
                "form": "contact",
                "inquiry_type": "sales",
                "name": "Sales Lead",
                "message": "General contact",
            },
            "website_contact",
            "high",
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
    result = MagicMock()
    result.lead = lead
    with patch(
        "porterchain_api.routers.public_inquiries._ingest.ingest",
        return_value=result,
    ) as ingest:
        res = client.post(
            "/v1/public/inquiries",
            headers={"X-Ingest-Key": "test-ingest-key"},
            json=payload,
        )
    assert res.status_code == 201
    assert res.json()["id"] == "lead-1"
    ingest.assert_called_once()
    event = ingest.call_args[0][1]
    assert event.source == expected_source
    assert event.priority == expected_priority
    assert event.email == payload["email"]


def test_public_inquiry_stores_full_phone_in_custom_fields_when_truncated(
    client: TestClient,
) -> None:
    long_phone = "+1 (416) 555-0100 ext. 204 extra digits"
    lead = MagicMock()
    lead.id = "lead-2"
    result = MagicMock()
    result.lead = lead
    with patch(
        "porterchain_api.routers.public_inquiries._ingest.ingest",
        return_value=result,
    ) as ingest:
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
    event = ingest.call_args[0][1]
    assert event.phone == long_phone
    assert event.custom_fields.get("phone_full") == long_phone


def test_public_inquiry_with_merchant_referral(client: TestClient) -> None:
    lead = MagicMock()
    lead.id = "lead-ref"
    result = MagicMock()
    result.lead = lead
    with patch(
        "porterchain_api.routers.public_inquiries._ingest.ingest",
        return_value=result,
    ) as ingest:
        res = client.post(
            "/v1/public/inquiries",
            headers={"X-Ingest-Key": "test-ingest-key"},
            json={
                "email": "referred@example.com",
                "form": "business",
                "intent": "quote",
                "referred_by_merchant_id": "merch_abc",
            },
        )
    assert res.status_code == 201
    event = ingest.call_args[0][1]
    assert event.referred_by_merchant_id == "merch_abc"
    assert event.channel == "merchant_referral"
    assert event.source == "merchant_referral"
