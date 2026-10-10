"""Lead fixes P1: unified inbox (reply, log call, bulk, CSV), sign-ups → leads,
newsletter double opt-in, inbound email, WhatsApp non-text parsing.
All outbound transports are stubbed — nothing leaves the test."""

from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

import porterchain_api.main  # noqa: F401
from porterchain_api.collaboration_engine import lead_inbox
from porterchain_api.collaboration_engine.lead_channel_adapters import (
    parse_prefill_tags,
    whatsapp_message_body,
)
from porterchain_api.collaboration_engine.lead_email_inbound import (
    InboundEmail,
    ingest_inbound_email,
    parse_rfc822,
    poll_imap_once,
    should_skip,
    strip_quoted,
)
from porterchain_api.collaboration_engine.lead_ingest_service import (
    CanonicalLeadEvent,
    LeadIngestService,
)
from porterchain_api.config import Settings, get_settings
from porterchain_api.crm_models import (
    CrmConversation,
    CrmConversationMessage,
    CrmLead,
)
from porterchain_api.main import create_app


def _settings(**over) -> Settings:
    base = dict(app_env="local", jwt_secret="t", stripe_mock=True)
    base.update(over)
    return Settings(**base)


def _lead(db, **over) -> CrmLead:
    suffix = uuid.uuid4().hex[:8]
    lead = CrmLead(
        company_name=f"Inbox Co {suffix}",
        email=f"inbox-{suffix}@acme.test",
        phone=None,
        source="website_contact",
        channel="website",
        status="new",
        priority="high",
        custom_fields={},
        consent={},
        tags=[],
        address={},
    )
    for k, v in over.items():
        setattr(lead, k, v)
    db.add(lead)
    db.commit()
    return lead


def _messages(db, lead_id: str) -> list[CrmConversationMessage]:
    return (
        db.query(CrmConversationMessage)
        .join(CrmConversation, CrmConversation.id == CrmConversationMessage.conversation_id)
        .filter(CrmConversation.lead_id == lead_id)
        .all()
    )


# --- 7. Inbox: inbound flips awaiting reply ---------------------------------
def test_inbound_message_marks_awaiting_reply(db) -> None:
    email = f"aw-{uuid.uuid4().hex[:8]}@acme.test"
    res = LeadIngestService().ingest(
        db,
        CanonicalLeadEvent(
            channel="website",
            source="website_contact",
            provider="website",
            external_event_id=f"t:{uuid.uuid4()}",
            company_name="Await Co",
            email=email,
            message="Can you do 40 deliveries a week?",
            seed_conversation=True,
            skip_outreach=True,
        ),
    )
    db.refresh(res.lead)
    assert res.lead.awaiting_reply is True
    assert res.lead.last_inbound_at is not None


# --- 7. Reply composer ---------------------------------------------------------
def test_reply_disabled_when_no_transport(db) -> None:
    lead = _lead(db)
    with pytest.raises(lead_inbox.ReplyError) as exc:
        lead_inbox.send_lead_reply(
            db, _settings(), lead, channel="email", body="Hi", subject=None, actor_id="adm"
        )
    assert exc.value.code == "email_reply_transport_not_configured"
    status = lead_inbox.reply_channels(_settings(), lead)
    assert status["email"]["enabled"] is False
    assert status["whatsapp"] == {"enabled": False, "reason": "whatsapp_cloud_disabled"}


def test_reply_email_via_zoho_smtp_records_thread(db) -> None:
    lead = _lead(db, awaiting_reply=True)
    s = _settings(
        lead_reply_email_transport="zoho_smtp",
        zoho_mail_user="sales@porterchain.com",
        zoho_mail_app_password="app-pass",
    )
    with patch.object(lead_inbox, "send_via_zoho_smtp", return_value=f"<{uuid.uuid4().hex}@porterchain.com>") as send:
        out = lead_inbox.send_lead_reply(
            db, s, lead, channel="email", body="Thanks — yes we can.", subject=None, actor_id="adm"
        )
    send.assert_called_once()
    assert send.call_args.kwargs["to"] == lead.email
    assert out["status"] == "sent"
    db.refresh(lead)
    assert lead.awaiting_reply is False
    assert lead.first_response_at is not None
    assert lead.status == "replied"
    outbound = [m for m in _messages(db, lead.id) if m.direction == "outbound"]
    assert outbound and outbound[0].channel == "email"


def test_reply_email_blocked_when_suppressed(db) -> None:
    lead = _lead(db)
    s = _settings(
        lead_reply_email_transport="zoho_smtp", zoho_mail_user="u", zoho_mail_app_password="p"
    )
    with (
        patch(
            "porterchain_api.collaboration_engine.lead_suppression.is_suppressed",
            return_value=True,
        ),
        patch.object(lead_inbox, "send_via_zoho_smtp") as send,
    ):
        with pytest.raises(lead_inbox.ReplyError) as exc:
            lead_inbox.send_lead_reply(
                db, s, lead, channel="email", body="Hi", subject=None, actor_id="adm"
            )
    assert exc.value.code == "suppressed"
    send.assert_not_called()


def test_reply_whatsapp_needs_flag_and_window(db) -> None:
    lead = _lead(
        db,
        channel="whatsapp",
        phone="+16476197951",
        custom_fields={"wa_id": "16475550100"},
        last_inbound_at=datetime.now(UTC) - timedelta(hours=30),
    )
    on = _settings(
        whatsapp_cloud_enabled=True, meta_wa_access_token="tok", meta_wa_phone_number_id="pn"
    )
    with patch(
        "porterchain_api.collaboration_engine.lead_whatsapp_cloud.whatsapp_cloud_configured",
        return_value=True,
    ):
        st = lead_inbox.whatsapp_channel_status(on, lead)
        assert st["enabled"] is False and st["reason"] == "outside_24h_service_window"
        lead.last_inbound_at = datetime.now(UTC) - timedelta(hours=1)
        db.commit()
        with patch(
            "porterchain_api.collaboration_engine.lead_whatsapp_cloud.send_whatsapp_text",
            return_value={"status": "sent", "to": "16475550100", "message_id": f"wamid.{uuid.uuid4().hex}"},
        ) as send:
            out = lead_inbox.send_lead_reply(
                db, on, lead, channel="whatsapp", body="On our way", subject=None, actor_id="adm"
            )
    send.assert_called_once()
    assert send.call_args.kwargs["phone"] == "16475550100"
    assert out["status"] == "sent"


# --- 7. Log a call / bulk / CSV --------------------------------------------------
def test_log_call_marks_responded_and_creates_callback_task(db) -> None:
    from porterchain_api.crm_models import CrmSalesTask

    lead = _lead(db, awaiting_reply=True)
    out = lead_inbox.log_call(
        db,
        lead,
        direction="outbound",
        outcome="callback",
        notes="Call Tue 10am",
        duration_minutes=4,
        actor_id="adm",
    )
    db.refresh(lead)
    assert lead.awaiting_reply is False
    assert lead.first_response_at is not None
    assert out["task_id"]
    assert db.get(CrmSalesTask, out["task_id"]).entity_id == lead.id
    calls = [m for m in _messages(db, lead.id) if m.channel == "phone_call"]
    assert calls and "callback" in calls[0].body


def test_log_call_rejects_unknown_outcome(db) -> None:
    lead = _lead(db)
    with pytest.raises(lead_inbox.ReplyError):
        lead_inbox.log_call(
            db, lead, direction="outbound", outcome="??", notes=None, duration_minutes=None, actor_id="a"
        )


def test_bulk_update_assign_and_status(db) -> None:
    a, b = _lead(db), _lead(db)
    out = lead_inbox.bulk_update(db, [a.id, b.id, "missing"], status="contacted", priority="low")
    assert out == {"updated": 2, "missing": 1}
    db.refresh(a)
    assert a.status == "replied" and a.priority == "low"
    with pytest.raises(lead_inbox.ReplyError):
        lead_inbox.bulk_update(db, [a.id], status="bogus")


def test_csv_export_neutralises_formulas(db) -> None:
    lead = _lead(db, company_name="=HYPERLINK(\"http://x\")")
    text = lead_inbox.leads_to_csv([lead])
    assert text.splitlines()[0].startswith("id,created_at,company_name")
    assert "'=HYPERLINK" in text


def test_list_filters_awaiting_reply_and_driver_view(db) -> None:
    from porterchain_api.collaboration_engine import CrmSalesService

    driver = _lead(db, intent_type="driver_partner", awaiting_reply=True)
    buyer = _lead(db, awaiting_reply=True)
    svc = CrmSalesService()
    drivers = {row.id for row in svc.list_leads(db, view="drivers", awaiting_reply=True, limit=500)}
    buyers = {row.id for row in svc.list_leads(db, view="buyers", awaiting_reply=True, limit=500)}
    assert driver.id in drivers and driver.id not in buyers
    assert buyer.id in buyers and buyer.id not in drivers


# --- 8. Sign-ups → leads ------------------------------------------------------------
def test_signups_link_to_existing_lead_and_drivers_separate(db) -> None:
    from porterchain_api.collaboration_engine.signup_leads import record_signup_lead

    existing = _lead(db)
    with patch("porterchain_api.platform.staff_notify.dispatch_staff_specs"):
        lid = record_signup_lead(
            db,
            kind="shopify_install",
            external_id=f"shop-{uuid.uuid4().hex[:6]}.myshopify.com",
            email=existing.email,
            company_name="Shop",
        )
        assert lid == existing.id  # deduped by email
        did = record_signup_lead(
            db,
            kind="driver_signup",
            external_id=f"user_{uuid.uuid4().hex[:6]}",
            email=f"drv-{uuid.uuid4().hex[:6]}@acme.test",
            contact_name="Dee River",
        )
    driver = db.get(CrmLead, did)
    assert driver.intent_type == "driver_partner"
    assert driver.channel == "driver_signup"


# --- 9. Newsletter double opt-in --------------------------------------------------
def test_newsletter_double_opt_in(db) -> None:
    from porterchain_api.collaboration_engine import newsletter_subscribers as subscribers

    email = f"nl-{uuid.uuid4().hex[:8]}@acme.test"
    events: list[dict] = []

    with patch(
        "porterchain_api.platform.bus.publish_domain_event",
        side_effect=lambda **kw: events.append(kw),
    ):
        row = subscribers.subscribe(db, email=email, website_url="https://porterchain.com", ip="1.2.3.4")
    assert row.status == "pending"
    assert [e["event_type"] for e in events] == ["newsletter.confirm_requested"]
    sent = {"context": events[0]["payload"]}
    # The event router turns it into exactly one transactional email to the subscriber.
    from porterchain_api.notification_engine.event_router import _specs_for_event

    specs = _specs_for_event("newsletter.confirm_requested", events[0]["payload"])
    assert [(s["template_key"], s["channel"], s["recipient_address"], s["category"]) for s in specs] == [
        ("newsletter_confirm", "email", email, "crm")
    ]
    token = sent["context"]["confirm_url"].split("token=")[1]
    assert db.query(CrmLead).filter(CrmLead.email == email).first() is None  # not a sales lead
    assert subscribers.confirm(db, token="x" * 20) is None
    done = subscribers.confirm(db, token=token, ip="1.2.3.4")
    assert done is not None and done.status == "confirmed"
    assert done.consent["marketing"] is True and done.consent["method"] == "double_opt_in"
    assert subscribers.confirm(db, token=token) is None  # single use


def test_newsletter_http_flow(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("PUBLIC_INGEST_API_KEY", "k")
    get_settings.cache_clear()
    client = TestClient(create_app())
    with patch("porterchain_api.collaboration_engine.newsletter_subscribers._send_confirm") as send:
        res = client.post(
            "/v1/public/newsletter/subscribe",
            headers={"X-Ingest-Key": "k"},
            json={"email": f"h-{uuid.uuid4().hex[:6]}@acme.test", "form_elapsed_ms": 5000},
        )
    assert res.status_code == 202
    send.assert_called_once()
    bad = client.post("/v1/public/newsletter/confirm", json={"token": "y" * 30})
    assert bad.status_code == 400
    get_settings.cache_clear()


# --- 10. Inbound email ----------------------------------------------------------------
def test_strip_quoted_and_skip_rules() -> None:
    assert strip_quoted("Sounds good\n\nOn Mon, Ravi wrote:\n> old") == "Sounds good"
    s = _settings()
    auto = InboundEmail("a@b.co", None, [], "x", "y", "<1>", {"Auto-Submitted": "auto-replied"})
    assert should_skip(auto, s) == "auto_reply"
    assert should_skip(InboundEmail("noreply@b.co", None, [], "", "", "<2>"), s) == "system_sender"
    assert should_skip(InboundEmail("sales@porterchain.com", None, [], "", "", "<3>"), s) == "own_address"


def test_inbound_email_threads_onto_existing_lead(db) -> None:
    lead = _lead(db)
    mid = f"<{uuid.uuid4().hex}@mail.acme.test>"
    msg = InboundEmail(lead.email, "Pat", ["sales@porterchain.com"], "Re: quote", "Yes please\n\nOn Mon wrote:\n> q", mid)
    with patch("porterchain_api.platform.staff_notify.dispatch_staff_specs"):
        out = ingest_inbound_email(db, _settings(), msg)
        again = ingest_inbound_email(db, _settings(), msg)
    assert out["lead_id"] == lead.id and out["created"] is False
    assert again["lead_id"] == lead.id
    db.refresh(lead)
    assert lead.awaiting_reply is True
    inbound = [m for m in _messages(db, lead.id) if m.channel == "email"]
    assert len(inbound) == 1  # idempotent on Message-ID
    assert inbound[0].body.startswith("Re: quote") and "> q" not in inbound[0].body


def test_imap_poll_uses_peek_and_marks_seen(db) -> None:
    raw = (
        f"From: Sam <sam-{uuid.uuid4().hex[:6]}@acme.test>\r\nTo: sales@porterchain.com\r\nSubject: Need a van\r\n"
        f"Message-ID: <{uuid.uuid4().hex}@acme.test>\r\n\r\nTomorrow 9am?\r\n"
    ).encode()
    parsed = parse_rfc822(raw)
    assert parsed.subject == "Need a van" and parsed.text.strip() == "Tomorrow 9am?"
    imap = MagicMock()
    imap.uid.side_effect = lambda cmd, *a: {
        "search": ("OK", [b"7"]),
        "fetch": ("OK", [(b"7 (BODY[] {1}", raw)]),
        "store": ("OK", [b""]),
    }[cmd]
    s = _settings(
        lead_inbound_imap_enabled=True, zoho_mail_user="sales@porterchain.com", zoho_mail_app_password="p"
    )
    with patch("porterchain_api.platform.staff_notify.dispatch_staff_specs"):
        out = poll_imap_once(db, s, imap_factory=lambda: imap)
    assert out["ingested"] == 1
    fetch_call = [c for c in imap.uid.call_args_list if c.args[0] == "fetch"][0]
    assert "PEEK" in fetch_call.args[2]
    assert any(c.args[0] == "store" for c in imap.uid.call_args_list)


def test_imap_poll_off_by_default(db) -> None:
    assert poll_imap_once(db, _settings())["fetched"] == 0


def test_inbound_email_webhook_requires_hmac(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("LEAD_INBOUND_EMAIL_SECRET", "whsec")
    get_settings.cache_clear()
    client = TestClient(create_app())
    body = json.dumps({"from": "noreply@x.co", "subject": "s", "text": "t", "message_id": "<z>"}).encode()
    bad = client.post("/v1/public/mail/inbound", content=body, headers={"X-PorterChain-Signature": "00"})
    assert bad.status_code == 401
    sig = hmac.new(b"whsec", body, hashlib.sha256).hexdigest()
    ok = client.post(
        "/v1/public/mail/inbound",
        content=body,
        headers={"X-PorterChain-Signature": sig, "Content-Type": "application/json"},
    )
    assert ok.status_code == 200 and ok.json()["status"] == "skipped"
    get_settings.cache_clear()


# --- 11. WhatsApp inbound parsing ---------------------------------------------------
@pytest.mark.parametrize(
    ("msg", "expect"),
    [
        ({"type": "image", "image": {"id": "m1", "caption": "damaged box"}}, "[image] damaged box"),
        (
            {"type": "document", "document": {"id": "d1", "filename": "manifest.pdf"}},
            "[document: manifest.pdf]",
        ),
        (
            {"type": "location", "location": {"latitude": 43.6, "longitude": -79.4, "name": "Dock 4"}},
            "[location] Dock 4 (43.6,-79.4)",
        ),
        (
            {"type": "interactive", "interactive": {"button_reply": {"id": "q", "title": "Get quote"}}},
            "Get quote",
        ),
        ({"type": "reaction", "reaction": {"emoji": "👍"}}, ""),
    ],
)
def test_whatsapp_non_text_bodies(msg: dict, expect: str) -> None:
    body, meta = whatsapp_message_body(msg)
    assert body == expect
    assert meta["wa_type"] == msg["type"]


def test_whatsapp_prefill_tags() -> None:
    tags = parse_prefill_tags(
        "Hi PorterChain\nutm_source=site&utm_medium=fab&utm_campaign=gta_q4\npage=/en/pricing\nclaim=pcv-12345678"
    )
    assert tags == {
        "utm_source": "site",
        "utm_medium": "fab",
        "utm_campaign": "gta_q4",
        "landing_page": "/en/pricing",
        "visitor_claim": "pcv-12345678",
    }
