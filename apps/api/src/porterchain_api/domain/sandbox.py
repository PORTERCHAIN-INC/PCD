"""Sandbox helpers shared by booking, tracking, labels, and lists."""

from __future__ import annotations

from typing import Any

from porterchain_api.booking_models import Customer, Order


def order_is_sandbox(order: Order) -> bool:
    """True when the order is a test booking.

    ``Order.is_sandbox`` is SoT. Legacy rows may still carry
    ``compliance_metadata.sandbox`` from pre-column writes — dual-read only.
    """
    if bool(getattr(order, "is_sandbox", False)):
        return True
    meta = order.compliance_metadata if isinstance(order.compliance_metadata, dict) else {}
    return meta.get("sandbox") is True


def owner_sees_review_demo(db: Any, order: Order, clerk_user_id: str | None) -> bool:
    """App Review demo orders (sandbox + ``app_review_demo``) are visible to their signed-in owner only."""
    meta = order.compliance_metadata if isinstance(order.compliance_metadata, dict) else {}
    if meta.get("app_review_demo") is not True or not clerk_user_id or not order.customer_id:
        return False
    customer = db.get(Customer, order.customer_id)
    return bool(customer and customer.clerk_user_id == clerk_user_id)


def hidden_from_viewer(db: Any, order: Order, clerk_user_id: str | None = None) -> bool:
    """Public lookups hide sandbox orders, except a review-demo order for its owner."""
    return order_is_sandbox(order) and not owner_sees_review_demo(db, order, clerk_user_id)
