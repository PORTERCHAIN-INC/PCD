"""Lead fixes P0: CASL form consent, hot-lead alerts, booking conversion,
form spam guard, webhook secrets. No real messages leave the test."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

import porterchain_api.main  # noqa: F401 — registers ORM models
from porterchain_api.collaboration_engine.lead_consent import (
    CASL_FORM_TEXT,
    CASL_FORM_TEXT_VERSION,
    casl_evidence,
    form_consent_evidence,
)
from porterchain_api.collaboration_engine.lead_suppression import merge_consent_safe
from porterchain_api.config import get_settings
from porterchain_api.crm_models import CrmLead
from porterchain_api.main import create_app
from porterchain_api.marketing_site import rate_limit as rl
from porterchain_api.platform.secret_compare import secrets_match


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("PUBLIC_INGEST_API_KEY", "test-ingest-key")
    get_settings.cache_clear()
    yield TestClient(create_app())
    get_settings.cache_clear()


H = {"X-Ingest-Key": "test-ingest-key", "X-Forwarded-For": "198.51.100.7"}


def _fake_ingest():
    lead = MagicMock()
    lead.id = "lead-x"
    result = MagicMock()
    result.lead = lead
    return result


# --- 1. CASL ---------------------------------------------------------------
def test_cookie_banner_marketing_is_not_email_consent() -> None:
    out = casl_evidence(
        {"marketing": True, "analytics": True, "source": "website_cmp"}, source="website_inquiry"
    )
    assert out.get("marketing") is not True
    assert out.get("analytics") is True


def test_form_consent_records_text_version_time_ip_source() -> None:
    ev = form_consent_evidence(
        marketing=True, source="website_contact", ip="198.51.100.7", locale="fr", page="/fr/contact"
    )
    assert ev["marketing"] is True
    assert ev["text_version"] == CASL_FORM_TEXT_VERSION
    assert ev["text"] == CASL_FORM_TEXT["fr"]
    assert ev["ip"] == "198.51.100.7"
    assert ev["source"] == "website_contact"
    assert ev["captured_at"]
    assert ev["method"] == "form_checkbox"


def test_unticked_box_never_withdraws_prior_consent() -> None:
    db = MagicMock()
    with patch(
        "porterchain_api.collaboration_engine.lead_suppression.is_suppressed", return_value=False
    ):
        merged = merge_consent_safe(
            {"marketing": True, "text_version": "casl_v1_marketing"},
            form_consent_evidence(marketing=False, source="website_contact"),
            db=db,
            email="a@b.co",
            phone=None,
        )
    assert merged["marketing"] is True


def test_inquiry_uses_form_checkbox_and_ignores_cmp(client: TestClient) -> None:
    with patch(
        "porterchain_api.routers.public_inquiries._ingest.ingest", return_value=_fake_ingest()
    ) as ingest:
        res = client.post(
            "/v1/public/inquiries",
            headers=H,
            json={
                "email": "ops@acme.test",
                "form": "contact",
                "marketing_consent": False,
                "consent": {"marketing": True, "source": "website_cmp"},
                "form_elapsed_ms": 9000,
            },
        )
    assert res.status_code == 201
    consent = ingest.call_args[0][1].consent
    assert consent["marketing"] is False
    assert consent["ip"] == "198.51.100.7"
    assert consent["text_version"] == CASL_FORM_TEXT_VERSION


def test_vehicle_partner_consent_is_persisted(client: TestClient) -> None:
    with patch(
        "porterchain_api.routers.public_inquiries._ingest.ingest", return_value=_fake_ingest()
    ) as ingest:
        res = client.post(
            "/v1/public/inquiries",
            headers=H,
            json={
                "email": "driver@acme.test",
                "intent": "driver_partner",
                "form": "vehicle_partner",
                "contact_consent": True,
                "marketing_consent": True,
                "form_elapsed_ms": 9000,
            },
        )
    assert res.status_code == 201
    consent = ingest.call_args[0][1].consent
    assert consent["contact_consent"] is True
    assert consent["marketing"] is True
    assert consent["source"] == "website_vehicle_partner"


# --- 2. Priority + alerts -----------------------------------------------------
def test_sales_contact_inquiry_is_high(client: TestClient) -> None:
    with patch(
        "porterchain_api.routers.public_inquiries._ingest.ingest", return_value=_fake_ingest()
    ) as ingest:
        client.post(
            "/v1/public/inquiries",
            headers=H,
            json={"email": "s@acme.test", "form": "contact", "inquiry_type": "sales"},
        )
    assert ingest.call_args[0][1].priority == "high"


def test_hot_lead_alerts_owner_and_team_once_per_day() -> None:
    from porterchain_api.collaboration_engine.lead_ops import notify_hot_lead

    lead = CrmLead(
        id=str(uuid.uuid4()),
        company_name="Acme",
        priority="high",
        status="new",
        assigned_to="adm-owner",
        source="website_calculator",
        channel="website",
        custom_fields={},
    )
    with patch("porterchain_api.platform.staff_notify.dispatch_staff_specs") as dispatch:
        assert notify_hot_lead(MagicMock(), lead, created=True) is True
        assert notify_hot_lead(MagicMock(), lead, created=False) is False  # deduped today
    specs = dispatch.call_args[0][1]
    recipients = {s["recipient_id"] for s in specs}
    assert "adm-owner" in recipients
    assert any(r.startswith("__staff:") for r in recipients)
    assert {s["channel"] for s in specs} == {"in_app", "push", "email"}
    # Mobile-first: the email goes to the owner only, never to the whole team.
    assert {s["recipient_id"] for s in specs if s["channel"] == "email"} == {"adm-owner"}
    assert all(s["recipient_type"] == "admin" for s in specs)


def test_medium_lead_does_not_page() -> None:
    from porterchain_api.collaboration_engine.lead_ops import notify_hot_lead

    lead = CrmLead(id="x", company_name="A", priority="medium", status="new", custom_fields={})
    with patch("porterchain_api.platform.staff_notify.dispatch_staff_specs") as dispatch:
        assert notify_hot_lead(MagicMock(), lead, created=True) is False
    dispatch.assert_not_called()


def test_calculator_lead_is_high_priority(db) -> None:
    from porterchain_api.marketing_site.lead_service import submit_calculator_lead
    from porterchain_api.marketing_site.schemas import CalculatorLeadRequest

    email = f"calc-{uuid.uuid4().hex[:8]}@acme.test"
    with (
        patch("porterchain_api.platform.staff_notify.dispatch_staff_specs"),
        patch("porterchain_api.collaboration_engine.lead_nurture.apply_nurture_after_ingest"),
    ):
        out = submit_calculator_lead(
            db,
            CalculatorLeadRequest(
                business_name="Calc Co",
                email=email,
                phone=f"+1 416 {uuid.uuid4().int % 900 + 100} {uuid.uuid4().int % 9000 + 1000}",
                industry="pharmacy",
                monthly_volume="21-100",
                marketing_consent=True,
                form_elapsed_ms=8000,
            ),
            ip="203.0.113.5",
        )
    lead = db.get(CrmLead, out["lead_id"])
    assert lead is not None
    assert lead.priority == "high"
    assert lead.consent["ip"] == "203.0.113.5"
    assert lead.consent["text_version"] == CASL_FORM_TEXT_VERSION


# --- 3. Paid booking -> converted --------------------------------------------
def test_paid_booking_marks_lead_converted(db) -> None:
    from porterchain_api.collaboration_engine.booking_lead_mirror import (
        mark_booking_lead_converted,
    )

    quote_id = str(uuid.uuid4())
    order_id = str(uuid.uuid4())
    lead = CrmLead(
        company_name="123 King St W, Toronto",
        email=f"retail-{uuid.uuid4().hex[:6]}@acme.test",
        source="website_booking",
        channel="website_booking",
        status="new",
        quote_id=quote_id,
        awaiting_reply=True,
        custom_fields={"pickup": {"formatted_address": "123 King St W, Toronto"}},
        tags=["booking_started"],
    )
    db.add(lead)
    db.commit()
    out = mark_booking_lead_converted(db, quote_id=quote_id, order_id=order_id, email=lead.email)
    db.commit()
    assert out is not None
    db.refresh(lead)
    assert lead.status == "won"
    assert lead.order_id == order_id
    assert lead.awaiting_reply is False
    assert lead.company_name == lead.email  # not the pickup address any more
    assert "paid" in lead.tags


# --- 4. Spam guard -------------------------------------------------------------
def test_inquiry_honeypot_drops_silently(client: TestClient) -> None:
    with patch("porterchain_api.routers.public_inquiries._ingest.ingest") as ingest:
        res = client.post(
            "/v1/public/inquiries",
            headers=H,
            json={"email": "bot@spam.test", "website": "http://spam", "form_elapsed_ms": 9000},
        )
    assert res.status_code == 201
    ingest.assert_not_called()


def test_inquiry_too_fast_drops_silently(client: TestClient) -> None:
    with patch("porterchain_api.routers.public_inquiries._ingest.ingest") as ingest:
        res = client.post(
            "/v1/public/inquiries", headers=H, json={"email": "f@spam.test", "form_elapsed_ms": 300}
        )
    assert res.status_code == 201
    ingest.assert_not_called()


def test_inquiry_rate_limited(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(rl, "check_fixed_window", lambda key, limit, **_: (False, limit + 1, None))
    res = client.post("/v1/public/inquiries", headers=H, json={"email": "r@acme.test"})
    assert res.status_code == 429


def test_newsletter_endpoint_rate_limited(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(rl, "check_fixed_window", lambda key, limit, **_: (False, limit + 1, None))
    res = client.post("/v1/public/newsletter/subscribe", headers=H, json={"email": "n@acme.test"})
    assert res.status_code == 429


# --- 6. Webhook secrets ----------------------------------------------------------
def test_secrets_match_is_strict() -> None:
    assert secrets_match("abc", "abc")
    assert not secrets_match("abc", "abd")
    assert not secrets_match("", "")
    assert not secrets_match(None, "abc")


def test_zeptomail_webhook_requires_secret(client: TestClient, monkeypatch) -> None:
    monkeypatch.setenv("ZEPTOMAIL_WEBHOOK_SECRET", "")
    get_settings.cache_clear()
    res = client.post("/v1/public/mail/zeptomail", json={"event_name": ["hardbounce"]})
    assert res.status_code == 503
    monkeypatch.setenv("ZEPTOMAIL_WEBHOOK_SECRET", "s3cret")
    get_settings.cache_clear()
    bad = client.post(
        "/v1/public/mail/zeptomail",
        json={"event_name": ["hardbounce"]},
        headers={"X-PorterChain-Mail-Webhook": "nope"},
    )
    assert bad.status_code == 401
