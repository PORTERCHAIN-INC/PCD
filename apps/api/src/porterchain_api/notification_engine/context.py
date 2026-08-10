"""Shared notification context contract + Order hydration."""

from __future__ import annotations

from typing import Any, TypedDict

from sqlalchemy.orm import Session


class NotificationContext(TypedDict, total=False):
    """Fields emitters should provide (or that hydrate fills from Order)."""

    order_id: str
    order_number: str
    tracking_number: str
    customer_id: str
    merchant_id: str
    merchant_name: str
    merchant_email: str
    driver_id: str
    email: str
    contact_email: str
    deep_link: str
    customer_deep_link: str
    merchant_deep_link: str
    driver_deep_link: str
    admin_deep_link: str
    status: str
    message: str
    exception_type: str
    exception_id: str


def hydrate_order_context(db: Session, order_id: str | None) -> dict[str, Any]:
    """Load order-linked identities for notification routing.

    Returns a plain dict suitable for merging into an event payload.
    Missing order yields {}.
    """
    if not order_id:
        return {}

    from porterchain_api.booking_models import Customer, Order
    from porterchain_api.merchant_models import Merchant

    order = db.get(Order, order_id)
    if not order:
        return {}

    out: dict[str, Any] = {
        "order_id": order.id,
        "order_number": order.order_number,
        "tracking_number": order.tracking_number,
        "customer_id": order.customer_id,
        "merchant_id": order.merchant_id,
        "driver_id": order.assigned_driver_id,
        "status": order.state,
        "admin_deep_link": f"/orders/{order.id}",
        "merchant_deep_link": f"/orders/{order.id}",
        "driver_deep_link": f"/jobs/{order.id}",
        "deep_link": f"/orders/{order.id}",
    }
    if order.tracking_number:
        out["customer_deep_link"] = f"/track/{order.tracking_number}"

    if order.customer_id:
        customer = db.get(Customer, order.customer_id)
        if customer and customer.email:
            out["email"] = customer.email
            out["contact_email"] = customer.email

    if order.merchant_id:
        merchant = db.get(Merchant, order.merchant_id)
        if merchant:
            out["merchant_name"] = merchant.company_name
            if merchant.email:
                out["merchant_email"] = merchant.email

    return {k: v for k, v in out.items() if v is not None}


def merge_notification_context(
    payload: dict[str, Any] | None,
    hydrated: dict[str, Any] | None,
) -> dict[str, Any]:
    """Payload wins; hydrated fills gaps."""
    base = dict(hydrated or {})
    for key, value in (payload or {}).items():
        if value is not None:
            base[key] = value
    return base


def deep_link_for(recipient_type: str, payload: dict[str, Any]) -> str | None:
    if recipient_type == "customer":
        return payload.get("customer_deep_link") or payload.get("deep_link")
    if recipient_type == "merchant":
        return payload.get("merchant_deep_link") or payload.get("deep_link")
    if recipient_type == "driver":
        return payload.get("driver_deep_link") or payload.get("deep_link")
    if recipient_type in ("admin", "finance", "support"):
        return payload.get("admin_deep_link") or payload.get("deep_link")
    return payload.get("deep_link")
