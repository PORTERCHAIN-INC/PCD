"""Admin convert retail customer → merchant (order history remaps to merchant)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from porterchain_api.admin_engine.merchant_lifecycle import convert_from_customer
from porterchain_api.admin_engine.merchant_service import AdminMerchantService
from porterchain_api.booking_engine.numbers import generate_order_number, generate_tracking_number
from porterchain_api.booking_models import Customer, Order
from porterchain_api.domain.merchant_states import MerchantRole, MerchantStatus
from porterchain_api.domain.states import OrderState
from porterchain_api.merchant_models import Merchant, MerchantUser


def _convert(db, admin_ctx, settings, customer_id, **kwargs):
    return convert_from_customer(
        AdminMerchantService(), db, admin_ctx, settings, customer_id, **kwargs
    )


def test_convert_to_merchant_keeps_orders_and_soft_deletes_customer(
    db, admin_ctx, settings
) -> None:
    customer = Customer(
        auth_subject="pending:retail.convert@example.com",
        email="retail.convert@example.com",
        full_name="Retail Convert Co",
        phone="+15551234567",
    )
    db.add(customer)
    db.flush()
    order = Order(
        order_number=generate_order_number(),
        tracking_number=generate_tracking_number(),
        state=OrderState.DELIVERED.value,
        customer_id=customer.id,
        amount_cents=2500,
        pickup={"formatted": "A"},
        dropoff={"formatted": "B"},
        scheduled_at=datetime.now(UTC),
    )
    db.add(order)
    db.commit()

    first = _convert(
        db,
        admin_ctx,
        settings,
        customer.id,
        company_name="Retail Convert Co",
        auto_activate=False,
        send_invite=False,
    )
    assert first["idempotent"] is False
    merchant = db.get(Merchant, first["merchant_id"])
    assert merchant is not None
    assert merchant.email == "retail.convert@example.com"
    assert (merchant.profile or {}).get("converted_from_customer_id") == customer.id
    assert merchant.status in {
        MerchantStatus.PENDING.value,
        MerchantStatus.ONBOARDING.value,
        MerchantStatus.ACTIVE.value,
    }

    db.refresh(customer)
    assert customer.deleted_at is not None
    assert customer.delete_reason == "converted_to_merchant"
    assert str(customer.auth_subject).startswith("converted:")

    db.refresh(order)
    assert order.customer_id == customer.id
    assert order.merchant_id == merchant.id
    assert first.get("orders_remapped") == 1

    seat = (
        db.query(MerchantUser)
        .filter(MerchantUser.merchant_id == merchant.id, MerchantUser.email == merchant.email)
        .first()
    )
    assert seat is not None
    assert seat.role == MerchantRole.OWNER.value

    second = _convert(
        db,
        admin_ctx,
        settings,
        customer.id,
        company_name="Retail Convert Co",
        auto_activate=False,
        send_invite=False,
    )
    assert second["idempotent"] is True
    assert second["merchant_id"] == first["merchant_id"]


def test_convert_to_merchant_blocks_privacy_hold(db, admin_ctx, settings) -> None:
    customer = Customer(
        auth_subject="pending:hold.convert@example.com",
        email="hold.convert@example.com",
        full_name="Hold User",
        privacy_status="deletion_hold",
    )
    db.add(customer)
    db.commit()
    with pytest.raises(ValueError, match="customer_privacy_hold"):
        _convert(db, admin_ctx, settings, customer.id, send_invite=False)


def test_idempotent_convert_remaps_null_merchant_orders(db, admin_ctx, settings) -> None:
    """Already-converted customer (Kung Fu-like): re-hit remaps orphaned orders."""
    customer = Customer(
        auth_subject="converted:kft-remap-customer:kft-remap-merchant",
        email="kft.remap@example.com",
        full_name="KFT Remap Co",
        deleted_at=datetime.now(UTC),
        delete_reason="converted_to_merchant",
    )
    db.add(customer)
    db.flush()
    merchant = Merchant(
        email="kft.remap@example.com",
        company_name="KFT Remap Co",
        status=MerchantStatus.ACTIVE.value,
        profile={"converted_from_customer_id": customer.id},
    )
    db.add(merchant)
    db.flush()
    order = Order(
        order_number=generate_order_number(),
        tracking_number=generate_tracking_number(),
        state=OrderState.DELIVERED.value,
        customer_id=customer.id,
        merchant_id=None,
        amount_cents=1800,
        pickup={"formatted": "A"},
        dropoff={"formatted": "B"},
        scheduled_at=datetime.now(UTC),
    )
    db.add(order)
    db.commit()

    result = _convert(db, admin_ctx, settings, customer.id, send_invite=False)
    assert result["idempotent"] is True
    assert result["merchant_id"] == merchant.id
    assert result.get("orders_remapped") == 1
    db.refresh(order)
    assert order.merchant_id == merchant.id
