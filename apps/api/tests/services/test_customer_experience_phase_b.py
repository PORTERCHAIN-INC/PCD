"""Phase B — recipient experience: branded tracking, proactive notifications,
self-scheduling / instructions, bulky gate and the failed-delivery policy.

No real message may leave the box: DeliveryService senders are replaced with
tripwires and every assertion is on queued NotificationRecords only.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

import porterchain_api.main  # noqa: F401 — registers every ORM model (FK targets)
from porterchain_api.booking_engine.numbers import generate_order_number, generate_tracking_number
from porterchain_api.booking_models import Order, OrderEvent
from porterchain_api.customer_experience import scheduling, service
from porterchain_api.customer_experience.events import eta_payload_is_close, process_order_event
from porterchain_api.customer_experience.links import make_manage_token, manage_url, read_manage_token
from porterchain_api.customer_experience.notifications import in_quiet_hours, notify
from porterchain_api.customer_experience.reattempt import CONTRACT_FLAG, record_failure
from porterchain_api.customer_experience.settings import (
    apply_preset,
    cx_for_merchant,
    default_cx,
    merge_patch,
    normalize_cx,
    sanitize_hex,
)
from porterchain_api.customer_experience.tracking_view import build_experience
from porterchain_api.notification_engine.models import NotificationRecord

NOON_ET = datetime(2026, 10, 9, 16, 0, tzinfo=UTC)  # 12:00 America/Toronto
LATE_ET = datetime(2026, 10, 10, 2, 30, tzinfo=UTC)  # 22:30 America/Toronto


@pytest.fixture(autouse=True)
def no_real_sends(monkeypatch):
    """Tripwire: any attempt to actually deliver email/SMS/push fails the test."""
    from porterchain_api.notification_engine import delivery_service as ds

    def _boom(*_a, **_k):
        raise AssertionError("real notification send attempted in a test")

    for name in ("_send_email", "_send_sms", "_send_push", "_send_email_zeptomail_https", "_send_email_smtp", "_send_sms_twilio"):
        if hasattr(ds.DeliveryService, name):
            monkeypatch.setattr(ds.DeliveryService, name, _boom)
    monkeypatch.setattr(ds, "deliver_notification", _boom)


def _set_cx(db, merchant, patch: dict) -> dict:
    profile = dict(merchant.profile or {})
    settings = dict(profile.get("settings") or {})
    settings["customer_experience"] = normalize_cx(merge_patch(default_cx(), patch))
    profile["settings"] = settings
    merchant.profile = profile
    db.commit()
    return settings["customer_experience"]


def _order(db, merchant_ctx, *, state="IN_TRANSIT", driver_id=None, meta=None, sandbox=False) -> Order:
    order = Order(
        order_number=generate_order_number(),
        tracking_number=generate_tracking_number(),
        state=state,
        merchant_id=merchant_ctx.merchant.id,
        amount_cents=3200,
        currency="cad",
        pickup={"formatted": "100 King St W, Toronto", "postal": "M5X 1A1", "lat": 43.65, "lng": -79.38},
        dropoff={
            "formatted": "200 Bay St, Toronto",
            "postal": "M5J 2J2",
            "lat": 43.645,
            "lng": -79.38,
            "contact_phone": "+1 416 555 0100",
            "contact_name": "Jordan Receiver",
        },
        scheduled_at=datetime.now(UTC),
        assigned_driver_id=driver_id,
        is_sandbox=sandbox,
        compliance_metadata={
            "consignee": {"email": "receiver@example.test"},
            "package_type": "looseParcel",
            "vehicle_class": "cargo_van",
            **(meta or {}),
        },
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


def _event(db, order, from_state, to_state, *, at=None) -> OrderEvent:
    ev = OrderEvent(
        order_id=order.id,
        event_type=f"order.{to_state.lower()}",
        from_state=from_state,
        to_state=to_state,
        payload={},
        occurred_at=at or datetime.now(UTC),
    )
    db.add(ev)
    db.commit()
    return ev


def _records(db, order) -> list[NotificationRecord]:
    return (
        db.query(NotificationRecord)
        .filter(NotificationRecord.recipient_type == "consignee", NotificationRecord.recipient_id == order.id)
        .all()
    )


def _all_on() -> dict:
    return {
        "tracking": {"branded_page": True, "support_email": "help@shop.test", "show_pod_photo": True},
        "notifications": {"enabled": True, "channels": {"email": True, "sms": True, "whatsapp": True}},
        "self_service": {"enabled": True},
    }


# --- settings ---------------------------------------------------------------


def test_defaults_keep_every_customer_facing_change_off(merchant_ctx) -> None:
    cfg = cx_for_merchant(merchant_ctx.merchant)
    assert cfg["tracking"]["branded_page"] is False
    assert cfg["notifications"]["enabled"] is False
    assert cfg["self_service"]["enabled"] is False
    assert cfg["reattempt"]["enabled"] is False
    assert cfg["delivery_rules"]["require_schedule_for_bulky"] is False
    assert cfg["notifications"]["channels"] == {"email": True, "sms": False, "whatsapp": False}


@pytest.mark.parametrize(
    "raw,path",
    [
        ({"notifications": {"eta_minutes": 1}}, "notifications.eta_minutes"),
        ({"notifications": {"quiet_hours": {"start": "25:00"}}}, "notifications.quiet_hours.start"),
        ({"tracking": {"help_url": "http://insecure"}}, "tracking.help_url"),
        ({"tracking": {"support_email": "nope"}}, "tracking.support_email"),
        ({"reattempt": {"max_attempts": 9}}, "reattempt.max_attempts"),
        ({"self_service": "yes"}, "self_service"),
    ],
)
def test_normalize_rejects_bad_values(raw, path) -> None:
    with pytest.raises(ValueError, match=f"cx_invalid:{path}"):
        normalize_cx(raw)


def test_presets_and_rts_clamp() -> None:
    pharmacy = apply_preset(default_cx(), "pharmacy")
    assert pharmacy["delivery_rules"]["safe_place_allowed"] is False
    assert pharmacy["delivery_rules"]["id_required"] is True
    furniture = apply_preset(default_cx(), "furniture")
    assert furniture["delivery_rules"]["require_schedule_for_bulky"] is True
    assert furniture["self_service"]["enabled"] is True
    clamped = normalize_cx({"reattempt": {"max_attempts": 3, "return_to_sender_after": 1}})
    assert clamped["reattempt"]["return_to_sender_after"] == 3
    assert sanitize_hex("#ABCDEF") == "#abcdef"
    assert sanitize_hex("red", "#000000") == "#000000"
    with pytest.raises(ValueError):
        apply_preset(default_cx(), "unknown")


# --- signed links -------------------------------------------------------------


def test_manage_token_roundtrip_tamper_and_expiry() -> None:
    now = datetime(2026, 10, 9, tzinfo=UTC)
    token = make_manage_token("secret-a", order_id="o1", tracking_number="PC123", ttl_hours=2, now=now)
    claims = read_manage_token("secret-a", token, tracking_number="PC123", now=now + timedelta(hours=1))
    assert claims["order_id"] == "o1"
    with pytest.raises(ValueError, match="link_invalid"):
        read_manage_token("secret-b", token, now=now)
    with pytest.raises(ValueError, match="link_invalid"):
        read_manage_token("secret-a", token, tracking_number="PC999", now=now)
    with pytest.raises(ValueError, match="link_invalid"):
        read_manage_token("secret-a", token[:-2] + "xx", now=now)
    with pytest.raises(ValueError, match="link_invalid"):
        read_manage_token("secret-a", "garbage", now=now)
    with pytest.raises(ValueError, match="link_expired"):
        read_manage_token("secret-a", token, now=now + timedelta(hours=3))
    url = manage_url("https://porterchain.test/", "PC123", token)
    assert url.startswith("https://porterchain.test/track/PC123/manage?t=")


# --- branded tracking page ------------------------------------------------------


def test_experience_off_by_default_returns_plain_marker(db, merchant_ctx) -> None:
    order = _order(db, merchant_ctx)
    assert build_experience(db, order) == {"enhanced": False, "tracking_number": order.tracking_number}


def test_experience_branded_timeline_masked_and_privacy_safe(db, merchant_ctx, driver) -> None:
    driver.full_name = "Samantha Kowalski"
    driver.phone = "+14165550199"
    profile = dict(merchant_ctx.merchant.profile or {})
    profile["settings"] = {"branding": {"primary_color": "#112233", "logo_url": "https://cdn.test/logo.png"}}
    merchant_ctx.merchant.profile = profile
    db.commit()
    _set_cx(db, merchant_ctx.merchant, _all_on())
    order = _order(db, merchant_ctx, driver_id=driver.id, meta={"route_sequence": 3})
    ahead1 = _order(db, merchant_ctx, driver_id=driver.id, meta={"route_sequence": 1})
    _order(db, merchant_ctx, driver_id=driver.id, meta={"route_sequence": 5})
    t0 = datetime.now(UTC) - timedelta(hours=2)
    _event(db, order, "BOOKED", "DISPATCH_READY", at=t0)
    _event(db, order, "AT_PICKUP", "PICKED_UP", at=t0 + timedelta(minutes=30))
    _event(db, order, "PICKED_UP", "IN_TRANSIT", at=t0 + timedelta(minutes=40))

    exp = build_experience(db, order)
    assert exp["enhanced"] is True
    assert exp["branding"]["primary_color"] == "#112233"
    assert [i["code"] for i in exp["timeline"]] == ["booked", "picked_up", "out_for_delivery"]
    assert [s["done"] for s in exp["progress"]] == [True, True, True, False]
    assert exp["driver"] == {"name": "Samantha K."}
    assert exp["stops_away"] == 1
    assert exp["help"]["email"] == "help@shop.test"
    assert exp["self_service"]["available"] is True
    blob = str(exp)
    for secret in ("Kowalski", "4165550199", "200 Bay St", "receiver@example.test", "Jordan", "looseParcel"):
        assert secret not in blob
    # Driver finishes the earlier stop -> this order is next.
    ahead1.state = "DELIVERED"
    db.commit()
    assert build_experience(db, order)["stops_away"] == 0


def test_experience_pod_photos_need_signed_link(db, merchant_ctx, driver, settings) -> None:
    from porterchain_api.driver_models import DriverStopMeta

    _set_cx(db, merchant_ctx.merchant, _all_on())
    order = _order(db, merchant_ctx, state="DELIVERED", driver_id=driver.id)
    _event(db, order, "AT_DESTINATION", "DELIVERED")
    db.add(
        DriverStopMeta(
            order_id=order.id,
            driver_id=driver.id,
            meta={
                "proofs": [{"type": "photo", "value": "https://cdn.test/pod.jpg"}, {"type": "signature", "value": "sig"}],
                "received_by": "Jordan Receiver",
            },
        )
    )
    db.commit()
    public = service.experience(db, settings, order.tracking_number)
    pod = public["proof_of_delivery"]
    assert pod["proof_types"] == ["photo", "signature"]
    assert pod["received_by"] == "J. R."
    assert pod["photos"] == []
    token = make_manage_token(settings.jwt_secret, order_id=order.id, tracking_number=order.tracking_number)
    assert service.manage_pod(db, settings, order.tracking_number, token)["proof_of_delivery"]["photos"] == [
        "https://cdn.test/pod.jpg"
    ]


def test_experience_hides_sandbox_orders(db, merchant_ctx, settings) -> None:
    _set_cx(db, merchant_ctx.merchant, _all_on())
    order = _order(db, merchant_ctx, sandbox=True)
    with pytest.raises(LookupError):
        service.experience(db, settings, order.tracking_number)


# --- proactive notifications ------------------------------------------------------


def test_notifications_off_by_default_queue_nothing(db, merchant_ctx, settings) -> None:
    order = _order(db, merchant_ctx)
    res = notify(db, settings, order, "out_for_delivery", now=NOON_ET)
    assert res["skipped"] == {"all": "disabled"}
    assert _records(db, order) == []


def test_out_for_delivery_queues_email_and_sms_once(db, merchant_ctx, settings) -> None:
    _set_cx(db, merchant_ctx.merchant, _all_on())
    order = _order(db, merchant_ctx)
    res = notify(db, settings, order, "out_for_delivery", now=NOON_ET)
    db.commit()
    assert sorted(res["queued"]) == ["email", "sms"]
    assert res["skipped"] == {"whatsapp": "channel_unavailable"}
    rows = _records(db, order)
    assert {r.channel for r in rows} == {"email", "sms"}
    assert all(r.status == "queued" and r.template_key == "cx_out_for_delivery" for r in rows)
    email = next(r for r in rows if r.channel == "email")
    assert email.recipient_address == "receiver@example.test"
    assert "/track/" in email.body and "/manage?t=" in email.body
    assert "No marketing" in email.body and merchant_ctx.merchant.company_name in email.body
    again = notify(db, settings, order, "out_for_delivery", now=NOON_ET)
    assert again["skipped"] == {"all": "duplicate"}
    assert len(_records(db, order)) == 2


def test_quiet_hours_hold_sms_but_not_email(db, merchant_ctx, settings) -> None:
    cfg = _set_cx(db, merchant_ctx.merchant, _all_on())
    assert in_quiet_hours(cfg["notifications"]["quiet_hours"], LATE_ET)
    assert not in_quiet_hours(cfg["notifications"]["quiet_hours"], NOON_ET)
    order = _order(db, merchant_ctx)
    res = notify(db, settings, order, "delivered", now=LATE_ET)
    assert res["queued"] == ["email"]
    assert res["skipped"]["sms"] == "quiet_hours"


def test_sandbox_orders_never_notify(db, merchant_ctx, settings) -> None:
    _set_cx(db, merchant_ctx.merchant, _all_on())
    order = _order(db, merchant_ctx, sandbox=True)
    assert notify(db, settings, order, "delivered")["skipped"] == {"all": "sandbox"}
    assert process_order_event(db, settings, "order.delivered", {"order_id": order.id}) == []


def test_event_hooks_eta_next_stop_delivered(db, merchant_ctx, settings, driver) -> None:
    _set_cx(db, merchant_ctx.merchant, {**_all_on(), "notifications": {"enabled": True, "channels": {"sms": False}}})
    mine = _order(db, merchant_ctx, driver_id=driver.id, meta={"route_sequence": 2})
    first = _order(db, merchant_ctx, driver_id=driver.id, meta={"route_sequence": 1})
    third = _order(db, merchant_ctx, driver_id=driver.id, meta={"route_sequence": 3})
    assert not eta_payload_is_close({"lat": 1})
    assert eta_payload_is_close({"eta_seconds": 600})

    # ETA ping far away -> nothing; ~15 min -> eta_20 once.
    process_order_event(db, settings, "order.tracking_updated", {"order_id": mine.id, "eta_seconds": 3600})
    assert _records(db, mine) == []
    process_order_event(db, settings, "order.tracking_updated", {"order_id": mine.id, "eta_seconds": 900})
    process_order_event(db, settings, "order.tracking_updated", {"order_id": mine.id, "eta_seconds": 600})
    eta_rows = [r for r in _records(db, mine) if r.template_key == "cx_eta_20"]
    assert len(eta_rows) == 1 and "15 minutes" in eta_rows[0].body

    # First stop delivered -> delivered note for it, "you're next" for mine (1 ahead before -> 0 now).
    first.state = "DELIVERED"
    db.commit()
    process_order_event(db, settings, "order.delivered", {"order_id": first.id})
    assert [r.template_key for r in _records(db, first)] == ["cx_delivered"]
    next_rows = [r for r in _records(db, mine) if r.template_key == "cx_next_stop"]
    assert len(next_rows) == 1 and "You're next!" in next_rows[0].body
    # Threshold 1: the third stop is 1 away -> also told.
    assert [r.template_key for r in _records(db, third)] == ["cx_next_stop"]


def test_event_router_runs_cx_hook_and_skips_sandbox(db, merchant_ctx, monkeypatch) -> None:
    from porterchain_api.notification_engine import event_router

    _set_cx(db, merchant_ctx.merchant, _all_on())
    order = _order(db, merchant_ctx)
    _event(db, order, "PICKED_UP", "IN_TRANSIT")
    event_router.handle_domain_event(
        {"event_type": "order.in_transit", "aggregate_type": "order", "aggregate_id": order.id, "payload": {}}
    )
    db.expire_all()
    assert {r.template_key for r in _records(db, order)} == {"cx_out_for_delivery"}
    sandbox = _order(db, merchant_ctx, sandbox=True)
    event_router.handle_domain_event(
        {"event_type": "order.in_transit", "aggregate_type": "order", "aggregate_id": sandbox.id, "payload": {}}
    )
    assert _records(db, sandbox) == []


# --- self-scheduling / instructions -------------------------------------------------


def test_self_service_disabled_rejects_link_actions(db, merchant_ctx, settings) -> None:
    order = _order(db, merchant_ctx, state="BOOKED")
    token = make_manage_token(settings.jwt_secret, order_id=order.id, tracking_number=order.tracking_number)
    with pytest.raises(ValueError, match="self_service_disabled"):
        service.manage_options(db, settings, order.tracking_number, token)


def test_choose_window_and_instructions(db, merchant_ctx, settings, monkeypatch) -> None:
    _set_cx(db, merchant_ctx.merchant, _all_on())
    order = _order(db, merchant_ctx, state="DISPATCH_READY")
    order.special_instructions = "Leave with concierge"
    db.commit()
    token = make_manage_token(settings.jwt_secret, order_id=order.id, tracking_number=order.tracking_number)
    opts = service.manage_options(db, settings, order.tracking_number, token)
    assert opts["can_reschedule"] is True and opts["windows"]
    pick = opts["windows"][-1]
    with pytest.raises(ValueError, match="window_unavailable"):
        service.manage_schedule(db, settings, order.tracking_number, token, "1999-01-01:pm")
    out = service.manage_schedule(db, settings, order.tracking_number, token, pick["code"])
    db.refresh(order)
    assert out["schedule"]["code"] == pick["code"]
    assert order.scheduled_at == datetime.fromisoformat(pick["window_start"])
    out = service.manage_instructions(
        db, settings, order.tracking_number, token, {"gate_code": "1234", "buzzer": "12", "safe_place": "back porch"}
    )
    assert out["instructions"]["gate_code"] == "1234"
    db.refresh(order)
    assert order.special_instructions.splitlines() == [
        "Leave with concierge",
        "[Recipient] gate code 1234; buzzer 12; safe place: back porch",
    ]
    # Re-edit replaces the recipient line instead of stacking.
    service.manage_instructions(db, settings, order.tracking_number, token, {"notes": "Ring twice"})
    db.refresh(order)
    assert order.special_instructions.splitlines() == ["Leave with concierge", "[Recipient] Ring twice"]
    exp = build_experience(db, order)
    assert exp["eta_window"]["source"] == "customer"
    assert "1234" not in str(exp)  # gate code never on the public page


def test_pharmacy_rules_block_safe_place(db, merchant_ctx, settings) -> None:
    cfg = apply_preset(normalize_cx(_all_on()), "pharmacy")
    _set_cx(db, merchant_ctx.merchant, cfg)
    order = _order(db, merchant_ctx, state="DISPATCH_READY")
    token = make_manage_token(settings.jwt_secret, order_id=order.id, tracking_number=order.tracking_number)
    with pytest.raises(ValueError, match="safe_place_not_allowed"):
        service.manage_instructions(db, settings, order.tracking_number, token, {"safe_place": "mailbox"})
    assert service.manage_options(db, settings, order.tracking_number, token)["rules"]["id_required"] is True


def test_token_for_other_order_is_rejected(db, merchant_ctx, settings) -> None:
    _set_cx(db, merchant_ctx.merchant, _all_on())
    a = _order(db, merchant_ctx, state="BOOKED")
    b = _order(db, merchant_ctx, state="BOOKED")
    token = make_manage_token(settings.jwt_secret, order_id=a.id, tracking_number=b.tracking_number)
    with pytest.raises(ValueError, match="link_invalid"):
        service.manage_options(db, settings, b.tracking_number, token)


def test_bulky_gate_holds_until_recipient_schedules(db, merchant_ctx, settings, monkeypatch) -> None:
    from porterchain_api.merchant_engine.booking_service import MerchantBookingService
    from porterchain_api.schemas_merchant import AddressInput, MerchantBookDeliveryRequest

    merchant_ctx.merchant.payment_terms = "NET_30"
    _set_cx(db, merchant_ctx.merchant, apply_preset(normalize_cx(_all_on()), "furniture"))
    dispatched: list[str] = []
    monkeypatch.setattr(
        "porterchain_api.merchant_engine.booking_service.transition_to_dispatch_ready",
        lambda *_a, **_k: dispatched.append("booking"),
    )
    monkeypatch.setattr(
        "porterchain_api.booking_engine.order_transitions.transition_to_dispatch_ready",
        lambda *_a, **_k: dispatched.append("recipient"),
    )
    body = MerchantBookDeliveryRequest(
        pickup=AddressInput(formatted="100 King St W, Toronto", postal="M5X 1A1", lat=43.65, lng=-79.38),
        dropoff=AddressInput(formatted="200 Bay St, Toronto", postal="M5J 2J2", lat=43.645, lng=-79.38),
        scheduled_at=datetime.now(UTC),
        vehicle_class="cargo_van",
        package_type="furniture",
        consignee_email="buyer@example.test",
    )
    order = MerchantBookingService().create_shipment(db, settings, merchant_ctx, body)
    assert order.state == "BOOKED"
    assert dispatched == []
    assert (order.compliance_metadata or {}).get("cx", {}).get("awaiting_schedule") is True
    assert "cx_schedule_request" in {r.template_key for r in _records(db, order)}
    token = make_manage_token(settings.jwt_secret, order_id=order.id, tracking_number=order.tracking_number)
    opts = service.manage_options(db, settings, order.tracking_number, token)
    assert opts["awaiting_schedule"] is True
    service.manage_schedule(db, settings, order.tracking_number, token, opts["windows"][0]["code"])
    assert dispatched == ["recipient"]

    # Non-bulky parcels from the same merchant dispatch immediately.
    plain = MerchantBookingService().create_shipment(
        db, settings, merchant_ctx, body.model_copy(update={"package_type": "looseParcel"})
    )
    assert dispatched == ["recipient", "booking"]
    assert not (plain.compliance_metadata or {}).get("cx", {}).get("awaiting_schedule")


def test_default_merchant_booking_still_dispatches(db, merchant_ctx, settings, monkeypatch) -> None:
    from porterchain_api.merchant_engine.booking_service import MerchantBookingService
    from porterchain_api.schemas_merchant import AddressInput, MerchantBookDeliveryRequest

    merchant_ctx.merchant.payment_terms = "NET_30"
    db.commit()
    dispatched: list[str] = []
    monkeypatch.setattr(
        "porterchain_api.merchant_engine.booking_service.transition_to_dispatch_ready",
        lambda *_a, **_k: dispatched.append("booking"),
    )
    body = MerchantBookDeliveryRequest(
        pickup=AddressInput(formatted="100 King St W, Toronto", postal="M5X 1A1", lat=43.65, lng=-79.38),
        dropoff=AddressInput(formatted="200 Bay St, Toronto", postal="M5J 2J2", lat=43.645, lng=-79.38),
        scheduled_at=datetime.now(UTC),
        vehicle_class="cargo_van",
        package_type="furniture",
        consignee_email="buyer@example.test",
    )
    # Regression: a failed consignee-tracking queue write must not 500 the booking.
    order = MerchantBookingService().create_shipment(db, settings, merchant_ctx, body)
    assert dispatched == ["booking"]
    assert order.state == "BOOKED" and not (order.compliance_metadata or {}).get("cx")


# --- failed delivery / re-attempt policy -------------------------------------------------


def test_failure_policy_off_counts_only(db, merchant_ctx) -> None:
    order = _order(db, merchant_ctx, state="FAILED")
    _event(db, order, "AT_DESTINATION", "FAILED")
    decision = record_failure(db, order)
    assert decision["action"] == "manual" and decision["attempts"] == 1
    assert order.state == "FAILED"
    # Idempotent for the same FAILED transition.
    assert record_failure(db, order)["attempts"] == 1


def test_reattempt_then_return_to_sender(db, merchant_ctx, settings, monkeypatch) -> None:
    _set_cx(db, merchant_ctx.merchant, {**_all_on(), "reattempt": {"enabled": True, "max_attempts": 2, "return_to_sender_after": 2}})
    order = _order(db, merchant_ctx, state="FAILED")
    _event(db, order, "AT_DESTINATION", "FAILED")
    results = process_order_event(db, settings, "order.failed", {"order_id": order.id})
    db.refresh(order)
    decision = order.compliance_metadata["cx"]["reattempt"]
    assert decision["action"] == "reattempt" and decision["attempts"] == 1
    assert decision["quote"]["leg"] == "reattempt"
    assert decision["quote"]["final_cents"] > 0  # priced by the merchant's own engine config
    attempted = [
        r for r in _records(db, order) if r.template_key == "cx_attempted" and r.channel == "email"
    ]  # SMS may also queue when an SMS provider is configured
    assert len(attempted) == 1 and "/manage?t=" in attempted[0].body
    assert any(r["kind"] == "attempted" for r in results)

    # Recipient picks a new window -> back to DISPATCH_READY (re-attempt).
    token = make_manage_token(settings.jwt_secret, order_id=order.id, tracking_number=order.tracking_number)
    opts = service.manage_options(db, settings, order.tracking_number, token)
    assert opts["can_reschedule"] is True
    service.manage_schedule(db, settings, order.tracking_number, token, opts["windows"][0]["code"])
    db.refresh(order)
    assert order.state == "DISPATCH_READY"

    # Second failed attempt -> return to sender, priced return leg, distinct notification.
    order.state = "FAILED"
    db.commit()
    _event(db, order, "AT_DESTINATION", "FAILED", at=datetime.now(UTC) + timedelta(seconds=5))
    process_order_event(db, settings, "order.failed", {"order_id": order.id})
    db.refresh(order)
    assert order.state == "RETURN_TO_SENDER"
    decision = order.compliance_metadata["cx"]["reattempt"]
    assert decision["action"] == "return_to_sender" and decision["attempts"] == 2
    assert decision["quote"]["leg"] == "return_to_sender"
    attempted = [
        r for r in _records(db, order) if r.template_key == "cx_attempted" and r.channel == "email"
    ]  # SMS may also queue when an SMS provider is configured
    assert len(attempted) == 2
    assert build_experience(db, order)["returning_to_sender"] is True


def test_failure_at_pickup_is_not_a_delivery_attempt(db, merchant_ctx) -> None:
    _set_cx(db, merchant_ctx.merchant, {"reattempt": {"enabled": True}})
    order = _order(db, merchant_ctx, state="FAILED")
    _event(db, order, "AT_PICKUP", "FAILED")
    assert record_failure(db, order)["attempts"] == 0


def test_contract_merchant_flags_unmodelled_failed_delivery_rules(db, merchant_ctx) -> None:
    merchant_ctx.merchant.pricing_config = {"schedule": {"contract_schedule": "kaylulu-2026-09"}}
    db.commit()
    order = _order(db, merchant_ctx, state="FAILED")
    _event(db, order, "IN_TRANSIT", "FAILED")
    assert CONTRACT_FLAG in record_failure(db, order)["flags"]


# --- HTTP surface ---------------------------------------------------------------


@pytest.fixture
def client(db, settings, merchant_ctx):
    from fastapi.testclient import TestClient

    from porterchain_api.auth.merchant import get_merchant_context
    from porterchain_api.config import get_settings
    from porterchain_api.db import get_db
    from porterchain_api.main import app

    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_merchant_context] = lambda: merchant_ctx
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_http_public_experience_and_manage(client, db, merchant_ctx, settings) -> None:
    assert client.get(f"/v1/orders/NOPE{uuid4().hex[:6]}/experience").status_code == 404
    order = _order(db, merchant_ctx, state="DISPATCH_READY")
    assert client.get(f"/v1/orders/{order.tracking_number}/experience").json()["enhanced"] is False
    _set_cx(db, merchant_ctx.merchant, _all_on())
    assert client.get(f"/v1/orders/{order.tracking_number}/experience").json()["enhanced"] is True

    path = f"/v1/delivery-manage/{order.tracking_number}"
    assert client.get(path).status_code == 422  # header required
    assert client.get(path, headers={"X-Manage-Token": "bad.token"}).status_code == 403
    expired = make_manage_token(
        settings.jwt_secret,
        order_id=order.id,
        tracking_number=order.tracking_number,
        now=datetime.now(UTC) - timedelta(days=30),
    )
    res = client.get(path, headers={"X-Manage-Token": expired})
    assert res.status_code == 410 and res.json()["detail"]["code"] == "link_expired"
    token = make_manage_token(settings.jwt_secret, order_id=order.id, tracking_number=order.tracking_number)
    opts = client.get(path, headers={"X-Manage-Token": token}).json()
    code = opts["windows"][0]["code"]
    res = client.post(f"{path}/schedule", json={"window_code": code}, headers={"X-Manage-Token": token})
    assert res.status_code == 200 and res.json()["schedule"]["code"] == code
    res = client.post(f"{path}/instructions", json={"buzzer": "44"}, headers={"X-Manage-Token": token})
    assert res.status_code == 200 and res.json()["instructions"]["buzzer"] == "44"


def test_http_merchant_settings_roundtrip(client, db, merchant_ctx, monkeypatch) -> None:
    # Unlinked user -> SpiceDB module check denies (settings = Manager only).
    assert client.get("/v1/merchant/settings/customer-experience").status_code == 403
    checked: list[str] = []
    monkeypatch.setattr(
        "porterchain_api.routers.merchant.customer_experience.require_module",
        lambda _ctx, module: checked.append(module),
    )
    resp = client.get("/v1/merchant/settings/customer-experience")
    assert resp.status_code == 200, resp.text
    got = resp.json()
    assert got["settings"]["notifications"]["enabled"] is False
    assert set(got["presets"]) == {"furniture", "pharmacy"}
    res = client.put(
        "/v1/merchant/settings/customer-experience",
        json={"preset": "pharmacy", "notifications": {"enabled": True}, "tracking": {"branded_page": True}},
    )
    assert res.status_code == 200, res.text
    saved = res.json()["settings"]
    assert saved["notifications"]["enabled"] is True
    assert saved["delivery_rules"]["safe_place_allowed"] is False
    bad = client.put("/v1/merchant/settings/customer-experience", json={"notifications": {"eta_minutes": 999}})
    assert bad.status_code == 400
    db.refresh(merchant_ctx.merchant)
    assert cx_for_merchant(merchant_ctx.merchant)["tracking"]["branded_page"] is True
    assert set(checked) == {"settings"}
