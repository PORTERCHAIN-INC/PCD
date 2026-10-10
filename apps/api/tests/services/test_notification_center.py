"""Round 2: admin Notifications center, template manager, matrix, digest, ZeptoMail tracking,
merchant email branding and the email gap-fills (French, plain text, a11y, dark mode, preheader).

No real send: every sender is a tripwire.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import porterchain_api.main  # noqa: F401
import pytest
from fastapi.testclient import TestClient
from porterchain_api.admin_engine.rbac import AdminContext, parse_admin_role
from porterchain_api.admin_models import AdminUser
from porterchain_api.auth.admin import get_admin_context
from porterchain_api.db import get_db
from porterchain_api.main import app
from porterchain_api.notification_engine import center, template_copy
from porterchain_api.notification_engine.center_settings import DIGEST_KEY, MATRIX_KEY
from porterchain_api.notification_engine.models import (
    EmailSuppression,
    NotificationAdminSetting,
    NotificationRecord,
    NotificationTemplateCopy,
)
from porterchain_api.notification_engine.receiver_emails import RECEIVER_TEMPLATES
from porterchain_api.notification_engine.templates import TEMPLATES, render_email


@pytest.fixture(autouse=True)
def no_real_sends(monkeypatch):
    from porterchain_api.notification_engine import delivery_service as ds

    def _boom(*_a, **_k):
        raise AssertionError("real send attempted")

    for name in ("_send_sms", "_send_push", "_send_email_smtp", "_send_sms_twilio", "_send_email_zeptomail_https"):
        monkeypatch.setattr(ds.DeliveryService, name, _boom)


@pytest.fixture
def client(db, monkeypatch):
    # SpiceDB is not in the unit suite: allow the module checks, assert RBAC separately.
    monkeypatch.setattr("porterchain_api.routers.notifications_center.require_module", lambda *_a: None)
    user = AdminUser(id=str(uuid4()), clerk_user_id=f"nc-{uuid4().hex[:6]}", email="ravi@porterchain.com", role="super_admin")
    admin = AdminContext(user=user, role=parse_admin_role("super_admin"))
    app.dependency_overrides[get_admin_context] = lambda: admin
    app.dependency_overrides[get_db] = lambda: db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def clean_center(db):
    yield
    db.rollback()
    db.query(NotificationTemplateCopy).delete()
    for key in (MATRIX_KEY, DIGEST_KEY):
        row = db.get(NotificationAdminSetting, key)
        if row:
            db.delete(row)
    db.commit()
    template_copy.invalidate()


def _record(db, **kw) -> NotificationRecord:
    base = dict(
        event_type="order.delivered",
        template_key="cx_delivered",
        category="orders",
        channel="email",
        priority="normal",
        recipient_type="consignee",
        recipient_id=f"r-{uuid4().hex[:8]}",
        recipient_address=f"r-{uuid4().hex[:8]}@example.test",
        title="Delivered",
        body="Delivered",
        status="sent",
        search_tags={},
    )
    base.update(kw)
    row = NotificationRecord(**base)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


# --- tracking webhook ----------------------------------------------------------------


def _hook(client, body):
    from porterchain_api.routers import zeptomail_webhook

    class _S:
        zeptomail_webhook_secret = "s3cret"
        app_env = "local"

    zeptomail_webhook.get_settings = lambda: _S()  # restored by module reload below
    return client.post("/v1/public/mail/zeptomail", json=body, headers={"X-PorterChain-Mail-Webhook": "s3cret"})


def test_webhook_records_delivered_opened_and_hard_bounce_suppresses(client, db, monkeypatch) -> None:
    from porterchain_api.routers import zeptomail_webhook

    original = zeptomail_webhook.get_settings
    try:
        row = _record(db, sent_at=datetime.now(UTC), provider_message_id=None)
        row.provider_message_id = row.id
        row.delivery_status = "accepted"
        db.commit()
        ref = {"email_info": {"client_reference": row.id, "to": [{"email_address": {"address": row.recipient_address}}]}}
        assert _hook(client, {"event_name": ["delivered"], "event_message": [ref]}).json()["messages"] == 1
        db.refresh(row)
        assert row.delivery_status == "delivered" and row.delivered_at
        _hook(client, {"event_name": ["email_open"], "event_message": [ref]})
        db.refresh(row)
        assert row.delivery_status == "opened" and row.opened_at

        bad = _record(db, sent_at=datetime.now(UTC))
        bad.provider_message_id = bad.id
        db.commit()
        ref2 = {"email_info": {"client_reference": bad.id, "from": {"address": "noreply@porterchain.com"}}}
        out = _hook(client, {"event_name": ["hardbounce"], "event_message": [ref2]}).json()
        assert out["bounced"] == 1
        db.refresh(bad)
        assert bad.status == "bounced" and bad.delivery_status == "hard_bounce" and bad.bounced_at
        sup = db.get(EmailSuppression, bad.recipient_address.lower())
        assert sup is not None and sup.active
        assert db.get(EmailSuppression, "noreply@porterchain.com") is None  # never suppress our sender

        from porterchain_api.notification_engine.bounce import address_is_bounced

        assert address_is_bounced(db, bad.recipient_address)
        # Soft bounce marks the message only.
        soft = _record(db, sent_at=datetime.now(UTC))
        soft.provider_message_id = soft.id
        db.commit()
        _hook(client, {"event_name": ["softbounce"], "event_message": [{"client_reference": soft.id}]})
        assert db.get(EmailSuppression, soft.recipient_address.lower()) is None

        # Unsuppress from the center.
        resp = client.post("/v1/admin/notifications/center/suppressions/release", json={"email": bad.recipient_address})
        assert resp.status_code == 200
        assert not address_is_bounced(db, bad.recipient_address)
        assert client.post("/v1/admin/notifications/center/suppressions/release", json={"email": bad.recipient_address}).status_code == 404
    finally:
        zeptomail_webhook.get_settings = original


def test_accepted_email_is_not_counted_delivered_until_webhook(db) -> None:
    from porterchain_api.notification_engine.delivery_service import DeliveryService

    row = _record(db, status="queued")
    DeliveryService()._mark_sent(db, row.id)
    db.commit()
    db.refresh(row)
    assert row.status == "sent" and row.delivery_status == "accepted"
    assert row.delivered_at is None and row.provider_message_id == row.id


def test_zeptomail_payload_carries_client_reference_and_reply_to(monkeypatch) -> None:
    import httpx
    from porterchain_api.notification_engine.zeptomail import send_zeptomail

    seen = {}

    class _R:
        status_code = 201
        text = "ok"

    monkeypatch.setattr(httpx, "post", lambda url, json, headers, timeout: seen.update(json) or _R())

    class _S:
        smtp_password = "tok"
        zeptomail_api_url = "https://api.zeptomail.ca/v1.1/email"

    send_zeptomail(recipient="a@b.test", subject="s", text_body="t", html_body="<p>t</p>", from_addr="noreply@porterchain.com",
                   from_name="PorterChain", settings=_S(), reference="nid-123", reply_to="help@shop.test")
    assert seen["client_reference"] == "nid-123"
    assert seen["reply_to"] == [{"address": "help@shop.test"}]
    assert seen["textbody"] == "t"


# --- log, detail, dead letters, metrics ----------------------------------------------


def test_log_filters_and_detail(client, db) -> None:
    tag = uuid4().hex[:8]
    a = _record(db, recipient_address=f"{tag}-a@example.test", delivery_status="opened", sent_at=datetime.now(UTC))
    _record(db, recipient_address=f"{tag}-b@example.test", recipient_type="merchant", template_key="delivery_failed", event_type="order.failed")
    rows = client.get("/v1/admin/notifications/center/log", params={"q": tag, "persona": "receiver"}).json()
    assert [r["id"] for r in rows] == [a.id]
    assert rows[0]["persona"] == "receiver" and rows[0]["delivery"] == "opened"
    rows = client.get("/v1/admin/notifications/center/log", params={"q": tag, "event": "order.failed"}).json()
    assert len(rows) == 1 and rows[0]["persona"] == "merchant"
    rows = client.get("/v1/admin/notifications/center/log", params={"q": tag, "status": "opened"}).json()
    assert len(rows) == 1
    d = client.get(f"/v1/admin/notifications/center/log/{a.id}").json()
    assert d["id"] == a.id and "attempts" in d and d["replayable"] is False
    assert client.get("/v1/admin/notifications/center/log/nope").status_code == 404


def test_dead_letter_replay(client, db) -> None:
    row = _record(db, status="dead_letter", failure_reason="dispatch_error:boom", template_key="delivery_failed",
                  recipient_type="merchant", channel="in_app", recipient_address=None)
    ids = [r["id"] for r in client.get("/v1/admin/notifications/center/dead-letters").json()]
    assert row.id in ids
    assert client.post(f"/v1/admin/notifications/center/dead-letters/{row.id}/replay").status_code == 200
    db.refresh(row)
    assert row.status != "dead_letter"
    assert client.post(f"/v1/admin/notifications/center/dead-letters/{row.id}/replay").status_code == 404


def test_speed_metrics_percentiles_and_rates(db) -> None:
    now = datetime.now(UTC)
    tag = uuid4().hex[:6]
    base = now - timedelta(minutes=30)
    for i, ms in enumerate([100, 200, 300, 400, 5000]):
        r = _record(db, recipient_address=f"m{tag}{i}@example.test", created_at=base, sent_at=base + timedelta(milliseconds=ms),
                    delivery_status="delivered" if i < 4 else "hard_bounce", status="sent" if i < 4 else "bounced")
        assert r
    m = center.metrics(db, hours=1, now=now)
    assert m["accepted"] >= 5 and m["p50_ms"] is not None and m["p95_ms"] >= m["p50_ms"]
    assert m["bounce_pct"] is not None and m["delivery_pct"] is not None
    assert len(m["failures_per_hour"]) == 2 and sum(b["count"] for b in m["failures_per_hour"]) >= 1


# --- templates -----------------------------------------------------------------------


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_every_template_previews_in_both_languages(lang) -> None:
    for key in TEMPLATES:
        p = center.preview(key, lang=lang)
        assert p["subject"] and p["text"] and p["html"].startswith("<!DOCTYPE html>"), key


def test_customer_templates_have_french() -> None:
    from porterchain_api.notification_engine.customer_fr import FR

    for key in FR:
        if key not in TEMPLATES:
            continue
        p = center.preview(key, lang="fr")
        assert p["lang"] == "fr" and 'lang="fr-CA"' in p["html"], key
        assert "Ce n'est pas un message publicitaire" in p["text"], key
    for key in RECEIVER_TEMPLATES:
        assert 'lang="fr-CA"' in center.preview(key, lang="fr")["html"]


def test_copy_edit_versions_preview_and_history(client, db, clean_center) -> None:
    url = "/v1/admin/notifications/center/templates/cx_delivered"
    bad = client.put(f"{url}/copy", json={"lang": "en", "subject": "Hi {oops}"})
    assert bad.status_code == 422 and "unknown_placeholder" in bad.text
    draft = client.post(f"{url}/preview", json={"lang": "en", "subject": "Here it is · {tracking}", "intro": "Left at your door by {merchant}."}).json()
    assert draft["subject"].startswith("Here it is · PC-") and "Left at your door by Bloor West Pharmacy." in draft["html"]
    assert client.put(f"{url}/copy", json={"lang": "en", "subject": "v1 {tracking}"}).json()["version"] == 1
    assert client.put(f"{url}/copy", json={"lang": "en", "subject": "v2 {tracking}"}).json()["version"] == 2
    subject, _t, _h = render_email("cx_delivered", {**center.SAMPLE, "audience": "receiver", "lang": "en"})
    assert subject.startswith("v2 PC-")
    fr_subject, _t, _h = render_email("cx_delivered", {**center.SAMPLE, "audience": "receiver", "lang": "fr"})
    assert not fr_subject.startswith("v2")  # per-language
    hist = client.get(f"{url}/history").json()
    assert [h["version"] for h in hist] == [2, 1] and hist[0]["created_by"] == "ravi@porterchain.com"
    # Clearing reverts to the built-in copy; the CASL footer is never editable.
    assert client.put(f"{url}/copy", json={"lang": "en", "subject": "", "intro": ""}).json()["active"] is False
    subject, text, _h = render_email("cx_delivered", {**center.SAMPLE, "audience": "receiver", "lang": "en"})
    assert not subject.startswith("v2") and "not marketing" in text


def test_test_send_goes_only_to_the_admin(client, db) -> None:
    resp = client.post("/v1/admin/notifications/center/templates/cx_out_for_delivery/test", json={"lang": "fr"})
    assert resp.status_code == 200, resp.text
    out = resp.json()
    assert out["to"] == "ravi@porterchain.com"
    row = db.get(NotificationRecord, out["id"])
    assert row.recipient_address == "ravi@porterchain.com" and row.recipient_type == "admin"


# --- matrix --------------------------------------------------------------------------


def test_matrix_lists_personas_and_switch_drops_specs(client, db, clean_center) -> None:
    m = client.get("/v1/admin/notifications/center/matrix").json()
    assert m["personas"] == ["receiver", "customer", "merchant", "driver", "admin"]
    events = {r["event"]: r for r in m["rows"]}
    assert "cx.delivered" in events and "order.failed" in events
    assert {"merchant", "admin"} <= set(events["order.failed"]["cells"])
    assert client.put("/v1/admin/notifications/center/matrix", json={"event": "order.failed", "persona": "merchant", "enabled": False}).status_code == 200
    from porterchain_api.notification_engine.center_settings import drop_matrix_off

    specs = [{"recipient_type": "merchant", "template_key": "delivery_failed"}, {"recipient_type": "admin", "template_key": "delivery_failed"}]
    assert [s["recipient_type"] for s in drop_matrix_off(db, "order.failed", specs)] == ["admin"]
    m = client.get("/v1/admin/notifications/center/matrix").json()
    row = next(r for r in m["rows"] if r["event"] == "order.failed")
    assert row["cells"]["merchant"]["on"] is False


def test_matrix_receiver_switch_stops_cx_email(client, db, clean_center, merchant_ctx) -> None:
    from porterchain_api.booking_engine.numbers import generate_order_number, generate_tracking_number
    from porterchain_api.booking_models import Order
    from porterchain_api.customer_experience.notifications import notify

    client.put("/v1/admin/notifications/center/matrix", json={"event": "cx.out_for_delivery", "persona": "receiver", "enabled": False})
    order = Order(order_number=generate_order_number(), tracking_number=generate_tracking_number(), state="IN_TRANSIT",
                  merchant_id=merchant_ctx.merchant.id, amount_cents=100, currency="cad", pickup={}, dropoff={}, scheduled_at=datetime.now(UTC),
                  compliance_metadata={"consignee": {"email": f"x{uuid4().hex[:6]}@example.test"}})
    db.add(order)
    db.commit()
    from porterchain_api.config import get_settings

    out = notify(db, get_settings(), order, "out_for_delivery")
    assert out["skipped"].get("all") == "disabled_platform"


# --- digest --------------------------------------------------------------------------


def test_digest_off_by_default_needs_approval_then_sends_once(client, db, clean_center, monkeypatch) -> None:
    calls: list = []
    monkeypatch.setattr(
        "porterchain_api.platform.staff_notify.dispatch_staff_specs", lambda _db, specs, **k: calls.append((specs, k))
    )
    assert center.maybe_send_digest(db, force=True)["reason"] == "off"
    g = client.get("/v1/admin/notifications/center/digest").json()
    assert g["settings"]["enabled"] is False and "delivered" in g["preview"]
    assert client.put("/v1/admin/notifications/center/digest", json={"enabled": True}).status_code == 409
    ok = client.put("/v1/admin/notifications/center/digest", json={"enabled": True, "approve": True}).json()
    assert ok["settings"]["approved_by"] == "ravi@porterchain.com"
    at = datetime(2026, 10, 9, 12, 0, tzinfo=UTC)  # 08:00 Toronto
    first = center.maybe_send_digest(db, now=at)
    assert first["sent"] is True and first["digest"]["date"] == "2026-10-08"
    assert center.maybe_send_digest(db, now=at + timedelta(hours=1))["reason"] == "not_due"
    assert len(calls) == 1
    specs, kw = calls[0]
    assert kw["correlation_id"] == "digest-2026-10-08"
    assert [x["channel"] for x in specs] == ["email"] and specs[0]["template_key"] == "ops_daily_digest"
    subject, text, html = render_email("ops_daily_digest", specs[0]["context"])
    assert "delivered" in subject and "Dead letters" in html and "Dead letters" not in subject
    # Turning off clears the approval.
    off = client.put("/v1/admin/notifications/center/digest", json={"enabled": False}).json()
    assert off["settings"]["approved"] is False


# --- merchant branding & email gap-fills ---------------------------------------------


def test_brand_colour_used_only_when_aa_and_logo_has_alt() -> None:
    from porterchain_api.customer_experience.settings import contrast_on_white, email_brand, normalize_cx

    cfg = normalize_cx({"notifications": {"brand_color": "#0f766e", "reply_to": "help@shop.test", "logo_url": "https://cdn.shop.test/l.png"}})
    out = email_brand(None, cfg)
    assert out == {"brand_color": "#0f766e", "logo_url": "https://cdn.shop.test/l.png", "reply_to_email": "help@shop.test"}
    weak = email_brand(None, normalize_cx({"notifications": {"brand_color": "#fde047"}}))
    assert "brand_color" not in weak and contrast_on_white("#fde047") < 4.5
    with pytest.raises(ValueError):
        normalize_cx({"notifications": {"logo_url": "http://insecure.test/l.png"}})
    _s, _t, html = render_email("cx_delivered", {**center.SAMPLE, **out, "audience": "receiver", "lang": "en"})
    assert 'background:#0f766e' in html and 'alt="Bloor West Pharmacy"' in html


def test_every_email_has_preheader_plain_text_dark_mode_and_aa_colours() -> None:
    for key in TEMPLATES:
        for lang in ("en", "fr"):
            p = center.preview(key, lang=lang)
            html = p["html"]
            assert "&zwnj;" in html, key  # preheader filler
            assert "prefers-color-scheme: dark" in html, key
            assert "<html" in html and 'lang="' in html, key
            assert p["text"].strip() and "<" not in p["text"].split("\n")[0], key
            for weak in ("#94a3b8;line", "color:#3b82f6", "color:#64748b"):
                assert weak not in html, (key, weak)
            for img in re.findall(r"<img[^>]*>", html):
                assert "alt=" in img, key


def test_center_requires_notification_modules(db) -> None:
    user = AdminUser(id=str(uuid4()), clerk_user_id="nc-x", email="x@porterchain.com", role="support")
    app.dependency_overrides[get_admin_context] = lambda: AdminContext(user=user, role=parse_admin_role("super_admin"))
    app.dependency_overrides[get_db] = lambda: db
    try:
        c = TestClient(app)
        assert c.get("/v1/admin/notifications/center/metrics").status_code == 403  # unlinked user
        assert c.post("/v1/admin/notifications/center/dead-letters/replay-all").status_code == 403
    finally:
        app.dependency_overrides.clear()
