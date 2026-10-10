"""Programmatic booking dedupe + provenance — Shopify retries must not double-book."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from porterchain_api.booking_engine.numbers import generate_order_number, generate_tracking_number
from porterchain_api.domain.merchant_states import MerchantStatus
from porterchain_api.domain.states import OrderSource
from porterchain_api.booking_models import Order
from porterchain_api.merchant_models import Merchant
from porterchain_api.routers.merchant_api import _resolve_order_source


def _addr() -> dict:
    return {"formatted": "1 King St W, Toronto", "lat": 43.6488, "lng": -79.3817}


def _merchant(db: Session) -> Merchant:
    suffix = uuid4().hex[:8]
    merchant = Merchant(
        company_name=f"Idempotency Co {suffix}",
        email=f"idem-{suffix}@test.local",
        status=MerchantStatus.ACTIVE.value,
        profile={},
    )
    db.add(merchant)
    db.flush()
    return merchant


def _make_order(db: Session, *, merchant_id: str, idempotency_key: str | None) -> Order:
    order = Order(
        order_number=generate_order_number(),
        tracking_number=generate_tracking_number(),
        merchant_id=merchant_id,
        idempotency_key=idempotency_key,
        amount_cents=2500,
        currency="cad",
        pickup=_addr(),
        dropoff=_addr(),
        scheduled_at=datetime.now(UTC),
    )
    db.add(order)
    db.flush()
    return order


def test_shopify_channel_header_stamps_shopify_source() -> None:
    assert _resolve_order_source("shopify") == OrderSource.SHOPIFY.value
    assert _resolve_order_source("Shopify") == OrderSource.SHOPIFY.value


def test_plain_api_calls_are_stamped_api_not_merchant() -> None:
    """Previously every API create recorded MERCHANT, hiding the channel."""
    assert _resolve_order_source(None) == OrderSource.API.value
    assert _resolve_order_source("") == OrderSource.API.value
    assert _resolve_order_source("some-other-tool") == OrderSource.API.value


def test_shopify_is_a_known_order_source() -> None:
    assert OrderSource.SHOPIFY.value == "SHOPIFY"
    # Column is String(16); a longer value would silently truncate or error.
    assert len(OrderSource.SHOPIFY.value) <= 16


def test_replayed_key_is_rejected_by_unique_index(db: Session) -> None:
    merchant_id = _merchant(db).id
    key = f"shopify-order-{uuid4().hex[:8]}"
    _make_order(db, merchant_id=merchant_id, idempotency_key=key)
    with pytest.raises(IntegrityError):
        _make_order(db, merchant_id=merchant_id, idempotency_key=key)
    db.rollback()


def test_same_key_across_merchants_is_allowed(db: Session) -> None:
    """Two shops can legitimately use order name #1001 on the same day."""
    key = f"shared-{uuid4().hex[:8]}"
    _make_order(db, merchant_id=_merchant(db).id, idempotency_key=key)
    _make_order(db, merchant_id=_merchant(db).id, idempotency_key=key)
    db.flush()


def test_null_keys_do_not_collide(db: Session) -> None:
    """Website orders and older portal builds carry no key and stay unconstrained."""
    merchant_id = _merchant(db).id
    for _ in range(3):
        _make_order(db, merchant_id=merchant_id, idempotency_key=None)
    db.flush()


def test_find_by_idempotency_key_is_merchant_scoped(db: Session) -> None:
    from porterchain_api.merchant_engine.booking_service import MerchantBookingService

    key = f"scoped-{uuid4().hex[:8]}"
    mine = _merchant(db).id
    theirs = _merchant(db).id
    _make_order(db, merchant_id=mine, idempotency_key=key)
    db.flush()

    service = MerchantBookingService()

    class _Ctx:
        def __init__(self, merchant_id: str) -> None:
            self.merchant = type("M", (), {"id": merchant_id})()

    assert service.find_by_idempotency_key(db, _Ctx(mine), key) is not None
    assert service.find_by_idempotency_key(db, _Ctx(theirs), key) is None
