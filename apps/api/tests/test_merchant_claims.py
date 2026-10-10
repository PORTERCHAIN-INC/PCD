"""AI — file a claim by order number or tracking, not only UUID."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from porterchain_api.auth.merchant import get_merchant_context
from porterchain_api.booking_engine.numbers import (
    generate_order_number,
    generate_tracking_number,
)
from porterchain_api.booking_models import Order
from porterchain_api.config import get_settings
from porterchain_api.db import get_db
from porterchain_api.domain.merchant_states import MerchantRole, MerchantStatus
from porterchain_api.domain.states import OrderState
from porterchain_api.main import app
from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_api.merchant_engine.support_bridge_service import (
    MerchantSupportBridgeService,
    claim_error_message,
)
from porterchain_api.merchant_models import Merchant, MerchantUser


def test_claim_words() -> None:
    assert "not found" in claim_error_message("order_not_found").lower()
    assert "order number" in claim_error_message("order_ref_required").lower()
    assert "order_not_found" not in claim_error_message("order_not_found")


def _merchant_ctx(db, *, suffix: str | None = None) -> MerchantContext:
    tag = suffix or uuid4().hex[:8]
    merchant = Merchant(
        company_name=f"Claim Co {tag}",
        email=f"claim-{tag}@test.local",
        status=MerchantStatus.ACTIVE.value,
    )
    db.add(merchant)
    db.flush()
    user = MerchantUser(
        merchant_id=merchant.id,
        clerk_user_id=f"clerk_{tag}",
        email=f"user-{tag}@test.local",
        role=MerchantRole.OWNER.value,
    )
    db.add(user)
    db.flush()
    return MerchantContext(merchant=merchant, user=user, role=MerchantRole.OWNER)


def _order(db, merchant_id: str) -> Order:
    order = Order(
        order_number=generate_order_number(),
        tracking_number=generate_tracking_number(),
        state=OrderState.DELIVERED.value,
        merchant_id=merchant_id,
        amount_cents=4200,
        currency="cad",
        pickup={"formatted": "1 King St W"},
        dropoff={"formatted": "200 Bay St"},
        scheduled_at=datetime.now(UTC),
    )
    db.add(order)
    db.flush()
    return order


def test_open_claim_by_order_number_and_tracking(db) -> None:
    ctx = _merchant_ctx(db)
    order = _order(db, ctx.merchant.id)
    db.commit()
    svc = MerchantSupportBridgeService()

    by_number = svc.open_claim(
        db, ctx, order_number=order.order_number, claim_type="damaged_parcel", description="Crushed"
    )
    assert by_number["order_id"] == order.id
    assert by_number["order_number"] == order.order_number

    by_track = svc.open_claim(
        db, ctx, order_number=order.tracking_number, claim_type="lost_parcel"
    )
    assert by_track["order_id"] == order.id
    assert by_track["tracking_number"] == order.tracking_number

    by_uuid = svc.open_claim(db, ctx, order_id=order.id, claim_type="late_delivery")
    assert by_uuid["order_id"] == order.id


def test_open_claim_rejects_foreign_and_blank(db) -> None:
    ctx = _merchant_ctx(db)
    other = _merchant_ctx(db)
    foreign = _order(db, other.merchant.id)
    db.commit()
    svc = MerchantSupportBridgeService()

    try:
        svc.open_claim(db, ctx, order_number=foreign.order_number, claim_type="lost_parcel")
        raise AssertionError("expected LookupError")
    except LookupError as exc:
        assert str(exc) == "order_not_found"

    try:
        svc.open_claim(db, ctx, order_id=foreign.id, claim_type="lost_parcel")
        raise AssertionError("expected LookupError")
    except LookupError as exc:
        assert str(exc) == "order_not_found"

    try:
        svc.open_claim(db, ctx, claim_type="lost_parcel")
        raise AssertionError("expected ValueError")
    except ValueError as exc:
        assert str(exc) == "order_ref_required"


def test_claim_http_english(db, settings, monkeypatch) -> None:
    holder: dict = {}
    monkeypatch.setattr(
        "porterchain_api.routers.merchant.support_claims.require_module",
        lambda ctx, module: None,
    )
    app.dependency_overrides[get_merchant_context] = lambda: holder["ctx"]
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_settings] = lambda: settings
    client = TestClient(app)
    try:
        ctx = _merchant_ctx(db)
        order = _order(db, ctx.merchant.id)
        other = _merchant_ctx(db)
        foreign = _order(db, other.merchant.id)
        db.commit()
        holder["ctx"] = ctx

        missing = client.post(
            "/v1/merchant/claims",
            json={"claim_type": "lost_parcel"},
        )
        assert missing.status_code == 400
        assert "order number" in missing.json()["detail"].lower()

        ghost = client.post(
            "/v1/merchant/claims",
            json={"order_number": foreign.order_number, "claim_type": "lost_parcel"},
        )
        assert ghost.status_code == 404
        assert "not found" in ghost.json()["detail"].lower()
        assert ghost.json()["detail"] != "order_not_found"

        ok = client.post(
            "/v1/merchant/claims",
            json={"order_number": order.order_number, "claim_type": "damaged_parcel"},
        )
        assert ok.status_code == 200
        body = ok.json()
        assert body["order_id"] == order.id
        assert body["order_number"] == order.order_number
    finally:
        app.dependency_overrides.clear()
