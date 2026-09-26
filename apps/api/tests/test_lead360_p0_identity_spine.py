"""P0 Lead360 identity spine — visitor stamp, inquiry consent, booking mirror."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from porterchain_api.booking_engine.crm_lead_mirror import mirror_booking_lead_to_crm
from porterchain_api.booking_models import Lead, Quote, VisitorSession
from porterchain_api.collaboration_engine.lead_ingest_service import (
    CanonicalLeadEvent,
    LeadIngestService,
)
from porterchain_api.config import get_settings
from porterchain_api.crm_models import CrmLead
from porterchain_api.main import create_app


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("PUBLIC_INGEST_API_KEY", "test-ingest-key")
    get_settings.cache_clear()
    app = create_app()
    yield TestClient(app)
    get_settings.cache_clear()


def test_public_inquiry_stamps_visitor_and_consent(client: TestClient) -> None:
    lead = MagicMock()
    lead.id = "lead-vis-1"
    result = MagicMock()
    result.lead = lead
    with (
        patch(
            "porterchain_api.routers.public_inquiries._ingest.ingest",
            return_value=result,
        ) as ingest,
        patch(
            "porterchain_api.routers.public_inquiries._visitors.ensure_session",
        ) as ensure,
    ):
        res = client.post(
            "/v1/public/inquiries",
            headers={"X-Ingest-Key": "test-ingest-key"},
            json={
                "email": "ops@example.com",
                "form": "contact",
                "intent": "quote",
                "visitor_id": "pc-vid-aabbccdd-001",
                "consent": {"marketing": True, "sms": False},
            },
        )
    assert res.status_code == 201
    ensure.assert_called_once()
    assert ensure.call_args.kwargs["session_id"] == "pc-vid-aabbccdd-001"
    event = ingest.call_args[0][1]
    assert event.custom_fields.get("visitor_id") == "pc-vid-aabbccdd-001"
    assert event.external_ids.get("visitor_session") == "pc-vid-aabbccdd-001"
    assert event.consent.get("marketing") is True
    assert event.consent.get("sms") is False


def test_newsletter_inquiry_defaults_marketing_consent(client: TestClient) -> None:
    lead = MagicMock()
    lead.id = "lead-nl-1"
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
                "email": "reader@example.com",
                "form": "newsletter",
                "inquiry_type": "newsletter",
            },
        )
    assert res.status_code == 201
    event = ingest.call_args[0][1]
    assert event.consent.get("marketing") is True


def test_ingest_stamps_visitor_session_id_column(db) -> None:
    svc = LeadIngestService()
    suffix = uuid.uuid4().hex[:8]
    vid = f"vid-{suffix}"
    db.add(VisitorSession(id=vid))
    db.commit()
    email = f"vis-{suffix}@acme.test"
    result = svc.ingest(
        db,
        CanonicalLeadEvent(
            channel="website",
            source="website_contact",
            provider="test",
            external_event_id=f"evt-vis-{suffix}",
            company_name=f"Visitor Co {suffix}",
            email=email,
            custom_fields={"visitor_id": vid, "form": "contact"},
            external_ids={"visitor_session": vid},
            consent={"marketing": True},
        ),
    )
    assert result.created is True
    assert result.lead.visitor_session_id == vid
    assert result.lead.consent.get("marketing") is True
    assert (result.lead.custom_fields or {}).get("visitor_id") == vid


def test_mirror_booking_bidirectional_and_consent(db) -> None:
    from datetime import datetime, timedelta, timezone

    suffix = uuid.uuid4().hex[:8]
    quote_id = str(uuid.uuid4())
    customer_id = str(uuid.uuid4())
    vid = f"book-{suffix}"
    now = datetime.now(timezone.utc)
    db.add(VisitorSession(id=vid))
    quote = Quote(
        id=quote_id,
        amount_cents=5000,
        currency="cad",
        state="QUOTE",
        vehicle_class="cargo_van",
        package_type="parcel",
        visitor_session_id=vid,
        email=f"book-{suffix}@test.example",
        consent={"terms_accepted": True, "privacy_accepted": True, "marketing": True},
        pickup={"formatted_address": "100 King St W, Toronto"},
        dropoff={"formatted_address": "200 Bay St, Toronto"},
        pricing_breakdown={},
        scheduled_at=now,
        expires_at=now + timedelta(hours=24),
    )
    db.add(quote)
    db.commit()

    phone = f"+1416{int(suffix[:7], 16) % 10_000_000:07d}"
    crm = mirror_booking_lead_to_crm(
        db,
        email=f"book-{suffix}@test.example",
        phone=phone,
        quote_id=quote_id,
        customer_id=customer_id,
        stage="booking_started",
        visitor_session_id=vid,
        consent=quote.consent,
    )
    assert crm is not None
    assert crm.quote_id == quote_id
    assert crm.visitor_session_id == vid
    assert crm.consent.get("marketing") is True
    assert crm.consent.get("terms_accepted") is True

    retail = Lead(
        source="website_booking",
        email=f"book-{suffix}@test.example",
        quote_id=quote_id,
        customer_id=None,
        stage="booking_started",
        crm_lead_id=crm.id,
    )
    db.add(retail)
    db.commit()

    again = mirror_booking_lead_to_crm(
        db,
        email=f"book-{suffix}@test.example",
        phone=phone,
        quote_id=quote_id,
        customer_id=customer_id,
        stage="booking_started",
        visitor_session_id=vid,
        consent={"marketing": True, "sms": True},
    )
    assert again is not None
    assert again.id == crm.id
    db.refresh(again)
    assert again.consent.get("sms") is True

    linked = db.query(Lead).filter(Lead.quote_id == quote_id).first()
    assert linked is not None
    assert linked.crm_lead_id == crm.id
