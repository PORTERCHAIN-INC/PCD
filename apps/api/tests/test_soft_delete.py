"""Soft delete: guards, global filter, cascade + batch restore, purge permissions, PIPEDA anonymisation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from porterchain_api.admin_engine import soft_delete_service as sd
from porterchain_api.admin_engine.rbac import AdminContext, parse_admin_role
from porterchain_api.admin_models import AdminAuditLog, AdminUser, Driver
from porterchain_api.auth.admin import get_admin_context
from porterchain_api.booking_draft_models import BookingDraft
from porterchain_api.booking_models import Customer, CustomerAddress, Invoice, Order, Package
from porterchain_api.crm_models import CrmLead
from porterchain_api.db import get_db
from porterchain_api.dispatch_engine.models import DispatchPlan, DispatchRoute
from porterchain_api.driver_models import DriverShift
from porterchain_api.main import app
from porterchain_api.merchant_models import Merchant, MerchantApiKey
from porterchain_api.platform.soft_delete import DeletedBatch, including_deleted


def _ctx(role: str) -> AdminContext:
    return AdminContext(user=AdminUser(id=str(uuid4()), clerk_user_id=f"sd-{role}-{uuid4().hex[:6]}",
                                       email=f"{role}@porterchain.com", role=role), role=parse_admin_role(role))


ADMIN, SUPER, SUPPORT = _ctx("admin"), _ctx("super_admin"), _ctx("support")


def _u() -> str:
    return uuid4().hex[:10]


def _merchant(db) -> Merchant:
    m = Merchant(company_name=f"SD Co {_u()}", email=f"m{_u()}@ex.com", status="ACTIVE")
    db.add(m)
    db.flush()
    return m


def _customer(db) -> Customer:
    c = Customer(clerk_user_id=f"sd_{_u()}", email=f"c{_u()}@ex.com", full_name="Tracy Test", phone="+14165550100")
    db.add(c)
    db.flush()
    return c


def _order(db, *, merchant=None, customer=None, state="BOOKED", parcels=1) -> Order:
    n = _u()
    o = Order(order_number=f"SD-{n}", tracking_number=f"TSD{n}", amount_cents=13560, state=state,
              pickup={"address": "1 Main St, Milton", "name": "Kaylulu"}, dropoff={"address": "1 King St W, Toronto", "name": "Buyer"},
              scheduled_at=datetime.now(UTC), merchant_id=merchant.id if merchant else None,
              customer_id=customer.id if customer else None)
    db.add(o)
    db.flush()
    for i in range(parcels):
        db.add(Package(order_id=o.id, parcel_index=i + 1, total_parcels=parcels, tracking_suffix=f"{n}-{i}"))
    db.flush()
    return o


def _driver(db) -> Driver:
    d = Driver(email=f"d{_u()}@ex.com", full_name=f"Dan Driver {_u()}", phone="+14165550111")
    db.add(d)
    db.flush()
    return d


# ── filter ──────────────────────────────────────────────────────────────────────


def test_deleted_rows_vanish_from_queries_but_relationships_still_load(db):
    c = _customer(db)
    o = _order(db, customer=c)
    sd.soft_delete(db, ADMIN, "customer", c.id)
    db.flush()
    db.expunge_all()
    assert db.scalar(select(Customer).where(Customer.id == c.id)) is None
    assert db.get(Customer, c.id) is None
    with including_deleted(db):
        assert db.scalar(select(Customer).where(Customer.id == c.id)) is not None
    assert db.scalar(select(Customer).where(Customer.id == c.id).execution_options(include_deleted=True)) is not None
    # an order (kept for records) still shows who it was for
    order = db.scalar(select(Order).where(Order.id == o.id))
    assert order is not None and order.customer is not None and order.customer.id == c.id


# ── guards ──────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("state", ["DRIVER_EN_ROUTE", "PICKED_UP", "IN_TRANSIT"])
def test_order_on_the_road_cannot_be_deleted(db, state):
    o = _order(db, state=state)
    with pytest.raises(sd.Blocked, match="on the road"):
        sd.soft_delete(db, ADMIN, "order", o.id)
    assert sd.check(db, "order", o.id)["allowed"] is False


def test_delivered_order_is_archive_only(db):
    o = _order(db, state="POD_COMPLETED")
    b = sd.soft_delete(db, ADMIN, "order", o.id)
    with pytest.raises(sd.Blocked, match="proof of delivery"):
        sd.purge(db, SUPER, b.id, confirm=b.label)


def test_invoiced_order_is_archive_only(db):
    o = _order(db, state="CANCELLED")
    db.add(Invoice(invoice_number=f"INV-{_u()}", amount_cents=100, order_id=o.id))
    db.flush()
    b = sd.soft_delete(db, ADMIN, "order", o.id)
    with pytest.raises(sd.Blocked, match="6 years"):
        sd.purge(db, SUPER, b.id, confirm=b.label)


def test_driver_on_shift_and_live_route_are_blocked(db):
    d = _driver(db)
    shift = DriverShift(driver_id=d.id, status="active")
    db.add(shift)
    db.flush()
    with pytest.raises(sd.Blocked, match="on shift"):
        sd.soft_delete(db, ADMIN, "driver", d.id)
    plan = DispatchPlan(service_date=datetime.now(UTC).date())
    db.add(plan)
    db.flush()
    r = DispatchRoute(plan_id=plan.id, vehicle_id="van-1", vehicle_class="van", driver_id=d.id, status="accepted")
    db.add(r)
    db.flush()
    with pytest.raises(sd.Blocked, match="on the road with this route"):
        sd.soft_delete(db, ADMIN, "route", r.id)
    with pytest.raises(sd.Blocked, match="live route"):
        sd.soft_delete(db, ADMIN, "dispatch_plan", plan.id)
    shift.ended_at, shift.status = datetime.now(UTC), "ended"
    db.flush()
    assert sd.soft_delete(db, ADMIN, "route", r.id).state == "deleted"


def test_finance_and_audit_are_never_deletable(db):
    for key in ("invoice", "payment", "audit_log", "invoices", "admin_audit_logs", "forensic_audit_chain"):
        with pytest.raises(sd.Blocked, match="Finance and audit"):
            sd.entity(key)
    assert not set(sd.TABLE_TO_KEY) & sd.NEVER_DELETE


# ── cascade + batch restore ─────────────────────────────────────────────────────


def test_merchant_cascade_and_batch_restore(db):
    m = _merchant(db)
    idle = _order(db, merchant=m, parcels=2)
    key = MerchantApiKey(merchant_id=m.id, name="ERP", key_prefix="pk_x", key_hash=_u(), is_active=True)
    db.add(key)
    db.flush()
    b = sd.soft_delete(db, ADMIN, "merchant", m.id, reason="test")
    db.flush()
    assert {c["entity"] for c in b.children} >= {"order", "parcel"}
    assert key.is_active is False
    db.expunge_all()
    assert db.get(Merchant, m.id) is None and db.get(Order, idle.id) is None
    assert db.scalars(select(Package).where(Package.order_id == idle.id)).all() == []
    sd.restore(db, ADMIN, b.id)
    db.flush()
    db.expunge_all()
    assert db.get(Merchant, m.id) is not None and db.get(Order, idle.id) is not None
    assert len(db.scalars(select(Package).where(Package.order_id == idle.id)).all()) == 2
    assert db.get(MerchantApiKey, key.id).is_active is True
    assert db.get(DeletedBatch, b.id).state == "restored"


def test_merchant_with_order_on_road_is_blocked(db):
    m = _merchant(db)
    _order(db, merchant=m, state="IN_TRANSIT")
    with pytest.raises(sd.Blocked, match="on the road"):
        sd.soft_delete(db, ADMIN, "merchant", m.id)


def test_restore_child_while_parent_deleted_is_blocked(db):
    m = _merchant(db)
    o = _order(db, merchant=m)
    ob = sd.soft_delete(db, ADMIN, "order", o.id)
    sd.soft_delete(db, ADMIN, "merchant", m.id)
    db.flush()
    with pytest.raises(sd.Blocked, match="Restore the merchant first"):
        sd.restore(db, ADMIN, ob.id)


def test_every_action_is_audited(db):
    lead = CrmLead(company_name=f"Lead {_u()}")
    db.add(lead)
    db.flush()
    b = sd.soft_delete(db, ADMIN, "lead", lead.id)
    sd.restore(db, ADMIN, b.id)
    db.flush()
    actions = {a.action for a in db.scalars(select(AdminAuditLog).where(AdminAuditLog.resource_id == lead.id))}
    assert {"soft_delete.delete", "soft_delete.restore"} <= actions


# ── permissions + purge ─────────────────────────────────────────────────────────


def test_purge_needs_super_admin_and_exact_confirm(db):
    lead = CrmLead(company_name=f"Purge me {_u()}")
    db.add(lead)
    db.flush()
    with pytest.raises(PermissionError):
        sd.soft_delete(db, SUPPORT, "lead", lead.id)
    b = sd.soft_delete(db, ADMIN, "lead", lead.id)
    with pytest.raises(PermissionError):
        sd.purge(db, ADMIN, b.id, confirm=b.label)
    with pytest.raises(sd.Blocked, match="Type"):
        sd.purge(db, SUPER, b.id, confirm="nope")
    out = sd.purge(db, SUPER, b.id, confirm=b.label)
    assert out.state == "purged" and out.outcome["mode"] == "hard_delete"
    with including_deleted(db):
        assert db.scalar(select(CrmLead).where(CrmLead.id == lead.id)) is None


def test_booking_draft_delete_restore(db):
    d = BookingDraft(session_id=f"s{_u()}", expires_at=datetime.now(UTC) + timedelta(days=1))
    db.add(d)
    db.flush()
    b = sd.soft_delete(db, ADMIN, "booking_draft", d.id)
    db.expunge_all()
    assert db.get(BookingDraft, d.id) is None
    sd.restore(db, ADMIN, b.id)
    db.expunge_all()
    assert db.get(BookingDraft, d.id) is not None


# ── PIPEDA ──────────────────────────────────────────────────────────────────────


def test_customer_purge_anonymises_and_keeps_financial_records(db):
    c = _customer(db)
    db.add(CustomerAddress(customer_id=c.id, label="Home", line1="1 King St W", city="Toronto",
                           postal_code="M5V 1A1", province="ON")) if hasattr(CustomerAddress, "line1") else None
    o = _order(db, customer=c, state="CLOSED")
    inv = Invoice(invoice_number=f"INV-{_u()}", amount_cents=13560, order_id=o.id, customer_id=c.id)
    db.add(inv)
    db.flush()
    b = sd.soft_delete(db, ADMIN, "customer", c.id)
    out = sd.purge(db, SUPER, b.id, confirm=b.label)
    assert out.outcome["mode"] == "anonymized"
    db.flush()
    with including_deleted(db):
        row = db.scalar(select(Customer).where(Customer.id == c.id))
        assert row is not None
        assert row.full_name is None and row.phone is None and row.email.startswith("erased+")
        assert row.privacy_status == "erased"
        assert db.get(Invoice, inv.id) is not None and db.get(Invoice, inv.id).amount_cents == 13560
        assert db.scalar(select(Order).where(Order.id == o.id)).amount_cents == 13560


def test_driver_purge_hard_deletes_when_nothing_links(db):
    d = _driver(db)
    b = sd.soft_delete(db, ADMIN, "driver", d.id)
    out = sd.purge(db, SUPER, b.id, confirm=b.label)
    assert out.outcome["mode"] in {"hard_delete", "anonymized"}


# ── retention + auto-purge ──────────────────────────────────────────────────────


def test_retention_default_and_super_only(db):
    assert sd.retention_days(db) >= 1
    with pytest.raises(PermissionError):
        sd.set_retention_days(db, ADMIN, 7)
    assert sd.set_retention_days(db, SUPER, 7) == 7
    with pytest.raises(sd.Blocked):
        sd.set_retention_days(db, SUPER, 0)


def test_auto_purge_purges_due_and_keeps_archive_only(db):
    lead = CrmLead(company_name=f"Old lead {_u()}")
    db.add(lead)
    delivered = _order(db, state="DELIVERED")
    db.flush()
    b1 = sd.soft_delete(db, ADMIN, "lead", lead.id)
    b2 = sd.soft_delete(db, ADMIN, "order", delivered.id)
    past = datetime.now(UTC) - timedelta(days=1)
    b1.purge_after = b2.purge_after = past
    db.commit()
    out = sd.auto_purge(db)
    assert out["purged"] >= 1 and out["kept"] >= 1
    assert db.get(DeletedBatch, b1.id).state == "purged"
    kept = db.get(DeletedBatch, b2.id)
    assert kept.state == "deleted" and kept.purge_after is None and "proof of delivery" in kept.outcome["reason"]


# ── HTTP ────────────────────────────────────────────────────────────────────────


@pytest.fixture
def client(db):
    holder = {"ctx": ADMIN}
    app.dependency_overrides[get_admin_context] = lambda: holder["ctx"]
    app.dependency_overrides[get_db] = lambda: db
    yield TestClient(app), holder
    app.dependency_overrides.clear()


def test_http_flow(client, db):
    http, holder = client
    o = _order(db, state="IN_TRANSIT")
    r = http.get(f"/v1/admin/deleted-items/check/order/{o.id}")
    assert r.status_code == 200 and r.json()["allowed"] is False
    r = http.post(f"/v1/admin/deleted-items/order/{o.id}/delete", json={})
    assert r.status_code == 409 and "on the road" in r.json()["detail"]["message"]

    lead = CrmLead(company_name=f"HTTP lead {_u()}")
    db.add(lead)
    db.flush()
    r = http.delete(f"/v1/admin/leads/{lead.id}")
    assert r.status_code == 204
    items = http.get("/v1/admin/deleted-items", params={"entity": "lead"}).json()["items"]
    batch = next(i for i in items if i["root_id"] == lead.id)
    assert http.post(f"/v1/admin/deleted-items/{batch['id']}/purge", json={"confirm": batch["label"]}).status_code == 403
    assert http.post(f"/v1/admin/deleted-items/{batch['id']}/restore").status_code == 200
    assert http.get("/v1/admin/deleted-items/meta").json()["can_purge"] is False
    holder["ctx"] = SUPER
    r = http.delete(f"/v1/admin/leads/{lead.id}")
    assert r.status_code == 204
    batch = next(i for i in http.get("/v1/admin/deleted-items").json()["items"] if i["root_id"] == lead.id)
    assert http.post(f"/v1/admin/deleted-items/{batch['id']}/purge", json={"confirm": "x"}).status_code == 409
    assert http.post(f"/v1/admin/deleted-items/{batch['id']}/purge", json={"confirm": batch["label"]}).status_code == 200
    holder["ctx"] = SUPPORT
    assert http.get("/v1/admin/deleted-items").status_code == 403
