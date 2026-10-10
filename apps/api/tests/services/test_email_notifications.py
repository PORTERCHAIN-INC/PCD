"""Email-first notifications: one email per delivery moment, held-not-dropped quiet hours,
isolated fan-out with dead-letter replay, List-Unsubscribe, French receiver emails,
ops failure alert, per-recipient ETA rate limit, reschedule routing.

No real send: ZeptoMail/SMTP/SMS/push senders are tripwires; the one ZeptoMail test
stubs httpx.post and inspects the payload.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import porterchain_api.main  # noqa: F401 — registers every ORM model
import pytest
from porterchain_api.booking_engine.numbers import generate_order_number, generate_tracking_number
from porterchain_api.booking_models import Order
from porterchain_api.customer_experience.notifications import notify
from porterchain_api.notification_engine.engine import get_notification_engine
from porterchain_api.notification_engine.models import NotificationRecord, NotificationUserSettings
from porterchain_api.notification_engine.receiver_emails import render_receiver_email
from porterchain_api.notification_engine.templates import render_email

NOON_ET = datetime(2026, 10, 9, 16, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def no_real_sends(monkeypatch):
    from porterchain_api.notification_engine import delivery_service as ds

    def _boom(*_a, **_k):
        raise AssertionError("real notification send attempted in a test")

    for name in ("_send_sms", "_send_push", "_send_email_smtp", "_send_sms_twilio"):
        monkeypatch.setattr(ds.DeliveryService, name, _boom)


def _order(db, merchant_ctx, *, state="DELIVERED", email=None, dropoff_extra=None, driver_id=None) -> Order:
    order = Order(
        order_number=generate_order_number(),
        tracking_number=generate_tracking_number(),
        state=state,
        merchant_id=merchant_ctx.merchant.id,
        amount_cents=2500,
        currency="cad",
        pickup={"formatted": "1 Front St, Toronto", "postal": "M5J 1E6"},
        dropoff={"formatted": "9 Main St, Toronto", "postal": "M4E 2V5", **(dropoff_extra or {})},
        scheduled_at=datetime.now(UTC),
        assigned_driver_id=driver_id,
        compliance_metadata={"consignee": {"email": email or f"r-{uuid4().hex[:10]}@example.test"}},
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


def _rows(db, **filters) -> list[NotificationRecord]:
    q = db.query(NotificationRecord)
    for k, v in filters.items():
        q = q.filter(getattr(NotificationRecord, k) == v)
    return q.order_by(NotificationRecord.created_at.asc()).all()


# --- one email per moment ----------------------------------------------------------


def test_delivered_is_one_email_per_address_across_both_paths(db, merchant_ctx, settings) -> None:
    from porterchain_api.notification_engine.event_router import _specs_for_event

    order = _order(db, merchant_ctx)
    addr = order.compliance_metadata["consignee"]["email"]
    res = notify(db, settings, order, "delivered", now=NOON_ET)
    assert res["queued"] == ["email"]
    specs = [
        s
        for s in _specs_for_event(
            "order.delivered", {"order_id": order.id, "receiver_email": addr, "merchant_id": order.merchant_id}
        )
        if s["channel"] == "email" and s["recipient_address"] == addr
    ]
    assert specs and specs[0]["dedupe_family"].startswith(f"delivered|{order.id}|")
    get_notification_engine().dispatch_multi(db, specs, event_type="order.delivered", correlation_id=order.id)
    db.commit()
    emails = [r for r in _rows(db, channel="email") if r.recipient_address == addr]
    assert len(emails) == 1 and emails[0].template_key == "cx_delivered"


def test_route_table_has_no_dead_branches_for_owned_events() -> None:
    import inspect

    from porterchain_api.notification_engine import event_router

    src = inspect.getsource(event_router._specs_for_event)
    for owned in (
        "BOOKING_CONFIRMED:",
        "PARCEL_PICKED_UP:",
        "PARCEL_DELIVERED:",
        "(DomainEventType.ORDER_CREATED, DomainEventType.ORDER_BOOKED)",
    ):
        assert owned not in src


def test_second_attempt_gets_its_own_email(db, merchant_ctx, settings) -> None:
    from porterchain_api.notification_engine.route_table import attempt_family

    assert attempt_family("o", "A@x.test", 1) != attempt_family("o", "a@x.test", 2)
    assert attempt_family("o", "A@x.test", 1) == attempt_family("o", "a@x.test", 1)


# --- receiver email content --------------------------------------------------------


def test_delivered_email_has_signed_pod_link_report_problem_and_casl_footer(db, merchant_ctx, settings) -> None:
    order = _order(db, merchant_ctx)
    notify(db, settings, order, "delivered", now=NOON_ET)
    row = _rows(db, recipient_id=order.id, channel="email")[0]
    assert "View proof of delivery" in row.html_body
    assert f"/en/track/{order.tracking_number}?t=" in row.html_body
    assert "Report a problem" in row.html_body and "mailto:" in row.html_body
    assert "PorterChain Logistics Inc." in row.body and "not marketing" in row.body
    assert merchant_ctx.merchant.company_name in row.title
    # PIPEDA: no street address in the email.
    assert "9 Main St" not in row.html_body and "9 Main St" not in row.body
    assert "unsubscribe" not in row.html_body.lower()


def test_quebec_dropoff_gets_french_email(db, merchant_ctx, settings) -> None:
    order = _order(db, merchant_ctx, dropoff_extra={"province": "QC"})
    notify(db, settings, order, "delivered", now=NOON_ET)
    row = _rows(db, recipient_id=order.id, channel="email")[0]
    assert "Votre livraison est arrivée" in row.title
    assert 'lang="fr-CA"' in row.html_body
    assert f"/fr/track/{order.tracking_number}?t=" in row.html_body
    assert "Signaler un problème" in row.html_body
    assert "pas un message publicitaire" in row.body


@pytest.mark.parametrize(
    "template",
    [
        "cx_out_for_delivery",
        "cx_eta_20",
        "cx_attempted",
        "cx_rescheduled",
        "order_booked",
        "parcel_picked_up",
        "delivery_failed",
    ],
)
@pytest.mark.parametrize("lang", ["en", "fr"])
def test_every_receiver_template_renders(template: str, lang: str) -> None:
    subject, text, html = render_receiver_email(
        template,
        {
            "lang": lang,
            "merchant_name": "Rx Pharmacy",
            "tracking_number": "PC-1",
            "eta_minutes": "12",
            "window_label": "Sat 10:00-12:00",
        },
    )
    assert subject and "Rx Pharmacy" in subject and "PC-1" in text and "<html" in html


def test_business_copy_stays_english_business_layout() -> None:
    _s, _t, html = render_email(
        "delivered",
        {"audience": "business", "lang": "fr", "order_number": "O-1", "tracking_number": "PC-1"},
    )
    assert "Your shipment has arrived" in html


def test_attempted_email_offers_one_tap_reschedule_when_policy_allows(db, merchant_ctx, settings) -> None:
    from porterchain_api.customer_experience.context import update_cx_meta

    order = _order(db, merchant_ctx, state="FAILED")
    update_cx_meta(order, reattempt={"action": "reattempt"}, attempts=1)
    db.commit()
    notify(db, settings, order, "attempted", now=NOON_ET, dedupe_key="attempted:1")
    row = _rows(db, recipient_id=order.id, channel="email")[0]
    assert "Choose a new time" in row.html_body and "/manage?t=" in row.html_body


# --- ETA rate limit ------------------------------------------------------------------


def test_eta_emails_rate_limited_per_recipient(db, merchant_ctx, settings) -> None:
    addr = f"busy-{uuid4().hex[:8]}@example.test"
    first = _order(db, merchant_ctx, state="IN_TRANSIT", email=addr)
    second = _order(db, merchant_ctx, state="IN_TRANSIT", email=addr)
    assert notify(db, settings, first, "eta_20", now=NOON_ET)["queued"] == ["email"]
    res = notify(db, settings, second, "eta_20", now=NOON_ET)
    assert res["queued"] == [] and res["skipped"]["email"] == "suppressed"


# --- quiet hours hold, release -----------------------------------------------------


def test_quiet_hours_hold_then_sweeper_releases(db, monkeypatch) -> None:
    from porterchain_api.notification_engine import retry_sweeper

    uid = str(uuid4())
    db.add(
        NotificationUserSettings(
            user_role="driver",
            user_id=uid,
            quiet_hours_enabled=True,
            # Window always contains "now" (a fixed 0-23 window misses 23:xx UTC).
            quiet_start_hour=datetime.now(UTC).hour,
            quiet_end_hour=(datetime.now(UTC).hour + 2) % 24,
            timezone="UTC",
        )
    )
    db.flush()
    monkeypatch.setattr(
        "porterchain_api.notification_engine.device_service.DeviceService.list_active", lambda *_a, **_k: [object()]
    )
    rec = get_notification_engine().dispatch(
        db,
        event_type="t.quiet",
        template_key="driver_alert",
        channel="push",
        recipient_type="driver",
        recipient_id=uid,
        context={"title": "x", "body": "y"},
    )
    assert rec is not None and rec.status == "held" and rec.next_retry_at is not None
    rec.next_retry_at = datetime.now(UTC) - timedelta(seconds=1)
    db.commit()
    emitted: list[str] = []
    monkeypatch.setattr(retry_sweeper, "_emit_queued", lambda _db, row: emitted.append(row.id))
    out = retry_sweeper.sweep_notification_retries(db)
    assert out["held_released"] >= 1 and rec.id in emitted
    db.refresh(rec)
    assert rec.status == "queued"


# --- isolation, dead letter, replay, idempotency column ------------------------------


def test_one_bad_spec_does_not_roll_back_the_others(db, monkeypatch) -> None:
    from porterchain_api.notification_engine import engine as engine_mod

    real = engine_mod.render_email

    def flaky(template, ctx):
        if template == "boom_template":
            raise RuntimeError("template exploded")
        return real(template, ctx)

    monkeypatch.setattr(engine_mod, "render_email", flaky)
    uid = str(uuid4())
    specs = [
        {
            "template_key": "boom_template",
            "channel": "in_app",
            "recipient_type": "merchant",
            "recipient_id": uid,
            "context": {},
        },
        {
            "template_key": "order_booked",
            "channel": "in_app",
            "recipient_type": "merchant",
            "recipient_id": uid,
            "context": {"order_number": "O-9"},
        },
    ]
    out = get_notification_engine().dispatch_multi(db, specs, event_type="t.iso", correlation_id=str(uuid4()))
    db.commit()
    assert [r.template_key for r in out] == ["order_booked"]
    dead = _rows(db, recipient_id=uid, status="dead_letter")
    assert len(dead) == 1 and dead[0].failure_reason.startswith("dispatch_error:RuntimeError")

    monkeypatch.setattr(engine_mod, "render_email", real)
    assert get_notification_engine().requeue(db, dead[0].id) is True
    db.refresh(dead[0])
    assert dead[0].status == "sent"


def test_idempotency_key_is_a_real_unique_column(db) -> None:
    uid = str(uuid4())
    corr = str(uuid4())
    eng = get_notification_engine()
    a = eng.dispatch(
        db,
        event_type="t.idem",
        template_key="order_booked",
        channel="in_app",
        recipient_type="merchant",
        recipient_id=uid,
        correlation_id=corr,
    )
    b = eng.dispatch(
        db,
        event_type="t.idem",
        template_key="order_booked",
        channel="in_app",
        recipient_type="merchant",
        recipient_id=uid,
        correlation_id=corr,
    )
    db.commit()
    assert a is not None and b is not None and a.id == b.id
    assert a.idempotency_key and a.idempotency_key.startswith("t.idem|")
    from sqlalchemy import inspect as sa_inspect

    names = {ix["name"] for ix in sa_inspect(db.get_bind()).get_indexes("notification_records")}
    assert "uq_notification_records_idem_col" in names
    assert "uq_notification_records_idempotency_key" not in names


# --- List-Unsubscribe, unsubscribe endpoint ------------------------------------------


def _zepto_payload(monkeypatch, category: str) -> dict:
    import httpx
    from porterchain_api.notification_engine import delivery_service as ds

    captured: dict = {}

    class _Resp:
        status_code = 201
        text = "ok"

    def fake_post(url, json=None, headers=None, timeout=None):
        captured.update(json or {})
        return _Resp()

    monkeypatch.setattr(httpx, "post", fake_post)

    class _S:
        smtp_host = ""
        smtp_password = "tok"
        smtp_from_name = "PorterChain"
        zeptomail_api_url = "https://api.zeptomail.ca/v1.1/email"
        jwt_secret = "test-secret"
        porterchain_api_url = "https://api.example.test"
        unsubscribe_mailbox = "unsubscribe@example.test"

        def smtp_from_for(self, _alias):
            return "noreply@example.test"

        def resolve_mail_transport(self):
            return "https"

    monkeypatch.setattr(ds, "get_platform_settings", lambda: _S())
    monkeypatch.setattr("porterchain_api.notification_engine.bounce.address_is_bounced", lambda *_a: False)
    ds.DeliveryService()._send_email(
        "someone@example.test",
        "merchant_welcome" if category == "marketing" else "delivered",
        {"category": category, "recipient_type": "merchant", "recipient_id": "m-1", "order_number": "O-1"},
    )
    return captured


def test_marketing_email_has_one_click_unsubscribe_headers(monkeypatch) -> None:
    payload = _zepto_payload(monkeypatch, "marketing")
    headers = payload["mime_headers"]
    assert headers["List-Unsubscribe-Post"] == "List-Unsubscribe=One-Click"
    assert "https://api.example.test/v1/notifications/unsubscribe?t=" in headers["List-Unsubscribe"]
    assert "mailto:unsubscribe@example.test" in headers["List-Unsubscribe"]


def test_transactional_email_has_no_unsubscribe_headers(monkeypatch) -> None:
    assert "mime_headers" not in _zepto_payload(monkeypatch, "tracking")


def test_unsubscribe_get_is_safe_and_post_turns_email_off(db) -> None:
    from fastapi.testclient import TestClient
    from porterchain_api.config import get_settings
    from porterchain_api.main import app
    from porterchain_api.notification_engine.models import NotificationPreference
    from porterchain_api.notification_engine.unsubscribe import make_token

    uid = str(uuid4())
    token = make_token(get_settings().jwt_secret, role="merchant", user_id=uid, category="marketing")
    client = TestClient(app)
    page = client.get("/v1/notifications/unsubscribe", params={"t": token})
    assert page.status_code == 200 and "<form" in page.text
    assert db.query(NotificationPreference).filter_by(user_id=uid).first() is None
    done = client.post("/v1/notifications/unsubscribe", params={"t": token}, data={"List-Unsubscribe": "One-Click"})
    assert done.status_code == 200
    db.expire_all()
    pref = db.query(NotificationPreference).filter_by(user_id=uid, category="marketing").one()
    assert pref.email_enabled is False
    assert client.post("/v1/notifications/unsubscribe", params={"t": token + "x"}).status_code == 400


# --- ops alert, webhook prerequisite --------------------------------------------------


def test_dead_letter_burst_alerts_ops_once_per_hour(db, monkeypatch) -> None:
    from porterchain_api.notification_engine import health_alert

    calls: list[list[dict]] = []
    monkeypatch.setattr(
        health_alert,
        "notification_health",
        lambda _db, now=None: {"dead_letter": 7, "failed": 7, "sent": 3, "attempts": 10, "failure_rate": 0.7},
    )
    monkeypatch.setattr(
        "porterchain_api.platform.staff_notify.dispatch_staff_specs", lambda _db, specs, **_k: calls.append(specs)
    )
    db.query(NotificationRecord).filter(NotificationRecord.template_key == "notification_health_alert").delete()
    db.commit()
    out = health_alert.check_and_alert(db)
    assert out["alerted"] is True and {s["channel"] for s in calls[0]} == {"in_app", "email"}
    db.add(
        NotificationRecord(
            template_key="notification_health_alert",
            channel="in_app",
            recipient_type="admin",
            recipient_id="a",
            title="t",
            body="b",
            status="sent",
        )
    )
    db.commit()
    again = health_alert.check_and_alert(db)
    assert again.get("cooldown") is True and len(calls) == 1
    db.query(NotificationRecord).filter(NotificationRecord.template_key == "notification_health_alert").delete()
    db.commit()


def test_bounce_webhook_fails_closed_without_secret_in_production(monkeypatch) -> None:
    from fastapi.testclient import TestClient
    from porterchain_api.main import app
    from porterchain_api.routers import zeptomail_webhook

    class _S:
        zeptomail_webhook_secret = ""
        app_env = "production"

    monkeypatch.setattr(zeptomail_webhook, "get_settings", lambda: _S())
    resp = TestClient(app).post("/v1/public/mail/zeptomail", json={"event_name": ["hardbounce"]})
    assert resp.status_code == 503


# --- reschedule routing --------------------------------------------------------------


def test_reschedule_routes_to_merchant_admin_driver_and_receiver(db, merchant_ctx, settings, driver) -> None:
    from porterchain_api.customer_experience.events import process_order_event
    from porterchain_api.notification_engine.event_router import _specs_for_event

    order = _order(db, merchant_ctx, state="DISPATCH_READY", driver_id=driver.id)
    specs = _specs_for_event(
        "order.rescheduled",
        {
            "order_id": order.id,
            "merchant_id": order.merchant_id,
            "merchant_email": "m@example.test",
            "driver_id": driver.id,
            "customer_id": "c-1",
            "window_label": "Sat 10-12",
        },
    )
    got = {(s["recipient_type"], s["channel"]) for s in specs}
    assert {
        ("merchant", "in_app"),
        ("merchant", "email"),
        ("admin", "in_app"),
        ("admin", "email"),
        ("driver", "in_app"),
        ("customer", "in_app"),
    } <= got
    process_order_event(
        db,
        settings,
        "order.rescheduled",
        {"order_id": order.id, "window_code": "w1", "window_label": "Sat 10:00-12:00"},
    )
    rows = _rows(db, recipient_id=order.id, template_key="cx_rescheduled")
    assert len(rows) == 1 and "Sat 10:00-12:00" in rows[0].body
