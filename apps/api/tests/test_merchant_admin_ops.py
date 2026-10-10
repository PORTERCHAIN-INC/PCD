"""Merchant admin ops: money guard, health v2, credit hold, connections, quote
preview margin floor, documents, segments / bulk, change history."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from porterchain_api.admin_engine import merchant_money_guard as guard
from porterchain_api.admin_engine.rbac import AdminContext, parse_admin_role
from porterchain_api.admin_models import AdminUser
from porterchain_api.auth.admin import get_admin_context
from porterchain_api.booking_engine.numbers import (
    generate_order_number,
    generate_tracking_number,
)
from porterchain_api.booking_models import Invoice, Order
from porterchain_api.db import get_db
from porterchain_api.main import app
from porterchain_api.merchant_engine.account_ops import (
    connections,
    credit,
    health,
    quote_preview,
)
from porterchain_api.merchant_models import (
    Merchant,
    MerchantApiKey,
    MerchantAuditLog,
    ShopifyShop,
)

PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"


def _ctx(role: str) -> AdminContext:
    return AdminContext(
        user=AdminUser(clerk_user_id=f"ops-{role}", email=f"{role}@porterchain.com", role=role),
        role=parse_admin_role(role),
    )


@pytest.fixture
def merchant(db):
    row = Merchant(company_name=f"Ops Co {uuid4().hex[:6]}", email="ops-co@example.com", status="ACTIVE",
                   industry="Pharmacy", payment_terms="NET_30")
    db.add(row)
    db.commit()
    yield row


def _order(db, merchant_id: str, *, days_ago: int, state: str = "DELIVERED") -> Order:
    at = datetime.now(UTC) - timedelta(days=days_ago)
    order = Order(
        order_number=generate_order_number(),
        tracking_number=generate_tracking_number(),
        state=state,
        merchant_id=merchant_id,
        amount_cents=4400,
        currency="cad",
        pickup={"formatted": "1 King"},
        dropoff={"formatted": "200 Bay"},
        scheduled_at=at,
        created_at=at,
    )
    db.add(order)
    db.flush()
    return order


@pytest.fixture
def as_role(db, monkeypatch):
    monkeypatch.setattr("porterchain_api.routers.merchant_ops.require_module", lambda ctx, module: None)
    monkeypatch.setattr("porterchain_api.routers.merchants.require_module", lambda ctx, module: None)

    def make(role: str) -> TestClient:
        app.dependency_overrides[get_admin_context] = lambda: _ctx(role)
        app.dependency_overrides[get_db] = lambda: db
        return TestClient(app)

    yield make
    app.dependency_overrides.clear()


# ── 1. money guard + change history ─────────────────────────────────────────


@pytest.mark.parametrize("role,allowed", [
    ("super_admin", True), ("admin", True), ("finance", True),
    ("sales", False), ("sales_manager", False), ("support", False), ("compliance", False),
])
def test_money_editor_roles(role, allowed):
    assert guard.can_edit_money(_ctx(role)) is allowed


def test_sales_cannot_change_merchant_pricing(as_role, merchant):
    res = as_role("sales").put(f"/v1/admin/merchants/{merchant.id}/pricing", json={"pricing_model": "fsa"})
    assert res.status_code == 403
    assert "merchant_money_edit_forbidden" in res.text


def test_finance_pricing_edit_lands_in_change_history(as_role, merchant, db):
    client = as_role("finance")
    res = client.put(f"/v1/admin/merchants/{merchant.id}/pricing", json={"price_book": {"enabled": True}})
    assert res.status_code == 200, res.text
    hist = client.get(f"/v1/admin/merchant-ops/{merchant.id}/change-history").json()
    assert hist and hist[0]["area"] == "pricing"
    assert hist[0]["changes"]["price_book"]["new"] == {"enabled": True}
    assert hist[0]["actor_role"] == "finance"


def test_dict_diff_only_changed_keys():
    assert guard.dict_diff({"a": 1, "b": 2}, {"a": 1, "b": 3, "c": 4}) == {
        "b": {"old": 2, "new": 3}, "c": {"old": None, "new": 4},
    }


# ── 2. health v2 ────────────────────────────────────────────────────────────


def test_health_flags_churn_when_orders_stop(db, merchant):
    for d in (60, 57, 54, 51, 48, 45, 42, 39, 36, 33):
        _order(db, merchant.id, days_ago=d)
    db.commit()
    facts = health.collect_facts(db, [merchant])[merchant.id]
    out = health.evaluate(merchant, facts)
    assert "churn_risk" in out["signals"]
    assert "churn_risk" in out["needs_action"]
    assert any("No orders for" in r["label"] for r in out["reasons"])
    assert out["next_action"].startswith("Call the account")
    assert sum(out["trend"]["weekly"]) == 8  # 8-week window
    assert 0 <= out["score"] <= 100


def test_health_expansion_and_healthy(db, merchant):
    for d in (50, 45):
        _order(db, merchant.id, days_ago=d)
    for d in range(1, 26, 2):
        _order(db, merchant.id, days_ago=d)
    db.commit()
    out = health.evaluate(merchant, health.collect_facts(db, [merchant])[merchant.id])
    assert "expansion" in out["signals"]
    assert out["band"] == "healthy"
    assert out["needs_action"] == []


def test_segment_from_industry_and_override(merchant):
    assert health.segment_of(merchant) == "pharmacy_lab"
    merchant.segment_tags = ["trades"]
    assert health.segment_of(merchant) == "trades"


def test_board_needs_action_view_and_pagination(as_role, db, merchant):
    stuck = Merchant(company_name="Stuck Co", email="s@example.com", status="ONBOARDING",
                     created_at=datetime.now(UTC) - timedelta(days=20))
    db.add(stuck)
    db.commit()
    client = as_role("support")
    body = client.get("/v1/admin/merchant-ops/board", params={"view": "needs_action", "page_size": 5}).json()
    ids = [r["id"] for r in body["items"]]
    assert stuck.id in ids or body["total"] > 5
    assert body["page_size"] == 5 and body["pages"] >= 1
    assert "segments" in body["counts"]
    all_view = client.get("/v1/admin/merchant-ops/board", params={"view": "all", "search": "Stuck Co"}).json()
    assert all_view["items"][0]["needs_labels"] == ["Onboarding stuck"]


# ── 3. credit hold ──────────────────────────────────────────────────────────


def _overdue_invoice(db, merchant, days_old: int) -> None:
    order = _order(db, merchant.id, days_ago=days_old)
    db.add(Invoice(invoice_number=f"INV-{uuid4().hex[:8].upper()}", order_id=order.id,
                   merchant_id=merchant.id, amount_cents=4400, tax_cents=572, currency="cad",
                   created_at=datetime.now(UTC) - timedelta(days=days_old)))
    db.commit()


def test_auto_hold_after_grace_blocks_booking(db, merchant):
    _overdue_invoice(db, merchant, days_old=45)  # NET_30 → 15 days overdue > 7 grace
    with pytest.raises(ValueError, match="credit_hold"):
        credit.assert_can_book(db, merchant)
    assert merchant.credit_hold_mode == "auto"
    assert db.query(MerchantAuditLog).filter_by(merchant_id=merchant.id, action="credit.auto_hold_applied").count()


def test_overdue_within_grace_does_not_hold(db, merchant):
    _overdue_invoice(db, merchant, days_old=3)  # inside the 7-day grace on any terms
    credit.assert_can_book(db, merchant)
    assert merchant.credit_hold_mode == "none"


def test_override_lets_held_merchant_book(db, merchant):
    _overdue_invoice(db, merchant, days_old=45)
    credit.set_credit(db, _ctx("finance"), merchant, action="override", reason="Paid, e-Transfer pending",
                      override_days=2)
    credit.assert_can_book(db, merchant)


def test_manual_hold_api_needs_reason_and_money_role(as_role, merchant):
    url = f"/v1/admin/merchant-ops/{merchant.id}/credit"
    assert as_role("sales").post(url, json={"action": "hold", "reason": "x"}).status_code == 403
    assert as_role("finance").post(url, json={"action": "hold"}).status_code == 400
    ok = as_role("finance").post(url, json={"action": "hold", "reason": "Cheque bounced"})
    assert ok.status_code == 200, ok.text
    assert ok.json()["blocked"] is True and ok.json()["mode"] == "manual"


def test_booking_service_rejects_held_merchant(db, merchant):
    from porterchain_api.merchant_engine.booking_service import (
        _assert_not_on_credit_hold,
    )
    from porterchain_api.merchant_engine.booking_validation import (
        BookingValidationError,
    )

    merchant.credit_hold_mode = "manual"
    db.commit()

    class _Ctx:
        pass

    c = _Ctx()
    c.merchant = merchant
    with pytest.raises(BookingValidationError) as exc:
        _assert_not_on_credit_hold(db, c)
    assert exc.value.code == "credit_hold"
    assert "Interac" in exc.value.message


# ── 4. connections ──────────────────────────────────────────────────────────


def test_missing_scopes_write_implies_read():
    assert connections.missing_scopes("write_orders,write_shipping", "read_orders,write_shipping") == []
    assert connections.missing_scopes("read_orders", "read_orders,write_fulfillments") == ["write_fulfillments"]


def test_watchdog_red_on_missing_scope(db, merchant):
    from porterchain_api.config import get_settings

    db.add(ShopifyShop(merchant_id=merchant.id, shop_domain=f"{uuid4().hex[:8]}.myshopify.com",
                       encrypted_access_token="x", scopes="read_orders", carrier_service_gid=None))
    db.commit()
    out = connections.watchdog(db, merchant.id, get_settings())
    shop = [i for i in out["items"] if i["kind"] == "shopify"][0]
    assert shop["light"] == "red"
    assert "write_fulfillments" in shop["missing_scopes"]
    assert out["light"] == "red"


def test_rotate_key_keeps_old_until_grace_and_expired_key_fails(db, merchant, as_role):
    from porterchain_api.merchant_engine.api_key_service import MerchantApiKeyService

    raw_old = "pk_production_old_" + uuid4().hex
    import hashlib

    old = MerchantApiKey(merchant_id=merchant.id, name="ERP", key_prefix=raw_old[:12],
                         key_hash=hashlib.sha256(raw_old.encode()).hexdigest(), environment="production")
    db.add(old)
    db.commit()
    # Admin (not elevated) is refused at the router; super admin rotates.
    denied = as_role("admin").post(
        f"/v1/admin/merchant-ops/{merchant.id}/api-keys/{old.id}/rotate", json={"grace_days": 7, "reason": "r"}
    )
    assert denied.status_code == 403
    out = connections.rotate_api_key(db, _ctx("super_admin"), merchant.id, old.id, grace_days=7, reason="leak")
    db.commit()
    svc = MerchantApiKeyService()
    assert svc.authenticate_key(db, raw_old) is not None  # still in grace
    assert svc.authenticate_key(db, out["secret"]) is not None
    old.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    db.commit()
    assert svc.authenticate_key(db, raw_old) is None
    audit = db.query(MerchantAuditLog).filter_by(merchant_id=merchant.id, action="api_key.rotated").one()
    assert out["secret"] not in str(audit.payload)


# ── 6. quote preview margin floor ───────────────────────────────────────────


def test_driver_cost_wave_block_and_per_stop():
    policy = dict(quote_preview.DEFAULT_POLICY)
    plan = {"mode": "wave_block", "hourly_cents": 2700, "per_stop_cents": 800, "per_pickup_cents": 0,
            "per_route_cents": 0, "route_included_stops": 0, "route_extra_stop_cents": 0,
            "minimum_paid_hours": 0,
            "wave_block": {"block_hours": 4, "block_cents": 10800, "included_stops": 0, "extra_stop_cents": 0}}
    assert quote_preview.driver_cost_cents(plan, policy, drive_minutes=20)["cents"] == 1800
    plan["mode"] = "per_stop"
    assert quote_preview.driver_cost_cents(plan, policy, drive_minutes=20)["cents"] == 800


@pytest.mark.parametrize("price,cost,status", [(3000, 1800, "ok"), (2000, 1800, "below_floor"),
                                               (1500, 1800, "below_cost"), (0, 1800, "no_price")])
def test_margin_verdict(price, cost, status):
    assert quote_preview.margin_verdict(price, cost, 20)["status"] == status


def test_quote_preview_endpoint(as_role, merchant, monkeypatch):
    monkeypatch.setattr(
        "porterchain_api.integrations.shopify_carrier_rates.quote_merchant_rate",
        lambda db, m, **kw: (3390, {"subtotal_cents": 3000, "tax_cents": 390, "items": [],
                                    "metadata": {"distance_meters": 12000}}),
    )
    res = as_role("support").post(
        f"/v1/admin/merchant-ops/{merchant.id}/quote-preview",
        json={"pickup": {"formatted": "1 King St W", "lat": 43.65, "lng": -79.38, "postal": "M5H 1A1"},
              "dropoff": {"formatted": "200 Bay St", "lat": 43.64, "lng": -79.38, "postal": "M5J 2J5"}},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["price"]["final_cents"] == 3390
    assert body["margin"]["status"] == "ok"
    assert body["route"]["distance_km"] == 12.0


# ── 7. segments + bulk ──────────────────────────────────────────────────────


def test_bulk_segment_and_credit_hold_roles(as_role, db, merchant):
    other = Merchant(company_name="Bulk Two", email="b2@example.com", status="ACTIVE")
    db.add(other)
    db.commit()
    res = as_role("sales").post("/v1/admin/merchant-ops/bulk", json={
        "action": "set_segment", "merchant_ids": [merchant.id, other.id], "value": "trades"})
    assert res.status_code == 200, res.text
    assert sorted(res.json()["ok"]) == sorted([merchant.id, other.id])
    db.refresh(other)
    assert other.segment_tags == ["trades"]
    denied = as_role("sales").post("/v1/admin/merchant-ops/bulk", json={
        "action": "credit_hold", "merchant_ids": [merchant.id], "reason": "x"})
    assert denied.status_code == 403
    bad = as_role("admin").post("/v1/admin/merchant-ops/bulk", json={
        "action": "set_segment", "merchant_ids": [merchant.id], "value": "nope"})
    assert bad.json()["failed"][0]["error"] == "segment_invalid"


# ── 8. documents ────────────────────────────────────────────────────────────


def test_document_upload_download_delete_and_erasure(as_role, db, merchant):
    from porterchain_api.merchant_engine.account_ops.documents import purge_documents
    from porterchain_api.merchant_models import MerchantDocument

    client = as_role("admin")
    up = client.post(f"/v1/admin/merchant-ops/{merchant.id}/documents",
                     data={"kind": "insurance_coi", "expires_on": "2027-01-31"},
                     files={"file": ("coi.pdf", PDF, "application/pdf")})
    assert up.status_code == 201, up.text
    doc_id = up.json()["id"]
    fake = client.post(f"/v1/admin/merchant-ops/{merchant.id}/documents",
                       data={"kind": "other"}, files={"file": ("x.pdf", b"MZ\x90", "application/pdf")})
    assert fake.status_code == 400
    assert as_role("sales").get(
        f"/v1/admin/merchant-ops/{merchant.id}/documents/{doc_id}/download").status_code == 403
    client = as_role("admin")
    dl = client.get(f"/v1/admin/merchant-ops/{merchant.id}/documents/{doc_id}/download")
    assert dl.status_code == 200 and dl.content == PDF
    assert dl.headers["cache-control"] == "no-store"
    assert db.query(MerchantAuditLog).filter_by(merchant_id=merchant.id, action="document.downloaded").count()
    assert purge_documents(db, merchant.id) == 1
    row = db.get(MerchantDocument, doc_id)
    assert row.content is None and row.filename == "erased"


def test_support_rollup_and_overview(as_role, merchant):
    client = as_role("support")
    assert client.get(f"/v1/admin/merchant-ops/{merchant.id}/support").json() == {
        "tickets": [], "claims": [], "exceptions": []}
    ov = client.get(f"/v1/admin/merchant-ops/{merchant.id}").json()
    assert ov["segment"]["value"] == "pharmacy_lab"
    assert ov["can_edit_money"] is False
    assert ov["credit"]["payment_method"] == "interac_etransfer"


def test_sweep_emails_owner_once_per_week_through_injected_sender(db, merchant):
    """Churn alert goes through the worker-injected sender, deduped per ISO week."""
    from porterchain_api.merchant_engine.account_ops import alerts

    sent: list[tuple[str, str]] = []

    def sender(template, recipient, context):
        sent.append((template, recipient))
        return True

    out1 = alerts.sweep(db, None, sender=sender)
    out2 = alerts.sweep(db, None, sender=sender)
    assert out2["churn_emails"] == 0  # same week: deduped
    assert out1["churn_emails"] == len([t for t, _ in sent if t == "merchant_churn_alert"])
    assert alerts.sweep(db, None)["churn_emails"] == 0  # no sender: nothing emailed


@pytest.fixture
def cycle_cleanup(db):
    """Cycle invoices (order_id NULL) must not leak into other suites' shared DB."""
    yield
    db.rollback()
    db.query(Invoice).filter(Invoice.invoice_number.like("CYC-%")).delete(synchronize_session=False)
    db.commit()


def test_overdue_cycle_invoice_without_order_triggers_auto_hold(db, merchant, cycle_cleanup):
    """Billing-cycle invoices (no order_id) count toward overdue, not just per-order ones."""
    db.add(Invoice(invoice_number=f"CYC-{uuid4().hex[:8].upper()}", order_id=None, merchant_id=merchant.id,
                   amount_cents=120000, tax_cents=15600, currency="cad",
                   created_at=datetime.now(UTC) - timedelta(days=50)))
    db.commit()
    rows = credit.overdue_invoices(db, merchant)
    assert [r["kind"] for r in rows] == ["cycle"]
    assert credit.sync_auto_hold(db, merchant) == "applied"
    assert merchant.credit_hold_mode == "auto"


def test_paid_cycle_invoice_does_not_hold(db, merchant, cycle_cleanup):
    db.add(Invoice(invoice_number=f"CYC-{uuid4().hex[:8].upper()}", order_id=None, merchant_id=merchant.id,
                   amount_cents=120000, currency="cad", status="paid", paid_at=datetime.now(UTC),
                   created_at=datetime.now(UTC) - timedelta(days=50)))
    db.commit()
    assert credit.overdue_invoices(db, merchant) == []
