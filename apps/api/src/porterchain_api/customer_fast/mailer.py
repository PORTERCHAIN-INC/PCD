"""Send-again email eligibility. The notification router owns dispatch (§3.3.3).

``enrich_send_again`` runs inside ``event_router.handle_domain_event`` on parcel.delivered and
adds ``send_again_url`` / ``unsubscribe_url`` / ``send_again_eligible`` to the payload; the
router then adds the ``fast_send_again`` email spec. One email per order.
"""

from __future__ import annotations

from typing import Any

from porterchain_shared.events.catalog import DomainEventType


def enrich_send_again(db: Any, settings: Any, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    if event_type != DomainEventType.PARCEL_DELIVERED or not payload.get("order_id"):
        return payload
    from porterchain_api.booking_models import Customer, Order
    from porterchain_api.crm_suppression import is_suppressed
    from porterchain_api.customer_fast import service
    from porterchain_api.customer_fast.rules import order_locale

    order = db.get(Order, str(payload["order_id"]))
    if order is None or order.merchant_id or not order.customer_id or order.is_sandbox:
        return payload
    meta = dict(order.compliance_metadata or {}) if isinstance(order.compliance_metadata, dict) else {}
    if meta.get("send_again_queued"):
        return payload
    customer = db.get(Customer, order.customer_id)
    if customer is None or not customer.email or customer.privacy_status == "deletion_hold":
        return payload
    if is_suppressed(db, email=customer.email):
        return payload
    reorder = service.latest_consent(db, customer.id, "reorder")
    if reorder is not None and not reorder.granted:
        return payload
    meta["send_again_queued"] = True
    order.compliance_metadata = meta
    db.flush()
    return {
        **payload,
        "customer_id": customer.id,
        "send_again_email": customer.email,
        "send_again_eligible": True,
        "send_again_url": service.send_again_url(settings, order),
        "unsubscribe_url": service.preferences_url(settings, customer),
        "locale": order_locale(order),
    }
