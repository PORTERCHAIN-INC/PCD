"""HS-21 — Partner `/v1/merchant-api` book with API key + Idempotency-Key is replay-safe."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from porterchain_api.auth.merchant_api import MerchantApiKeyContext, get_merchant_api_context
from porterchain_api.config import get_settings
from porterchain_api.db import get_db
from porterchain_api.domain.merchant_states import MerchantRole, MerchantStatus
from porterchain_api.main import app
from porterchain_api.merchant_engine.api_key_service import MerchantApiKeyService
from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_api.merchant_models import Merchant, MerchantApiKey, MerchantUser


def _booking_body() -> dict:
    return {
        "pickup": {
            "formatted": "100 King St W, Toronto",
            "postal": "M5X 1A1",
            "lat": 43.65,
            "lng": -79.38,
        },
        "dropoff": {
            "formatted": "200 Bay St, Toronto",
            "postal": "M5J 2J2",
            "lat": 43.64,
            "lng": -79.37,
        },
        "vehicle_class": "cargo_van",
        "package_type": "looseParcel",
        "weight_kg": 10,
        "scheduled_at": (datetime.now(UTC) + timedelta(hours=4)).isoformat(),
    }


def _merchant_ctx(db: Session) -> MerchantContext:
    suffix = uuid4().hex[:8]
    merchant = Merchant(
        company_name=f"HS21 Partner {suffix}",
        email=f"hs21-{suffix}@test.invalid",
        status=MerchantStatus.ACTIVE.value,
        payment_terms="NET_30",
        profile={},
    )
    db.add(merchant)
    db.flush()
    user = MerchantUser(
        merchant_id=merchant.id,
        clerk_user_id=f"clerk_hs21_{suffix}",
        email=f"hs21-user-{suffix}@test.invalid",
        role=MerchantRole.OWNER.value,
        is_active=True,
    )
    db.add(user)
    db.flush()
    return MerchantContext(merchant=merchant, user=user, role=MerchantRole.OWNER)


def test_hs21_api_key_create_and_authenticate(db: Session) -> None:
    """Partner key mint + authenticate_key round-trip (X-Api-Key material)."""
    ctx = _merchant_ctx(db)
    svc = MerchantApiKeyService()
    record, raw = svc.create_key(
        db,
        ctx,
        name="hs21",
        scopes=["shipments:write", "shipments:read"],
        environment="sandbox",
    )
    assert raw.startswith("pk_sandbox_")
    assert record.key_prefix == raw[:12]
    found = svc.authenticate_key(db, raw)
    assert found is not None
    assert found.id == record.id
    assert svc.authenticate_key(db, "pk_sandbox_bogus") is None


def test_hs21_merchant_api_book_replay_safe(db: Session, settings) -> None:
    """Same Idempotency-Key on POST /v1/merchant-api/bookings returns the original order."""
    ctx = _merchant_ctx(db)
    api_key = MerchantApiKey(
        merchant_id=ctx.merchant.id,
        name="hs21-book",
        key_prefix="pk_sandbox_hs",
        key_hash="hs21-hash",
        scopes=["shipments:write", "shipments:read"],
        environment="sandbox",
    )
    db.add(api_key)
    db.flush()

    app.dependency_overrides[get_merchant_api_context] = lambda: MerchantApiKeyContext(
        merchant=ctx.merchant, api_key=api_key
    )
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_settings] = lambda: settings
    client = TestClient(app)
    key = f"hs21-{uuid4().hex}"
    headers = {"Idempotency-Key": key}

    try:
        with (
            patch(
                "porterchain_api.merchant_engine.booking_service.resolve_route_distance",
                return_value=(12_000, 900, "haversine"),
            ),
            patch(
                "porterchain_api.merchant_engine.booking_service.transition_to_dispatch_ready",
                side_effect=lambda _db, order, **_k: order,
            ),
        ):
            first = client.post("/v1/merchant-api/bookings", json=_booking_body(), headers=headers)
            second = client.post("/v1/merchant-api/bookings", json=_booking_body(), headers=headers)
        assert first.status_code == 200, first.text
        assert second.status_code == 200, second.text
        assert first.json()["order_id"] == second.json()["order_id"]
        assert first.json()["order_number"] == second.json()["order_number"]
        assert first.json()["is_sandbox"] is True
        # Two POSTs must not mint a second sandbox order for the same key.
        from porterchain_api.booking_models import Order

        rows = (
            db.query(Order)
            .filter(Order.merchant_id == ctx.merchant.id, Order.idempotency_key == key)
            .all()
        )
        assert len(rows) == 1
        assert rows[0].id == first.json()["order_id"]
    finally:
        app.dependency_overrides.pop(get_merchant_api_context, None)
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_settings, None)


def test_hs21_idempotency_key_too_long_rejected(db: Session, settings) -> None:
    ctx = _merchant_ctx(db)
    api_key = MerchantApiKey(
        merchant_id=ctx.merchant.id,
        name="hs21-long",
        key_prefix="pk_sandbox_ln",
        key_hash="hs21-long-hash",
        scopes=["shipments:write"],
        environment="sandbox",
    )
    db.add(api_key)
    db.flush()
    app.dependency_overrides[get_merchant_api_context] = lambda: MerchantApiKeyContext(
        merchant=ctx.merchant, api_key=api_key
    )
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_settings] = lambda: settings
    client = TestClient(app)
    try:
        r = client.post(
            "/v1/merchant-api/bookings",
            json=_booking_body(),
            headers={"Idempotency-Key": "x" * 129},
        )
        assert r.status_code == 400
        assert "idempotency_key_too_long" in r.text
    finally:
        app.dependency_overrides.pop(get_merchant_api_context, None)
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_settings, None)
