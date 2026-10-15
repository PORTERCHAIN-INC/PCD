"""Booking attachments: pickup documents shared with the assigned driver only."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

import porterchain_api.main  # noqa: F401  (registers every mapper)
from porterchain_api.admin_models import Driver
from porterchain_api.booking_attachment_models import BookingAttachmentEvent
from porterchain_api.booking_attachments import service as svc
from porterchain_api.booking_engine.numbers import (
    generate_order_number,
    generate_tracking_number,
)
from porterchain_api.booking_models import Order
from porterchain_api.domain.merchant_states import MerchantStatus
from porterchain_api.merchant_engine.tracking_views import driver_info
from porterchain_api.merchant_models import Merchant

PDF = b"%PDF-1.4\n1 0 obj << /Title (Pickup Release) >> endobj\n%%EOF"
PNG = b"\x89PNG\r\n\x1a\n" + b"\0" * 32
HEIC = b"\0\0\0\x18ftypheic" + b"\0" * 32
MILTON = {
    "street": "8500 Mount Pleasant Wy",
    "unit": "Unit 1",
    "city": "Milton",
    "postal_code": "L9E 1J7",
}


def _merchant(db) -> Merchant:
    s = uuid4().hex[:8]
    m = Merchant(
        company_name=f"Att {s}",
        email=f"att-{s}@test.local",
        status=MerchantStatus.ACTIVE.value,
    )
    db.add(m)
    db.flush()
    return m


def _driver(db, phone="+14165550101") -> Driver:
    s = uuid4().hex[:8]
    d = Driver(
        email=f"d-{s}@test.local",
        full_name=f"Sam Driver{s}",
        status="APPROVED",
        clerk_user_id=f"clerk_d_{s}",
        phone=phone,
    )
    db.add(d)
    db.flush()
    return d


def _order(
    db, merchant_id, driver_id=None, state="DRIVER_ASSIGNED", pickup=None
) -> Order:
    o = Order(
        order_number=generate_order_number(),
        tracking_number=generate_tracking_number(),
        state=state,
        merchant_id=merchant_id,
        amount_cents=1000,
        currency="cad",
        pickup=pickup or dict(MILTON),
        dropoff={"street": "1 King St W", "postal_code": "M5H 1A1"},
        scheduled_at=datetime.now(UTC),
        assigned_driver_id=driver_id,
    )
    db.add(o)
    db.flush()
    return o


def test_type_checks():
    assert svc.validate_file(PDF) == "application/pdf"
    assert svc.validate_file(PNG) == "image/png"
    assert svc.validate_file(HEIC) == "image/heic"
    for bad, code in [
        (b"MZ\x90\0exe", "attachment_type_not_allowed"),
        (b"", "attachment_empty"),
        (b"%PDF-1.4 /JavaScript (app.alert(1))", "attachment_active_content"),
        (b"%PDF" + b"0" * (svc.MAX_BYTES + 1), "attachment_too_large"),
    ]:
        with pytest.raises(svc.AttachmentError, match=code):
            svc.validate_file(bad)


def test_suggest_kind_and_stop():
    assert svc.suggest_kind("Kaylulu_pickup_release.pdf") == "pickup_authorization"
    assert svc.suggest_kind("BOL-4412.pdf") == "bill_of_lading"
    assert svc.suggest_kind("customs_b3.pdf") == "customs"
    assert (
        svc.suggest_kind("scan.pdf", b"%PDF Delivery instructions: back door")
        == "delivery_instructions"
    )
    assert svc.DEFAULT_STOP["delivery_instructions"] == "dropoff"


def test_merchant_upload_driver_view_and_pickup_gate(db):
    m, d, other = _merchant(db), _driver(db), _driver(db)
    o = _order(db, m.id, d.id)
    out = svc.upload(
        db,
        owner_type="merchant",
        owner_id=m.id,
        actor_id="u1",
        order_id=o.id,
        data=PDF,
        filename="pickup_release.pdf",
    )
    assert (
        out["kind"] == "pickup_authorization"
        and out["stop"] == "pickup"
        and out["required_at_stop"]
    )

    listing = svc.list_for_driver(db, d.id, o.id)
    assert [i["id"] for i in listing["items"]] == [out["id"]]
    assert listing["pickup_checklist"][0]["label"] == "Show document to warehouse staff"
    with pytest.raises(PermissionError):
        svc.list_for_driver(db, other.id, o.id)
    with pytest.raises(PermissionError):
        svc.driver_download(db, other.id, out["id"])

    svc.assert_pickup_documents_shown(db, o)  # gate off by default: no raise
    with pytest.raises(svc.PickupDocumentNotShown):
        svc.assert_pickup_documents_shown(db, o, force=True)
    _, data = svc.driver_download(db, d.id, out["id"])
    assert data == PDF
    assert (
        svc.list_for_owner(db, "merchant", m.id, o.id)["items"][0]["status"]
        == "viewed_by_driver"
    )
    svc.mark_shown(db, d.id, out["id"], proof=PNG)
    svc.assert_pickup_documents_shown(db, o, force=True)  # shown: no raise
    owner_view = svc.list_for_owner(db, "merchant", m.id, o.id)["items"][0]
    assert owner_view["status"] == "shown_at_pickup" and owner_view["has_proof_photo"]

    actions = {
        e.action for e in db.query(BookingAttachmentEvent).filter_by(order_id=o.id)
    }
    assert {"uploaded", "viewed", "shown_at_stop"} <= actions
    staff = svc.list_for_staff(db, o.id)
    assert staff["items"][0]["uploaded_by"] == "merchant:u1" and staff["events"]


def test_other_merchant_cannot_see_or_attach(db):
    m, intruder = _merchant(db), _merchant(db)
    o = _order(db, m.id)
    with pytest.raises(LookupError):
        svc.list_for_owner(db, "merchant", intruder.id, o.id)
    with pytest.raises(LookupError):
        svc.upload(
            db,
            owner_type="merchant",
            owner_id=intruder.id,
            actor_id="x",
            order_id=o.id,
            data=PDF,
            filename="a.pdf",
        )


def test_editable_until_pickup_then_locked(db):
    m, d = _merchant(db), _driver(db)
    o = _order(db, m.id, d.id)
    att = svc.upload(
        db,
        owner_type="merchant",
        owner_id=m.id,
        actor_id="u",
        order_id=o.id,
        data=PDF,
        filename="bol.pdf",
    )
    svc.update(
        db,
        owner_type="merchant",
        owner_id=m.id,
        actor_id="u",
        attachment_id=att["id"],
        required_at_stop=False,
    )
    o.state = "PICKED_UP"
    db.flush()
    with pytest.raises(svc.AttachmentError, match="attachment_stop_closed"):
        svc.upload(
            db,
            owner_type="merchant",
            owner_id=m.id,
            actor_id="u",
            order_id=o.id,
            data=PDF,
            filename="x.pdf",
        )
    with pytest.raises(svc.AttachmentError, match="attachment_stop_closed"):
        svc.delete(
            db,
            owner_type="merchant",
            owner_id=m.id,
            actor_id="u",
            attachment_id=att["id"],
        )
    # Drop-off docs still allowed, and the driver no longer gets pickup docs.
    svc.upload(
        db,
        owner_type="merchant",
        owner_id=m.id,
        actor_id="u",
        order_id=o.id,
        data=PDF,
        filename="delivery instructions.pdf",
    )
    assert {i["stop"] for i in svc.list_for_driver(db, d.id, o.id)["items"]} == {
        "dropoff"
    }


def test_location_template_reused_on_future_bookings(db):
    m, d = _merchant(db), _driver(db)
    first = _order(db, m.id, d.id)
    svc.upload(
        db,
        owner_type="merchant",
        owner_id=m.id,
        actor_id="u",
        order_id=first.id,
        data=PDF,
        filename="milton_pickup.pdf",
        save_for_location=True,
    )
    later = _order(
        db,
        m.id,
        d.id,
        pickup={
            "street": "8500 Mount Pleasant Wy.",
            "unit": "unit 1",
            "postal_code": "l9e1j7",
            "city": "Milton",
        },
    )
    items = svc.list_for_driver(db, d.id, later.id)["items"]
    assert (
        len(items) == 1
        and items[0]["from_location_template"]
        and items[0]["required_at_stop"]
    )
    svc.list_for_driver(db, d.id, later.id)  # idempotent
    assert len(svc.list_for_owner(db, "merchant", m.id, later.id)["items"]) == 1
    elsewhere = _order(
        db, m.id, d.id, pickup={"street": "1 Other Rd", "postal_code": "M1M 1M1"}
    )
    assert svc.list_for_driver(db, d.id, elsewhere.id)["items"] == []


def test_retention_purges_bytes_keeps_audit(db):
    m, d = _merchant(db), _driver(db)
    o = _order(db, m.id, d.id)
    att = svc.upload(
        db,
        owner_type="merchant",
        owner_id=m.id,
        actor_id="u",
        order_id=o.id,
        data=PDF,
        filename="p.pdf",
    )
    o.state = "DELIVERED"
    db.flush()
    assert (
        svc.purge_expired(
            db, now=datetime.now(UTC) + timedelta(days=svc.RETENTION_DAYS + 1)
        )
        >= 1
    )
    staff = svc.list_for_staff(db, o.id)
    assert staff["items"][0]["purged"]
    with pytest.raises(LookupError):
        svc.staff_download(db, "staff1", att["id"])


def test_merchant_sees_driver_name_only(db):
    m, d = _merchant(db), _driver(db)
    o = _order(db, m.id, d.id)
    info = driver_info(db, o, None)
    assert info["name"] == d.full_name
    assert "phone" not in info and "email" not in info


def test_gate_env_flag(monkeypatch):
    monkeypatch.setenv("PICKUP_DOCUMENT_GATE", "on")
    assert svc.pickup_gate_enforced()
    monkeypatch.setenv("PICKUP_DOCUMENT_GATE", "off")
    assert not svc.pickup_gate_enforced()


def test_owner_lookup_by_tracking_number_is_scoped(db):
    m, other = _merchant(db), _merchant(db)
    o = _order(db, m.id)
    assert svc.owned_order(db, "merchant", m.id, o.tracking_number).id == o.id
    with pytest.raises(LookupError):
        svc.owned_order(db, "merchant", other.id, o.tracking_number)


def test_short_lived_single_use_link(db):
    m, d, other = _merchant(db), _driver(db), _driver(db)
    o = _order(db, m.id, d.id)
    att = svc.upload(
        db,
        owner_type="merchant",
        owner_id=m.id,
        actor_id="u",
        order_id=o.id,
        data=PDF,
        filename="p.pdf",
    )
    with pytest.raises(PermissionError):
        svc.driver_link(db, other.id, att["id"])
    token = svc.driver_link(db, d.id, att["id"])
    _, data = svc.redeem_link(db, token)
    assert data == PDF
    with pytest.raises(LookupError):
        svc.redeem_link(db, token)  # single use
    token2 = svc.driver_link(db, d.id, att["id"])
    from porterchain_api.booking_attachment_models import BookingAttachment

    row = db.get(BookingAttachment, att["id"])
    row.link_expires_at = datetime.now(UTC) - timedelta(seconds=1)
    db.flush()
    with pytest.raises(LookupError):
        svc.redeem_link(db, token2)
