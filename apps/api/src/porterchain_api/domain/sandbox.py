"""Sandbox helpers shared by booking, tracking, labels, and lists."""

from __future__ import annotations

from porterchain_api.booking_models import Order


def order_is_sandbox(order: Order) -> bool:
    """True when the order is a test booking.

    ``Order.is_sandbox`` is SoT. Legacy rows may still carry
    ``compliance_metadata.sandbox`` from pre-column writes — dual-read only.
    """
    if bool(getattr(order, "is_sandbox", False)):
        return True
    meta = order.compliance_metadata if isinstance(order.compliance_metadata, dict) else {}
    return meta.get("sandbox") is True
