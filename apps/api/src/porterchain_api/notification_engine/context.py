"""Shared notification context contract + Order hydration."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


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
        "is_sandbox": bool(getattr(order, "is_sandbox", False)),
        "admin_deep_link": f"/orders/{order.id}",
        "merchant_deep_link": f"/orders/{order.id}",
        "driver_deep_link": f"/jobs/{order.id}",
        "deep_link": f"/orders/{order.id}",
    }
    if order.tracking_number:
        out["customer_deep_link"] = f"/track/{order.tracking_number}"
        try:
            from porterchain_api.config import get_settings
            from porterchain_api.merchant_engine.tracking_views import public_track_url

            track = public_track_url(
                get_settings(),
                order.tracking_number,
                is_sandbox=bool(getattr(order, "is_sandbox", False)),
            )
            if track:
                out["public_track_url"] = track
        except Exception:  # noqa: BLE001 — notice still sends without a button
            pass

    meta = order.compliance_metadata if isinstance(order.compliance_metadata, dict) else {}
    consignee = meta.get("consignee") if isinstance(meta.get("consignee"), dict) else {}
    receiver = consignee.get("email") if isinstance(consignee, dict) else None
    if isinstance(receiver, str) and "@" in receiver:
        out["receiver_email"] = receiver.strip()
    stop_emails: list[str] = []
    pickup_email: str | None = None
    stops = meta.get("stops") if isinstance(meta.get("stops"), list) else []
    for stop in stops:
        if not isinstance(stop, dict):
            continue
        contact = stop.get("contact_email")
        kind = str(stop.get("type") or stop.get("stop_type") or "").lower()
        if isinstance(contact, str) and "@" in contact:
            cleaned = contact.strip()
            stop_emails.append(cleaned)
            if kind == "pickup" and pickup_email is None:
                pickup_email = cleaned
    if isinstance(receiver, str) and "@" in receiver:
        stop_emails.insert(0, receiver.strip())
    if stop_emails:
        out["receiver_emails"] = stop_emails
    if pickup_email:
        out["pickup_email"] = pickup_email

    if order.customer_id:
        customer = db.get(Customer, order.customer_id)
        if customer and customer.email:
            out["email"] = customer.email
            out["contact_email"] = customer.email

    _add_business_order_details(db, order, out)

    merchant = db.get(Merchant, order.merchant_id) if order.merchant_id else None
    if merchant:
        out["merchant_name"] = merchant.company_name
        if merchant.email:
            out["merchant_email"] = merchant.email

    # Receiver-email language + links (French templates, report-a-problem, privacy).
    try:
        from porterchain_api.config import get_settings
        from porterchain_api.customer_experience.context import recipient_language
        from porterchain_api.customer_experience.settings import cx_for_merchant

        cfg = cx_for_merchant(merchant)
        out["lang"] = recipient_language(order, cfg["notifications"].get("language", "auto"))
        out["website_url"] = get_settings().website_url
        from porterchain_api.customer_experience.settings import email_brand

        out.update(email_brand(merchant, cfg))
        if cfg["tracking"].get("support_email"):
            out["support_email"] = cfg["tracking"]["support_email"]
    except Exception:  # noqa: BLE001 — English default is fine
        out.setdefault("lang", "en")

    return {k: v for k, v in out.items() if v is not None}


def _address_line(value: Any) -> str | None:
    if isinstance(value, dict):
        text = str(value.get("formatted") or value.get("address") or "").strip()
        return text or None
    if isinstance(value, str):
        return value.strip() or None
    return None


def _add_business_order_details(db: Session, order: Any, out: dict[str, Any]) -> None:
    """Merchant pickup/delivered mail: driver's name only (never phone/email), addresses, portal link."""
    driver_id = getattr(order, "assigned_driver_id", None)
    if driver_id:
        try:
            from porterchain_api.admin_models import Driver

            driver = db.get(Driver, driver_id)
            name = (getattr(driver, "full_name", None) or "").strip() if driver else ""
            if name:
                out["driver_name"] = name
        except Exception:  # the notice still sends without a name
            logger.debug("driver name lookup failed for order %s", order.id, exc_info=True)
    pickup = _address_line(getattr(order, "pickup", None))
    dropoff = _address_line(getattr(order, "dropoff", None))
    if pickup:
        out["pickup_address"] = pickup
    if dropoff:
        out["dropoff_address"] = dropoff
    if getattr(order, "merchant_id", None):
        try:
            from porterchain_api.config import get_settings

            base = (get_settings().merchant_portal_url or "").rstrip("/")
            if base.startswith("http"):
                out["merchant_order_url"] = f"{base}/orders/{order.id}"
        except Exception:  # the notice falls back to public tracking
            logger.debug("merchant portal url unavailable", exc_info=True)


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
