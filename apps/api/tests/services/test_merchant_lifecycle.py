"""Merchant close / convert, CLOSED kick-out, seat reactivate, quote TTL, reminders."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from porterchain_api.admin_engine.merchant_lifecycle import (
    operational_order_count,
    outstanding_cents,
)
from porterchain_api.admin_engine.merchant_service import AdminMerchantService
from porterchain_api.auth.merchant import portal_access_denied
from porterchain_api.booking_engine.numbers import generate_invoice_number, generate_order_number, generate_tracking_number
from porterchain_api.domain.merchant_states import MerchantRole, MerchantStatus
from porterchain_api.domain.states import OrderState
from porterchain_api.merchant_engine.booking_flow_service import MerchantBookingFlowService
from porterchain_api.merchant_engine.invoice_reminder import primary_billing_email
from porterchain_api.merchant_engine.team_service import MerchantTeamService, seat_status
from porterchain_api.merchant_models import MerchantUser
from porterchain_api.booking_models import Customer, Invoice, Order


def test_portal_access_denied_closed_and_suspended(merchant_ctx) -> None:
    merchant_ctx.merchant.status = MerchantStatus.CLOSED.value
    assert portal_access_denied(merchant_ctx.merchant) == "merchant_closed"
    merchant_ctx.merchant.status = MerchantStatus.SUSPENDED.value
    assert portal_access_denied(merchant_ctx.merchant) == "merchant_suspended"
    merchant_ctx.merchant.status = MerchantStatus.ACTIVE.value
    assert portal_access_denied(merchant_ctx.merchant) is None


def test_close_blocked_by_live_orders(db, admin_ctx, merchant_ctx) -> None:
    order = Order(
        order_number=generate_order_number(),
        tracking_number=generate_tracking_number(),
        state=OrderState.BOOKED.value,
        merchant_id=merchant_ctx.merchant.id,
        amount_cents=1200,
        pickup={"formatted": "A"},
        dropoff={"formatted": "B"},
        scheduled_at=datetime.now(UTC),
    )
    db.add(order)
    db.commit()
    assert operational_order_count(db, merchant_ctx.merchant.id) == 1
    with pytest.raises(ValueError, match="close_blocked_live_orders"):
        AdminMerchantService().close_merchant(
            db, admin_ctx, merchant_ctx.merchant.id, reason="offboard"
        )


def test_close_blocked_by_outstanding_ar(db, admin_ctx, merchant_ctx) -> None:
    order = Order(
        order_number=generate_order_number(),
        tracking_number=generate_tracking_number(),
        state=OrderState.INVOICED.value,
        merchant_id=merchant_ctx.merchant.id,
        amount_cents=5000,
        payment_terms="NET_30",
        pickup={"formatted": "A"},
        dropoff={"formatted": "B"},
        scheduled_at=datetime.now(UTC),
    )
    db.add(order)
    db.flush()
    db.add(
        Invoice(
            invoice_number=generate_invoice_number(),
            order_id=order.id,
            merchant_id=merchant_ctx.merchant.id,
            amount_cents=5000,
            tax_cents=0,
            fees_cents=0,
            currency="cad",
        )
    )
    db.commit()
    db.refresh(merchant_ctx.merchant)
    assert outstanding_cents(db, merchant_ctx.merchant) > 0
    with pytest.raises(ValueError, match="close_blocked_outstanding_ar"):
        AdminMerchantService().close_merchant(
            db, admin_ctx, merchant_ctx.merchant.id, reason="offboard"
        )


def test_close_and_kick_out(db, admin_ctx, merchant_ctx) -> None:
    merchant_ctx.user.role = MerchantRole.OWNER.value
    db.commit()
    closed = AdminMerchantService().close_merchant(
        db, admin_ctx, merchant_ctx.merchant.id, reason="left network"
    )
    assert closed.status == MerchantStatus.CLOSED.value
    db.refresh(merchant_ctx.user)
    assert merchant_ctx.user.is_active is False
    assert portal_access_denied(closed) == "merchant_closed"


def test_convert_creates_customer_without_moving_orders(db, admin_ctx, merchant_ctx) -> None:
    merchant_ctx.user.role = MerchantRole.OWNER.value
    merchant_ctx.user.email = merchant_ctx.merchant.email
    order = Order(
        order_number=generate_order_number(),
        tracking_number=generate_tracking_number(),
        state=OrderState.DELIVERED.value,
        merchant_id=merchant_ctx.merchant.id,
        amount_cents=0,
        pickup={"formatted": "A"},
        dropoff={"formatted": "B"},
        scheduled_at=datetime.now(UTC),
    )
    db.add(order)
    db.commit()
    result = AdminMerchantService().convert_to_customer(
        db, admin_ctx, merchant_ctx.merchant.id, owner_email=merchant_ctx.merchant.email
    )
    customer = db.query(Customer).filter(Customer.id == result["customer_id"]).first()
    assert customer is not None
    assert customer.email == merchant_ctx.merchant.email.lower()
    assert not str(customer.clerk_user_id).startswith("user_")
    db.refresh(order)
    assert order.merchant_id == merchant_ctx.merchant.id
    assert order.customer_id is None
    db.refresh(merchant_ctx.merchant)
    assert merchant_ctx.merchant.status == MerchantStatus.CLOSED.value


def test_reactivate_off_seat(db, merchant_ctx) -> None:
    merchant_ctx.user.role = MerchantRole.OWNER.value
    extra = MerchantUser(
        merchant_id=merchant_ctx.merchant.id,
        clerk_user_id="pending:ops@example.com",
        email="ops@example.com",
        role="merchant_ops",
        is_active=False,
    )
    db.add(extra)
    db.commit()
    assert seat_status(extra) == "off"
    updated = MerchantTeamService().update_member(
        db, merchant_ctx, extra.id, is_active=True
    )
    assert updated.is_active is True
    assert seat_status(updated) == "pending"


def test_confirm_draft_rejects_expired_quote(settings) -> None:
    draft = SimpleNamespace(
        expires_at=datetime.now(UTC) - timedelta(minutes=1),
        updated_at=datetime.now(UTC) - timedelta(hours=2),
        created_at=datetime.now(UTC) - timedelta(hours=2),
    )
    with pytest.raises(ValueError, match="quote_expired"):
        MerchantBookingFlowService()._assert_quote_fresh(draft, settings)


def test_primary_billing_email_prefers_primary_contact(merchant_ctx) -> None:
    merchant_ctx.merchant.email = "company@example.com"
    merchant_ctx.merchant.profile = {
        "settings": {
            "billing_contacts": [
                {"email": "ap@example.com", "is_primary": True},
                {"email": "ops@example.com", "is_primary": False},
            ]
        }
    }
    assert primary_billing_email(merchant_ctx.merchant) == "ap@example.com"
