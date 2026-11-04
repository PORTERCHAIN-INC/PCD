"""L180–L183: direct-booking receiver copy, proof wording, one invoice email, per-stop ETA, ASAP SLA."""

from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace

from porterchain_api.booking_engine.order_sla import order_sla_status, resolve_sla_deadline
from porterchain_api.notification_engine.event_router import _specs_for_event
from porterchain_api.notification_engine.receiver_emails import render_receiver_email

BASE = {"audience": "receiver", "tracking_number": "PC-TEST-1", "public_track_url": "https://x/t"}


def _render(template: str, **ctx):
    return render_receiver_email(template, {**BASE, **ctx})


def test_direct_booking_never_says_your_sender():
    for ctx in ({"direct_booking": True}, {}, {"merchant_name": "Your sender"}):
        subject, text, html = _render("delivered", proof_types=["photo"], **ctx)
        assert "sender" not in subject.lower()
        assert "Your sender" not in text and "Your Your" not in text
        assert "From:" not in text
        assert "Your sender" not in html
        assert subject == "Your delivery has arrived · PC-TEST-1"
        assert "Your parcel was delivered. The delivery photo is one tap away." in text


def test_direct_booking_french():
    subject, text, _ = _render("delivered", direct_booking=True, lang="fr", proof_types=["signature"])
    assert "expéditeur" not in subject.lower()
    assert "Votre colis a été livré. La signature est à portée de clic." in text


def test_merchant_booking_keeps_merchant_name():
    subject, text, _ = _render("delivered", merchant_name="Bloor Pharmacy", proof_types=["photo", "signature"])
    assert subject == "Your delivery has arrived · Bloor Pharmacy · PC-TEST-1"
    assert "Your Bloor Pharmacy parcel was delivered. Photo and signature proof are one tap away." in text
    assert "From: Bloor Pharmacy" in text


def test_proof_lists_only_what_was_captured():
    _, photo, _ = _render("delivered", merchant_name="M", proof_types=["photo"])
    assert "signature" not in photo.split("--")[0].lower()
    _, none, _ = _render("delivered", merchant_name="M", proof_types=[])
    assert "one tap away" not in none
    _, unknown, _ = _render("delivered", merchant_name="M")
    assert "Proof of delivery is one tap away." in unknown


def test_other_direct_kinds_have_no_placeholder_gaps():
    for tpl in ("order_booked", "parcel_picked_up", "cx_out_for_delivery", "order_cancelled"):
        _, text, _ = _render(tpl, direct_booking=True)
        assert "  " not in text.split("\n")[2]
        assert "Your sender" not in text


def _invoice_specs(**extra):
    payload = {"customer_id": "c1", "email": "c@x.test", "order_id": "o1", **extra}
    return [s for s in _specs_for_event("order.invoiced", payload) if s.get("template_key") == "invoice_ready"]


def test_invoice_ready_once_per_invoice():
    assert _invoice_specs(), "first invoice event emails the customer"
    assert _invoice_specs(invoice_already_notified=True) == []


def test_eta_targets_the_next_stop():
    from porterchain_driver.navigation import eta_stop_kind

    for state in ("DRIVER_ASSIGNED", "DRIVER_ACCEPTED", "DRIVER_EN_ROUTE", "AT_PICKUP"):
        assert eta_stop_kind(state) == "pickup"
    for state in ("PICKED_UP", "IN_TRANSIT", "AT_DESTINATION"):
        assert eta_stop_kind(state) == "dropoff"


def test_asap_express_with_pickup_lead_is_not_at_risk():
    created = datetime(2026, 11, 3, 18, 9)
    order = SimpleNamespace(
        state="DISPATCH_READY",
        order_type="EXPRESS",
        created_at=created,
        scheduled_at=created + timedelta(minutes=19),
        compliance_metadata={},
        sla_deadline_at=None,
    )
    assert resolve_sla_deadline(order) == created + timedelta(minutes=19, hours=4)
    assert order_sla_status(order, created + timedelta(minutes=4)) == "ok"


def test_scheduled_order_keeps_its_appointment():
    created = datetime(2026, 11, 3, 18, 0)
    order = SimpleNamespace(
        state="DISPATCH_READY", order_type="SCHEDULED", created_at=created,
        scheduled_at=created + timedelta(days=1), compliance_metadata={}, sla_deadline_at=None,
    )
    assert resolve_sla_deadline(order) == created + timedelta(days=1)
