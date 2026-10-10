"""Lead desk round 2: instant quote, fit score, drafts, 5-stage pipeline,
lost reasons, speed dashboard, mobile-first owner alerts.

Every transport is stubbed — nothing leaves the test, and nothing here sends
without an explicit reply call (which is itself stubbed)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

import porterchain_api.main  # noqa: F401
from porterchain_api.collaboration_engine import lead_inbox
from porterchain_api.collaboration_engine.booking_lead_mirror import (
    mark_booking_lead_converted,
)
from porterchain_api.config import Settings
from porterchain_api.crm_models import CrmLead
from porterchain_api.domain.crm_states import LeadStatus, normalize_lead_status
from porterchain_api.lead_desk import draft as draft_mod
from porterchain_api.lead_desk.draft import build_draft
from porterchain_api.lead_desk.fit_score import fit_score
from porterchain_api.lead_desk.quote import QuoteUnavailable, lead_quote
from porterchain_api.lead_desk.speed import speed_window, weekly_summary


@pytest.fixture
def admin_client(db, monkeypatch):
    import porterchain_api.routers.admin.leads_desk as desk_mod

    # Same as the other admin lead suites: RBAC tuples are covered elsewhere.
    monkeypatch.setattr(desk_mod, "require_module", lambda ctx, module: None)
    from porterchain_api.admin_engine.rbac import AdminContext, parse_admin_role
    from porterchain_api.admin_models import AdminUser
    from porterchain_api.auth.admin import get_admin_context
    from porterchain_api.db import get_db
    from porterchain_api.main import app
    from porterchain_api.user_models import PorterchainUser

    db.merge(
        PorterchainUser(
            id="user-desk-r2",
            clerk_user_id="clerk-desk",
            email="desk@porterchain.com",
            role="super_admin",
            status="active",
        )
    )
    db.flush()
    admin = AdminContext(
        user=AdminUser(
            clerk_user_id="clerk-desk",
            email="desk@porterchain.com",
            role="super_admin",
            porterchain_user_id="user-desk-r2",
        ),
        role=parse_admin_role("super_admin"),
    )
    app.dependency_overrides[get_admin_context] = lambda: admin
    app.dependency_overrides[get_db] = lambda: db
    yield TestClient(app)
    app.dependency_overrides.clear()


def _settings(**over) -> Settings:
    base = dict(app_env="local", jwt_secret="t", stripe_mock=True)
    base.update(over)
    return Settings(**base)


def _lead(db, **over) -> CrmLead:
    s = uuid.uuid4().hex[:8]
    lead = CrmLead(
        company_name=f"Desk Co {s}",
        email=f"desk-{s}@acme.test",
        phone="4165550123",
        source="website_calculator",
        channel="website",
        status="new",
        priority="high",
        industry="pharmacy",
        estimated_deliveries_per_month=60,
        custom_fields={
            "form": "calculator",
            "pickup_fsa": "M5V",
            "dropoff_fsa": "M4C",
            "estimate_cents": 2450,
        },
        consent={},
        tags=["calculator"],
        address={},
    )
    for k, v in over.items():
        setattr(lead, k, v)
    db.add(lead)
    db.commit()
    return lead


# --- 4. Pipeline ----------------------------------------------------------------
def test_five_stage_pipeline_and_legacy_names() -> None:
    assert [s.value for s in LeadStatus][:5] == [
        "new",
        "replied",
        "quoted",
        "won",
        "lost",
    ]
    assert (
        LeadStatus.CONTACTED is LeadStatus.REPLIED
        and LeadStatus.CONVERTED is LeadStatus.WON
    )
    assert normalize_lead_status("converted") == "won"
    assert normalize_lead_status("unqualified") == "lost"
    assert normalize_lead_status("quoted") == "quoted"


def test_reply_with_quote_moves_to_quoted(db) -> None:
    lead = _lead(db)
    s = _settings(
        lead_reply_email_transport="zoho_smtp",
        zoho_mail_user="u",
        zoho_mail_app_password="p",
    )
    quote = lead_quote(db, lead, website_url="https://porterchain.com")
    with patch.object(
        lead_inbox, "send_via_zoho_smtp", return_value=f"<{uuid.uuid4().hex}@x>"
    ) as send:
        lead_inbox.send_lead_reply(
            db,
            s,
            lead,
            channel="email",
            body="Quote",
            subject=None,
            actor_id="adm",
            quote=quote,
        )
    send.assert_called_once()
    db.refresh(lead)
    assert (
        lead.status == "quoted"
        and lead.quoted_at is not None
        and lead.first_response_at is not None
    )
    assert lead.custom_fields["last_quote"]["amount_cents"] == quote["amount_cents"]


def test_plain_reply_moves_new_to_replied_never_backwards(db) -> None:
    lead = _lead(db, status="quoted", quoted_at=datetime.now(UTC))
    s = _settings(
        lead_reply_email_transport="zoho_smtp",
        zoho_mail_user="u",
        zoho_mail_app_password="p",
    )
    with patch.object(
        lead_inbox, "send_via_zoho_smtp", return_value=f"<{uuid.uuid4().hex}@x>"
    ):
        lead_inbox.send_lead_reply(
            db, s, lead, channel="email", body="Hi", subject=None, actor_id="adm"
        )
    db.refresh(lead)
    assert lead.status == "quoted"


def test_booking_by_email_marks_quoted_lead_won(db) -> None:
    lead = _lead(db, status="quoted", quoted_at=datetime.now(UTC))
    out = mark_booking_lead_converted(
        db,
        quote_id=str(uuid.uuid4()),
        order_id=str(uuid.uuid4()),
        email=lead.email.upper(),
    )
    assert out is not None and out.id == lead.id
    assert out.status == "won" and out.won_at is not None and out.order_id


def test_lost_reason_one_tap(admin_client, db) -> None:
    lead = _lead(db)
    bad = admin_client.post(f"/v1/admin/leads/{lead.id}/lost", json={"reason": "meh"})
    assert bad.status_code == 422
    res = admin_client.post(f"/v1/admin/leads/{lead.id}/lost", json={"reason": "price"})
    assert res.status_code == 200, res.text
    db.refresh(lead)
    assert (lead.status, lead.lost_reason) == (
        "lost",
        "price",
    ) and lead.lost_at is not None


# --- 1. Instant quote --------------------------------------------------------------
def test_quote_uses_pricing_service_retail_vs_merchant(db) -> None:
    lead = _lead(db)
    q = lead_quote(db, lead, website_url="https://porterchain.com")
    assert q["pricing"] == "retail" and q["amount_cents"] > 0
    assert (
        q["booking_url"].startswith("https://porterchain.com/en/book?")
        and lead.id in q["booking_url"]
    )
    with patch("porterchain_pricing.PricingService.calculate_merchant") as merch:
        merch.return_value = SimpleNamespace(final_cents=5000, items=[], metadata={})
        lead.custom_fields = {**lead.custom_fields, "merchant_id": "m-1"}
        m = lead_quote(db, lead, website_url="https://porterchain.com")
    merch.assert_called_once()
    assert m["pricing"] == "merchant" and m["amount_cents"] == 5000


def test_quote_unavailable_without_postal_or_outside_area(db) -> None:
    lead = _lead(db, custom_fields={})
    try:
        lead_quote(db, lead, website_url="x")
        raise AssertionError("expected QuoteUnavailable")
    except QuoteUnavailable as exc:
        assert str(exc) == "no_postal_code"
    lead.custom_fields = {"pickup_fsa": "V6B"}  # Vancouver
    try:
        lead_quote(db, lead, website_url="x")
        raise AssertionError("expected QuoteUnavailable")
    except QuoteUnavailable as exc:
        assert str(exc) == "outside_service_area"


def test_quote_and_draft_endpoints(admin_client, db) -> None:
    lead = _lead(db)
    q = admin_client.get(f"/v1/admin/leads/{lead.id}/quote").json()
    assert q["available"] is True and q["amount_display"].startswith("$")
    d = admin_client.get(
        f"/v1/admin/leads/{lead.id}/draft", params={"channel": "whatsapp"}
    ).json()
    assert (
        d["channel"] == "whatsapp"
        and q["amount_display"] in d["body"]
        and d["source"] == "template"
    )
    sc = admin_client.get(f"/v1/admin/leads/{lead.id}/score").json()
    assert 0 <= sc["score"] <= 100 and sc["reasons"]


# --- 2. Fit score ---------------------------------------------------------------------
def _duck(**kw):
    base = dict(
        custom_fields={},
        tags=[],
        industry=None,
        business_type=None,
        company_name="X",
        source="manual",
        channel="manual",
        intent_type="merchant",
        estimated_deliveries_per_month=0,
        phone=None,
        email=None,
        last_inbound_at=None,
        awaiting_reply=False,
        address={},
        service_area=None,
    )
    base.update(kw)
    return SimpleNamespace(**base)


def test_fit_score_is_deterministic_and_explained() -> None:
    hot = _duck(
        industry="pharmacy",
        estimated_deliveries_per_month=300,
        service_area="M5V",
        channel="whatsapp",
        phone="1",
        email="a@b",
        awaiting_reply=True,
    )
    a, b = fit_score(hot), fit_score(hot)
    assert a == b and a["score"] >= 80
    labels = " | ".join(r["label"] for r in a["reasons"])
    assert (
        "Pharmacy" in labels and "In coverage (M5V" in labels and "WhatsApp" in labels
    )
    assert sum(r["points"] for r in a["reasons"]) == a["score"]
    cold = fit_score(_duck(industry="crypto", service_area="V6B"))
    assert cold["score"] < 30 and any(
        "Outside coverage" in r["label"] for r in cold["reasons"]
    )
    for word in (
        "shopify",
        "laboratory",
        "warehouse",
        "wholesale",
        "construction",
        "plumbing",
        "electrical",
    ):
        assert fit_score(_duck(industry=word))["reasons"][0]["points"] == 30, word
    assert fit_score(_duck(intent_type="driver_partner"))["score"] == 0


# --- 3. Draft -----------------------------------------------------------------------------
def test_draft_templates_and_ai_off_by_default(db) -> None:
    lead = _lead(db, primary_contact_name="Maya Patel")
    q = lead_quote(db, lead, website_url="https://porterchain.com")
    email = build_draft(lead, channel="email", quote=q, sender="Ravi")
    assert email["subject"].startswith("Your PorterChain delivery quote")
    assert (
        "Hi Maya" in email["body"]
        and q["booking_url"] in email["body"]
        and "prescription" in email["body"]
    )
    assert email["source"] == "template"
    no_q = build_draft(lead, channel="whatsapp", quote=None)
    assert "$" not in no_q["body"] and no_q["subject"] is None


def test_ai_polish_cannot_drop_price(db) -> None:
    lead = _lead(db)
    q = lead_quote(db, lead, website_url="https://porterchain.com")
    with patch.object(
        draft_mod, "_llm_polish", return_value="Short and sweet, no price."
    ):
        d = build_draft(lead, channel="email", quote=q)
    assert d["source"] == "template" and q["amount_display"] in d["body"]
    with patch.object(
        draft_mod,
        "_llm_polish",
        return_value=f"Nice! {q['amount_display']} {q['booking_url']}",
    ):
        assert build_draft(lead, channel="email", quote=q)["source"] == "template+ai"


# --- 6/5. Speed dashboard + weekly summary --------------------------------------------------------
def test_speed_window_and_weekly_summary(db) -> None:
    now = datetime.now(UTC) + timedelta(minutes=1)
    ch = f"desk_{uuid.uuid4().hex[:6]}"
    t0 = datetime.now(UTC) - timedelta(hours=1)
    _lead(db, channel=ch, created_at=t0, first_response_at=t0 + timedelta(minutes=3))
    _lead(
        db,
        channel=ch,
        created_at=t0,
        first_response_at=t0 + timedelta(minutes=30),
        status="won",
        quoted_at=t0,
        won_at=t0 + timedelta(minutes=40),
    )
    _lead(db, channel=ch, created_at=t0, status="lost", lost_reason="price", lost_at=t0)
    w = speed_window(db, days=7, now=now)
    row = next(r for r in w["win_rate_by_channel"] if r["channel"] == ch)
    assert (row["leads"], row["won"], row["lost"], row["win_rate"]) == (3, 1, 1, 50.0)
    assert (
        w["median_first_reply_minutes"] is not None
        and w["answered_within_5m_pct"] is not None
    )
    weekly = weekly_summary(db, now=now)
    wrow = next(r for r in weekly["by_channel"] if r["channel"] == ch)
    assert (wrow["won"], wrow["lost"]) == (1, 1)
    assert any(r["reason"] == "price" for r in weekly["lost_reasons"])


def test_speed_endpoint(admin_client) -> None:
    res = admin_client.get("/v1/admin/leads/speed")
    assert res.status_code == 200, res.text
    assert [w["days"] for w in res.json()["windows"]] == [7, 30]
    assert admin_client.get("/v1/admin/leads/weekly-summary").status_code == 200


# --- 7. Mobile-first alerts -------------------------------------------------------------------------
def test_owner_alert_email_and_sms_only_when_enabled() -> None:
    from porterchain_api.collaboration_engine.lead_ops import notify_hot_lead

    def run(**cfg):
        lead = CrmLead(
            id=str(uuid.uuid4()),
            company_name="Acme",
            priority="high",
            status="new",
            phone="(416) 555-0199",
            source="website_calculator",
            channel="website",
            custom_fields={},
        )
        s = _settings(
            lead_alert_email="ravi@porterchain.com",
            lead_alert_sms_to="+14165550100",
            **cfg,
        )
        with (
            patch("porterchain_api.config.get_settings", return_value=s),
            patch(
                "porterchain_api.platform.staff_notify.dispatch_staff_specs"
            ) as dispatch,
        ):
            notify_hot_lead(MagicMock(), lead, created=True)
        return dispatch.call_args[0][1]

    specs = run()
    email = [s for s in specs if s["channel"] == "email"]
    assert [s["recipient_address"] for s in email] == ["ravi@porterchain.com"]
    assert "tel:+14165550199" in email[0]["context"]["quick_actions"]
    assert "https://wa.me/14165550199" in email[0]["context"]["quick_actions"]
    assert not [s for s in specs if s["channel"] == "sms"]  # flag off
    with patch(
        "porterchain_shared.config.settings.get_platform_settings",
        return_value=SimpleNamespace(twilio_account_sid=""),
    ):
        assert not [
            s for s in run(lead_alert_sms_enabled=True) if s["channel"] == "sms"
        ]  # no Twilio
    with patch(
        "porterchain_shared.config.settings.get_platform_settings",
        return_value=SimpleNamespace(twilio_account_sid="AC123"),
    ):
        sms = [s for s in run(lead_alert_sms_enabled=True) if s["channel"] == "sms"]
    assert [s["recipient_address"] for s in sms] == ["+14165550100"]


# --- Round 3: inbound triage + auto-send default ------------------------------------
def test_triage_extracts_quote_inputs_and_intent() -> None:
    from porterchain_api.lead_desk.triage import triage

    t = triage("Hi, how much for 12 boxes from M5V 2T6 to L4K by cargo van tomorrow?")
    assert (t["pickup_fsa"], t["dropoff_fsa"], t["parcel_count"], t["vehicle_class"]) == ("M5V", "L4K", 12, "cargo_van")
    assert t["intent"] == "ready_to_book" and t["urgent"]
    assert triage("I'm out of office until Monday")["intent"] == "auto_reply"
    assert triage("not interested, thanks")["intent"] == "not_interested"


def test_inbound_message_fills_quote_inputs_without_overwriting(db) -> None:
    from porterchain_api.collaboration_engine.lead_pipeline import apply_triage

    lead = _lead(db, priority="medium", custom_fields={"pickup_fsa": "M4C"})
    apply_triage(lead, "Need a quote: 3 pallets M5V to L6T, box truck")
    assert lead.custom_fields["pickup_fsa"] == "M4C"  # kept
    assert lead.custom_fields["dropoff_fsa"] == "L6T"
    assert lead.custom_fields["parcel_count"] == 3 and lead.preferred_vehicle == "box_16"
    assert lead.priority == "high" and lead.custom_fields["triage"]["intent"] == "quote_request"


def test_lead_agent_auto_send_is_off_by_default() -> None:
    assert Settings(app_env="local", jwt_secret="t").lead_agent_auto_send is False


def test_rescore_aligns_stored_score_with_fit(db, admin_client) -> None:
    lead = _lead(db, lead_score=3, industry="pharmacy", estimated_deliveries_per_month=60)
    r = admin_client.post("/v1/admin/leads/rescore")
    assert r.status_code == 200 and r.json()["rescored"] >= 1
    db.refresh(lead)
    assert lead.lead_score == admin_client.get(f"/v1/admin/leads/{lead.id}/score").json()["score"]


def test_redact_strips_contact_details_before_any_model_call() -> None:
    from porterchain_api.intelligence_engine.privacy import redact

    out = redact("Call Priya at +1 (416) 555-0199 or priya@rexall.example, pickup M5V 2T6")
    assert "555" not in out and "@" not in out and "2T6" not in out
    assert "[phone]" in out and "[email]" in out and "M5V" in out


def test_lead_assist_flag_key_matches_phase2_check() -> None:
    from porterchain_api.intelligence_engine import phase2_intelligence_enabled

    assert phase2_intelligence_enabled({"intelligence": True})
    src = open("src/porterchain_api/routers/admin/leads_360.py").read()
    assert 'flags={"intelligence":' in src
