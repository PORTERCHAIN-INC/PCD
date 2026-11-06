"""Remap order history when converting customer ↔ merchant.

Merchant portal history filters on ``Order.merchant_id``. Customer history
filters on ``Order.customer_id``. Convert must attach past orders so they
follow the new account — leaving the other FK NULL orphans history (the
Kung Fu Tea case).
"""

from __future__ import annotations

from sqlalchemy.orm import Session


def remap_orders_customer_to_merchant(
    db: Session, *, customer_id: str, merchant_id: str
) -> int:
    """Set merchant_id on this customer's orders that have no merchant yet."""
    from porterchain_api.booking_models import Order

    count = (
        db.query(Order)
        .filter(Order.customer_id == customer_id, Order.merchant_id.is_(None))
        .update({Order.merchant_id: merchant_id}, synchronize_session=False)
    )
    return int(count or 0)


def remap_orders_merchant_to_customer(
    db: Session, *, merchant_id: str, customer_id: str
) -> int:
    """Set customer_id on this merchant's orders that have no customer yet."""
    from porterchain_api.booking_models import Order

    count = (
        db.query(Order)
        .filter(Order.merchant_id == merchant_id, Order.customer_id.is_(None))
        .update({Order.customer_id: customer_id}, synchronize_session=False)
    )
    return int(count or 0)
