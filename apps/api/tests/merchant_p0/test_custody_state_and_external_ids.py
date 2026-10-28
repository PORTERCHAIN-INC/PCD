"""Chain of custody: package state machine, rejection audit, partner barcodes."""

from __future__ import annotations

import dataclasses

from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from porterchain_api.booking_engine.order_transitions import (
    ORDER_TRANSITION_REJECTED,
    transition_order_state,
)
from porterchain_api.booking_models import OrderEvent, Package
from porterchain_api.db import get_db
from porterchain_api.domain.states import (
    PACKAGE_TRANSITIONS,
    OrderState,
    PackageState,
    can_transition_package,
)
from porterchain_api.main import app
from porterchain_api.merchant_engine.external_identifier_service import (
    ExternalIdentifierService,
    normalize,
)
from porterchain_api.domain.merchant_states import MerchantRole
from porterchain_api.merchant_engine.rbac import MODULE_PERMISSIONS
from porterchain_api.merchant_engine.package_state import (
    EVENT_CHANGED,
    EVENT_REJECTED,
    IllegalPackageTransition,
    set_package_status,
)
from porterchain_api.routers.merchant._deps import get_merchant_context


def _pkg(db, order, idx: int = 1, total: int = 1) -> Package:
    row = Package(
        order_id=order.id,
        parcel_index=idx,
        total_parcels=total,
        tracking_suffix=f"T{uuid4().hex[:10]}",
    )
    db.add(row)
    db.flush()
    return row


def _events(db, order_id: str, event_type: str) -> list[OrderEvent]:
    db.expire_all()
    return db.query(OrderEvent).filter(OrderEvent.order_id == order_id, OrderEvent.event_type == event_type).all()


# ------------------------------------------------------------ state machine


def test_every_package_state_has_transition_entry():
    assert set(PACKAGE_TRANSITIONS) == set(PackageState)
    assert PACKAGE_TRANSITIONS[PackageState.DELIVERED] == set()


@pytest.mark.parametrize(
    ("src", "dst", "ok"),
    [
        (PackageState.MANIFESTED, PackageState.PICKED_UP, True),
        (PackageState.MANIFESTED, PackageState.MISSING_AT_PICKUP, True),
        (PackageState.MISSING_AT_PICKUP, PackageState.PICKED_UP, True),
        (PackageState.PICKED_UP, PackageState.DELIVERED, True),
        (PackageState.MANIFESTED, PackageState.DELIVERED, False),
        (PackageState.DELIVERED, PackageState.PICKED_UP, False),
        (PackageState.OUT_FOR_DELIVERY, PackageState.MANIFESTED, False),
    ],
)
def test_can_transition_package(src, dst, ok):
    assert can_transition_package(src, dst) is ok


def test_legal_move_writes_status_changed_event(db, dispatch_order):
    pkg = _pkg(db, dispatch_order)
    assert set_package_status(db, pkg, PackageState.PICKED_UP, actor_type="driver", source="scan") is True
    db.flush()
    assert pkg.status == "picked_up"
    ev = _events(db, dispatch_order.id, EVENT_CHANGED)
    assert [(e.from_state, e.to_state) for e in ev] == [("manifested", "picked_up")]
    assert ev[0].payload["package_id"] == pkg.id


def test_same_state_is_noop(db, dispatch_order):
    pkg = _pkg(db, dispatch_order)
    assert set_package_status(db, pkg, PackageState.MANIFESTED) is False
    assert _events(db, dispatch_order.id, EVENT_CHANGED) == []


def test_illegal_move_rejected_and_audit_survives_rollback(db, dispatch_order):
    pkg = _pkg(db, dispatch_order)
    db.commit()  # the audit row is written in its own transaction and needs the order to exist
    with pytest.raises(IllegalPackageTransition) as exc:
        set_package_status(db, pkg, PackageState.DELIVERED, actor_type="driver", actor_id="d1")
    assert str(exc.value) == "illegal_package_transition"
    db.rollback()
    assert db.get(Package, pkg.id).status == "manifested"
    rej = _events(db, dispatch_order.id, EVENT_REJECTED)
    assert len(rej) == 1
    assert (rej[0].from_state, rej[0].to_state, rej[0].actor_id) == ("manifested", "delivered", "d1")


def test_db_check_rejects_unknown_status(db, dispatch_order):
    pkg = _pkg(db, dispatch_order)
    with pytest.raises(IntegrityError):
        db.execute(text("UPDATE packages SET status = 'teleported' WHERE id = :i"), {"i": pkg.id})
    db.rollback()


def test_illegal_order_transition_is_logged(db, dispatch_order):
    db.commit()
    with pytest.raises(ValueError):
        transition_order_state(db, dispatch_order, OrderState.DELIVERED, event_type="test.jump")
    db.rollback()
    rej = _events(db, dispatch_order.id, ORDER_TRANSITION_REJECTED)
    assert len(rej) == 1 and rej[0].to_state == OrderState.DELIVERED.value


# ------------------------------------------------------- external identifiers


def test_normalize():
    assert normalize(" 1z-999 aa1 ") == "1Z999AA1"
    assert normalize("") == ""


def test_register_resolve_and_duplicates(db, dispatch_order, merchant_ctx):
    svc = ExternalIdentifierService()
    a, b = _pkg(db, dispatch_order, 1, 2), _pkg(db, dispatch_order, 2, 2)
    row = svc.register(db, dispatch_order, a.id, source="shopify", value="1Z-999 AA1")
    assert row.value_normalized == "1Z999AA1"
    # idempotent for the same package
    assert svc.register(db, dispatch_order, a.id, source="shopify", value="1z999aa1").id == row.id
    with pytest.raises(ValueError, match="external_id_already_assigned"):
        svc.register(db, dispatch_order, b.id, source="shopify", value="1Z999AA1")
    with pytest.raises(ValueError, match="external_id_source_invalid"):
        svc.register(db, dispatch_order, a.id, source="ups_tracking_number", value="X")
    with pytest.raises(ValueError, match="external_id_value_invalid"):
        svc.register(db, dispatch_order, a.id, source="merchant", value=" - ")
    with pytest.raises(LookupError):
        svc.register(db, dispatch_order, str(uuid4()), source="merchant", value="X1")
    assert svc.resolve(db, dispatch_order, "1z 999 aa1").id == a.id
    assert svc.resolve(db, dispatch_order, "nope") is None
    assert svc.remove(db, dispatch_order, row.id) is True
    assert svc.resolve(db, dispatch_order, "1Z999AA1") is None


def _matrix_require(ctx, module: str) -> None:
    """SpiceDB bypass mirroring MODULE_PERMISSIONS (same approach as test_p0_personas_http)."""
    if ctx.role not in MODULE_PERMISSIONS.get(module, frozenset()):
        raise HTTPException(status_code=403, detail=f"merchant_forbidden:{module}")


@pytest.fixture
def merchant_client(db, merchant_ctx):
    app.dependency_overrides[get_merchant_context] = lambda: merchant_ctx
    app.dependency_overrides[get_db] = lambda: db
    with patch("porterchain_api.routers.merchant.package_external_ids.require_module", _matrix_require):
        yield TestClient(app)
    app.dependency_overrides.clear()


def test_external_id_endpoints(db, dispatch_order, merchant_client):
    pkg = _pkg(db, dispatch_order)
    base = f"/v1/merchant/orders/{dispatch_order.id}/external-ids"
    r = merchant_client.post(base, json={"package_id": pkg.id, "source": "marketplace", "value": "AMZ-123"})
    assert r.status_code == 201, r.text
    ident = r.json()
    listed = merchant_client.get(base).json()
    assert listed["items"][0]["id"] == ident["id"]
    assert listed["packages"][0] == {
        "id": pkg.id,
        "parcel_index": 1,
        "total_parcels": 1,
        "tracking_suffix": pkg.tracking_suffix,
        "status": "manifested",
    }
    bad = merchant_client.post(base, json={"package_id": pkg.id, "source": "bogus", "value": "X"})
    assert bad.status_code == 422
    missing = merchant_client.get(f"/v1/merchant/orders/{uuid4()}/external-ids")
    assert missing.status_code == 404
    assert merchant_client.delete(f"{base}/{ident['id']}").json() == {"ok": True}
    assert merchant_client.delete(f"{base}/{ident['id']}").status_code == 404


def test_viewer_cannot_register_external_id(db, dispatch_order, merchant_ctx, merchant_client):
    pkg = _pkg(db, dispatch_order)
    readonly = dataclasses.replace(merchant_ctx, role=MerchantRole.READONLY)
    app.dependency_overrides[get_merchant_context] = lambda: readonly
    base = f"/v1/merchant/orders/{dispatch_order.id}/external-ids"
    r = merchant_client.post(base, json={"package_id": pkg.id, "value": "X1"})
    assert r.status_code == 403
    assert merchant_client.get(base).status_code == 200


def test_sandbox_purge_goes_through_order_writer(db, merchant_ctx):
    from datetime import UTC, datetime

    from porterchain_api.booking_engine.numbers import generate_order_number, generate_tracking_number
    from porterchain_api.booking_models import Order
    from porterchain_api.merchant_engine.integrations_service import MerchantIntegrationsService

    def _o(state):
        o = Order(
            order_number=generate_order_number(),
            tracking_number=generate_tracking_number(),
            state=state,
            merchant_id=merchant_ctx.merchant.id,
            amount_cents=100,
            currency="cad",
            pickup={},
            dropoff={},
            scheduled_at=datetime.now(UTC),
            is_sandbox=True,
        )
        db.add(o)
        db.flush()
        return o

    booked, delivered = _o(OrderState.BOOKED.value), _o(OrderState.DELIVERED.value)
    out = MerchantIntegrationsService().purge_sandbox_orders(db, merchant_ctx, confirm="purge test")
    assert out["cancelled"] == 1 and out["skipped"] == 1
    db.refresh(booked)
    db.refresh(delivered)
    assert booked.state == OrderState.CANCELLED.value
    assert delivered.state == OrderState.DELIVERED.value
    ev = _events(db, booked.id, "order.cancelled")
    assert len(ev) == 1 and ev[0].actor_id == merchant_ctx.user.id
    assert ev[0].payload == {"reason": "sandbox_purge"}


def test_admin_switch_turns_partner_barcodes_off(db, dispatch_order, merchant_client):
    """Control: staff flag on the merchant disables registration and the scan fallback."""
    from porterchain_api.admin_engine.merchant_service import AdminMerchantService
    from tests.test_enterprise_identity import _admin_ctx

    svc = ExternalIdentifierService()
    pkg = _pkg(db, dispatch_order)
    svc.register(db, dispatch_order, pkg.id, source="merchant", value="BOX-1")
    assert svc.resolve(db, dispatch_order, "BOX1").id == pkg.id

    AdminMerchantService().update_merchant_terms(
        db, _admin_ctx(db), dispatch_order.merchant_id, partner_barcodes_enabled=False
    )
    assert svc.resolve(db, dispatch_order, "BOX1") is None
    base = f"/v1/merchant/orders/{dispatch_order.id}/external-ids"
    r = merchant_client.post(base, json={"package_id": pkg.id, "source": "merchant", "value": "BOX-2"})
    assert r.status_code == 403 and "switched off" in r.json()["detail"]

    AdminMerchantService().update_merchant_terms(
        db, _admin_ctx(db), dispatch_order.merchant_id, partner_barcodes_enabled=True
    )
    assert svc.resolve(db, dispatch_order, "BOX1").id == pkg.id
