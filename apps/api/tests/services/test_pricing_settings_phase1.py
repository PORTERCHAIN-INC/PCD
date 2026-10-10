"""Pricing settings phase 1 — super-admin edits, versions on quotes, multi-box
items (packages + labels), pickup checklist with missing-box reports, Shopify
multi-box lines.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.merchant_org import (
    apply_kaylulu_pricing_template,
    clone_pricing_from,
    merge_pricing_config,
)
from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.admin_engine.settings_bindings import resolve_writable_config_key
from porterchain_api.admin_engine.settings_service import AdminSettingsService
from porterchain_api.admin_models import AdminAuditLog, AdminUser
from porterchain_api.booking_models import DomainEvent, OrderException, Package
from porterchain_api.domain.admin_states import AdminRole
from porterchain_api.integrations.shopify_carrier_rates import (
    item_boxes,
    packages_from_items,
    parcels_from_items,
)
from porterchain_api.merchant_engine.package_service import PackageService
from porterchain_api.merchant_engine.scan_gate_service import PackagesIncomplete, ScanGateService
from porterchain_api.pricing_engine import get_pricing_service
from porterchain_api.domain.pricing_version import SUPER_ADMIN_ONLY
from porterchain_api.pricing_engine.repository import current_price_version as current_version
from porterchain_api.reporting.label_service import LabelService
from porterchain_api.reporting.qr_codec import encode_label_qr
from porterchain_pricing import GeoPoint, ParcelSpec, PricingRequest

IN = 2.54


def _admin(db: Session, role: AdminRole) -> AdminContext:
    suffix = uuid4().hex[:8]
    user = AdminUser(
        clerk_user_id=f"clerk_{role.value}_{suffix}",
        email=f"{role.value}-{suffix}@svc.test".lower(),
        name="Pricing test",
        role=role.value,
        is_active=True,
    )
    db.add(user)
    db.flush()
    return AdminContext(user=user, role=role)


def _version_n(db: Session) -> int:
    return int(current_version(db).split("-")[1])


# ── settings: super admin only, versioned, audited ─────────────────────


def test_super_admin_saves_price_book_and_version_bumps(db, admin_ctx) -> None:
    svc = AdminSettingsService()
    before = _version_n(db)
    book = svc.get_config_value(db, "pricing_book")
    book["stop_price_cents"] = book["stop_price_cents"] + 100
    svc.set_config(db, admin_ctx, "pricing_book", book, reason="phase1 test")
    assert _version_n(db) == before + 1
    audit = (
        db.query(AdminAuditLog)
        .filter(AdminAuditLog.action == "settings.config.update", AdminAuditLog.resource_id == "pricing_book")
        .order_by(AdminAuditLog.created_at.desc())
        .first()
    )
    assert audit is not None and audit.actor_user_id == admin_ctx.user.id
    assert audit.payload["new"]["stop_price_cents"] == book["stop_price_cents"]
    assert audit.payload["reason"] == "phase1 test"
    # Same value again: no new version.
    svc.set_config(db, admin_ctx, "pricing_book", book, reason="no-op")
    assert _version_n(db) == before + 1


def test_regular_admin_cannot_edit_pricing_keys(db) -> None:
    admin = _admin(db, AdminRole.ADMIN)
    svc = AdminSettingsService()
    for key in ("pricing_book", "driver_pay_plan", "pricing_gta_rate", "pricing_tax", "pricing_rate_card"):
        with pytest.raises(PermissionError, match=SUPER_ADMIN_ONLY):
            svc.set_config(db, admin, key, {}, reason="nope")
    # Non-pricing settings stay editable by admins.
    general = svc.get_config_value(db, "settings_general")
    svc.set_config(db, admin, "settings_general", general, reason="ok")


def test_new_keys_are_writable_with_a_reason() -> None:
    assert resolve_writable_config_key("pricing_book", reason="x") == "pricing_book"
    assert resolve_writable_config_key("driver_pay", reason="x") == "driver_pay_plan"
    with pytest.raises(ValueError, match="reason_required"):
        resolve_writable_config_key("pricing_book", reason=None)


def test_invalid_price_book_and_pay_plan_are_rejected(db, admin_ctx) -> None:
    svc = AdminSettingsService()
    with pytest.raises(ValueError, match="price_book_invalid"):
        svc.set_config(db, admin_ctx, "pricing_book", {"stop_price_cents": -5}, reason="bad")
    db.rollback()
    with pytest.raises(ValueError, match="driver_pay_invalid"):
        svc.set_config(db, admin_ctx, "driver_pay_plan", {"mode": "salary"}, reason="bad")
    db.rollback()
    saved = svc.set_config(db, admin_ctx, "driver_pay_plan", {"mode": "hourly"}, reason="ok")
    assert saved.value["hourly_cents"] == 2700
    assert saved.value["wave_block"]["block_hours"] == 4


def test_every_quote_carries_the_price_version(db, admin_ctx, merchant_ctx) -> None:
    svc = AdminSettingsService()
    book = svc.get_config_value(db, "pricing_book")
    book["dedicated"]["block_hours"] = 5
    svc.set_config(db, admin_ctx, "pricing_book", book, reason="version stamp")
    request = PricingRequest(
        pickup=GeoPoint(lat=43.65, lng=-79.38, postal="M5V 1A1"),
        dropoff=GeoPoint(lat=43.70, lng=-79.40, postal="M4P 1A1"),
        vehicle_class="cargo_van",
        merchant_id=merchant_ctx.merchant.id,
        distance_meters=8000,
    )
    pricing = get_pricing_service(db)
    for breakdown in (pricing.calculate_retail(request), pricing.calculate_merchant(request)):
        assert breakdown.metadata["price_version"] == current_version(db)
        assert pricing.to_api_breakdown(breakdown)["price_version"] == current_version(db)


# ── merchant pricing: guardrails ────────────────────────────────────────


def test_admin_may_flip_price_book_switches_but_not_prices(db, merchant_ctx) -> None:
    admin = _admin(db, AdminRole.ADMIN)
    mid = merchant_ctx.merchant.id
    before = _version_n(db)
    merge_pricing_config(db, admin, mid, {"price_book": {"enabled": True, "multi_box_as_one_item": True}})
    assert merchant_ctx.merchant.pricing_config["price_book"] == {"enabled": True, "multi_box_as_one_item": True}
    assert _version_n(db) == before + 1
    with pytest.raises(PermissionError, match=SUPER_ADMIN_ONLY):
        merge_pricing_config(db, admin, mid, {"price_book": {"stop_price_cents": 1}})
    db.rollback()
    with pytest.raises(PermissionError, match=SUPER_ADMIN_ONLY):
        merge_pricing_config(db, admin, mid, {"rate_card": {"liftgate_cents": 1}})
    db.rollback()
    with pytest.raises(PermissionError, match=SUPER_ADMIN_ONLY):
        clone_pricing_from(db, admin, mid, mid + "x")


def test_super_admin_overrides_price_merchant_quotes(db, admin_ctx, merchant_ctx) -> None:
    mid = merchant_ctx.merchant.id
    merge_pricing_config(
        db,
        admin_ctx,
        mid,
        {
            "pricing_model": "fsa",
            "schedule": {"fsa_miss": "refuse", "fuel_surcharge_percent": 0},
            "price_book": {"enabled": True, "stop_price_cents": 2000, "minimum": {"cents": 0}},
        },
    )
    sofa = {"length": 40 * IN, "width": 30 * IN, "height": 20 * IN}
    request = PricingRequest(
        pickup=GeoPoint(lat=43.65, lng=-79.38, postal="L9T 1A1"),
        dropoff=GeoPoint(lat=43.59, lng=-79.64, postal="L5M 1A1"),
        vehicle_class="cargo_van",
        merchant_id=mid,
        distance_meters=10000,
        parcel_count=3,
        parcels=[ParcelSpec(0, 20, sofa, item_key="sofa") for _ in range(3)],
    )
    b = get_pricing_service(db).calculate_merchant(request)
    assert [(i.code, i.amount_cents) for i in b.items if i.code != "fuel"] == [
        ("stop_price", 2000),
        ("parcel_tier", 1200),
    ]
    merge_pricing_config(db, admin_ctx, mid, {"price_book": {"multi_box_as_one_item": True}})
    b = get_pricing_service(db).calculate_merchant(request)
    assert sum(i.amount_cents for i in b.items if i.code == "parcel_tier") == 400


def test_contract_merchant_keeps_multi_box_off(db, admin_ctx, merchant_ctx) -> None:
    mid = merchant_ctx.merchant.id
    apply_kaylulu_pricing_template(db, admin_ctx, mid)
    with pytest.raises(ValueError, match="multi_box_not_allowed_on_contract"):
        merge_pricing_config(db, admin_ctx, mid, {"price_book": {"multi_box_as_one_item": True}})


# ── multi-box packages + labels ─────────────────────────────────────────


def _three_box_order(db, order):
    order.compliance_metadata = {
        "stops": [
            {
                "id": "pu",
                "sequence": 1,
                "stop_type": "pickup",
                "packages": [
                    {"name": "Sofa", "boxes": 3, "item_key": "sofa-1", "weight_kg": 20},
                    {"name": "Lamp", "weight_kg": 2},
                ],
            }
        ]
    }
    db.commit()
    rows = PackageService().sync_from_order(db, order)
    db.commit()
    return rows


def test_boxes_expand_to_one_package_per_box(db, dispatch_order) -> None:
    rows = _three_box_order(db, dispatch_order)
    assert len(rows) == 4
    sofa = [r for r in rows if r.item_key == "sofa-1"]
    assert [(r.box_index, r.box_count) for r in sofa] == [(1, 3), (2, 3), (3, 3)]
    assert rows[-1].item_key is None
    # Re-sync from the projected JSON keeps the item grouping.
    again = PackageService().sync_from_order(db, dispatch_order)
    assert [(r.item_key, r.box_index) for r in again] == [(r.item_key, r.box_index) for r in rows]


def test_labels_show_item_box_line_without_contents(db, dispatch_order) -> None:
    rows = _three_box_order(db, dispatch_order)
    pages = LabelService()._page_dicts(dispatch_order, rows, merchant_name="Acme")
    assert [p["item_line"] for p in pages] == [
        "Item 1 · box 1 of 3",
        "Item 1 · box 2 of 3",
        "Item 1 · box 3 of 3",
        "",
    ]
    assert all("Sofa" not in p["item_line"] for p in pages)
    pdf, _ = LabelService().build_order_labels_pdf(db, dispatch_order, merchant_name="Acme")
    assert pdf.startswith(b"%PDF") and b"/Count 4" in pdf


# ── pickup checklist + missing box ──────────────────────────────────────


def test_pickup_checklist_needs_every_box_scanned_or_reported(db, dispatch_order, driver) -> None:
    rows = _three_box_order(db, dispatch_order)
    gate = ScanGateService()
    checklist = gate.pickup_checklist(db, dispatch_order)
    assert [i["label"] for i in checklist["items"]] == ["Item 1", "Parcel 4"]
    assert checklist["items"][0]["box_count"] == 3
    assert checklist["can_confirm"] is False

    for row in rows[:2] + rows[3:]:
        gate.scan_qr(db, dispatch_order, encode_label_qr(order_id=dispatch_order.id, package_id=row.id), phase="pickup")
    checklist = gate.pickup_checklist(db, dispatch_order)
    assert checklist["items"][0]["scanned"] == 2
    assert checklist["can_confirm"] is False
    with pytest.raises(PackagesIncomplete):
        gate.assert_complete(db, dispatch_order, phase="pickup")

    third = rows[2]
    with pytest.raises(ValueError, match="photo_required"):
        gate.report_missing(db, dispatch_order, third.id, photo_url="", reason="not_found", actor_id=driver.id)
    with pytest.raises(ValueError, match="reason_invalid"):
        gate.report_missing(
            db, dispatch_order, third.id, photo_url="https://x.test/p.jpg", reason="lost", actor_id=driver.id
        )
    out = gate.report_missing(
        db,
        dispatch_order,
        third.id,
        photo_url="data:image/jpeg;base64,AAAA",
        reason="not_found",
        notes="shelf empty",
        actor_id=driver.id,
    )
    assert out["status"] == "missing_at_pickup"
    assert out["checklist"]["can_confirm"] is True
    assert out["checklist"]["items"][0]["missing"] == 1
    gate.assert_complete(db, dispatch_order, phase="pickup")

    exc = db.query(OrderException).filter(OrderException.id == out["exception_id"]).one()
    assert exc.type == "package_missing" and exc.evidence["box_index"] == 3
    event = (
        db.query(DomainEvent)
        .filter(DomainEvent.aggregate_id == dispatch_order.id, DomainEvent.event_type == "incident.reported")
        .first()
    )
    assert event is not None and event.payload["exception_type"] == "package_missing"

    # Delivery expects only the boxes that were picked up.
    progress = gate.scan_progress(db, dispatch_order, phase="delivery")
    assert progress["required"] == 3
    with pytest.raises(ValueError, match="scan_pickup_required_first"):
        gate.scan_qr(db, dispatch_order, third.tracking_suffix, phase="delivery")
    with pytest.raises(ValueError, match="package_already_picked_up"):
        gate.report_missing(
            db, dispatch_order, rows[0].id, photo_url="https://x.test/p.jpg", reason="other", actor_id=driver.id
        )
    assert db.query(Package).filter(Package.id == third.id).one().status == "missing_at_pickup"


# ── Shopify multi-box lines ─────────────────────────────────────────────


def _line(qty=1, boxes=None, grams=30000):
    props = [{"name": "length", "value": "40"}, {"name": "width", "value": "30"}, {"name": "height", "value": "20"}]
    if boxes:
        props.append({"name": "Boxes", "value": str(boxes)})
    return {"id": 77, "title": "Sofa", "sku": "SOFA", "quantity": qty, "grams": grams, "properties": props}


def test_shopify_lines_without_boxes_are_unchanged() -> None:
    parcels = parcels_from_items([_line(qty=2)])
    assert len(parcels) == 2 and all(p.item_key is None for p in parcels)
    assert packages_from_items([_line(qty=2)]) is None


def test_shopify_boxes_property_splits_units_into_boxes() -> None:
    assert item_boxes(_line(boxes=3)) == 3
    parcels = parcels_from_items([_line(qty=2, boxes=3)])
    assert len(parcels) == 6
    assert {p.item_key for p in parcels} == {"77:1", "77:2"}
    assert parcels[0].weight_kg == pytest.approx(10.0)
    packages = packages_from_items([_line(qty=1, boxes=3), {"id": 5, "title": "Pillow", "quantity": 1, "grams": 500}])
    assert [(p["item_key"], p["box_index"], p["box_count"]) for p in packages] == [
        ("77:1", 1, 3),
        ("77:1", 2, 3),
        ("77:1", 3, 3),
        (None, None, None),
    ]
