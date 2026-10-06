"""Parcel notice policy. One table. Email rows require an address.

Events not listed here stay in event_router until they move over.
"""

from __future__ import annotations

import uuid
from typing import Any

from porterchain_shared.events.catalog import DomainEventType

# Fleetbase echoes these. The driver (or proof) path already notifies.
_FLEETBASE_COVERED_STATES = frozenset(
    {
        "AT_PICKUP",
        "PICKED_UP",
        "IN_TRANSIT",
        "AT_DESTINATION",
        "DELIVERED",
        "POD_COMPLETED",
    }
)

def specs_for_parcel(event_type: str, payload: dict[str, Any], add: Any) -> bool:
    """Apply the parcel table. Return True when this event is owned here."""
    if payload.get("skip_notification") is True:
        return True

    customer_id = payload.get("customer_id")
    merchant_id = payload.get("merchant_id")
    driver_id = payload.get("driver_id") or payload.get("assigned_driver_id")
    email = payload.get("email") or payload.get("contact_email") or payload.get("receiver_email")
    merchant_email = payload.get("merchant_email")
    order_id = payload.get("order_id")

    def receiver_addresses() -> list[str]:
        found: list[str] = []
        seen: set[str] = set()
        candidates: list[Any] = [email, payload.get("receiver_email")]
        extra = payload.get("receiver_emails")
        if isinstance(extra, list):
            candidates.extend(extra)
        for item in candidates:
            if not isinstance(item, str) or "@" not in item:
                continue
            cleaned = item.strip()
            key = cleaned.lower()
            if key in seen:
                continue
            seen.add(key)
            found.append(cleaned)
        return found

    def email_customer(
        template: str,
        addresses: list[str] | None = None,
        *,
        category: str | None = None,
        pri: str | None = None,
    ) -> None:
        chosen = receiver_addresses() if addresses is None else addresses
        if not chosen:
            return
        rest = chosen
        if customer_id:
            add(template, "email", "customer", customer_id, address=chosen[0], category=category, pri=pri)
            rest = chosen[1:]
        for addr in rest:
            rid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{order_id or 'order'}:{addr.lower()}"))
            add(template, "email", "consignee", rid, address=addr, category=category, pri=pri)

    def one_address(value: Any) -> list[str]:
        if isinstance(value, str) and "@" in value:
            return [value.strip()]
        return []

    def email_merchant(template: str, *, category: str | None = None, pri: str | None = None) -> None:
        if merchant_email and merchant_id:
            add(
                template,
                "email",
                "merchant",
                merchant_id,
                address=merchant_email,
                category=category,
                pri=pri,
            )

    if event_type == DomainEventType.ORDER_CREATED:
        # Timeline only. The booked mail is order.booked / merchant.booking_created.
        if customer_id:
            add("order_created", "in_app", "customer", customer_id)
        if merchant_id:
            add("order_created", "in_app", "merchant", merchant_id)
        return True

    if event_type in (DomainEventType.ORDER_BOOKED, "merchant.booking_created"):
        if customer_id:
            add("order_booked", "in_app", "customer", customer_id)
        email_customer("order_booked")
        if merchant_id:
            add("order_booked", "in_app", "merchant", merchant_id)
        email_merchant("order_booked")
        return True

    if event_type == DomainEventType.BOOKING_CONFIRMED:
        # In-app only. Email already went out on order.booked.
        if customer_id:
            add("booking_confirmed", "in_app", "customer", customer_id)
        if merchant_id:
            add("booking_confirmed", "in_app", "merchant", merchant_id)
        return True

    if event_type == DomainEventType.PARCEL_PICKED_UP:
        if customer_id:
            add("parcel_picked_up", "push", "customer", customer_id)
            add("parcel_picked_up", "in_app", "customer", customer_id)
        pickup = one_address(payload.get("pickup_email")) or receiver_addresses()[:1]
        email_customer("parcel_picked_up", pickup)
        if merchant_id:
            add("parcel_picked_up", "in_app", "merchant", merchant_id)
        email_merchant("parcel_picked_up")
        return True

    if event_type == DomainEventType.PARCEL_DELIVERED:
        if customer_id:
            add("delivered", "in_app", "customer", customer_id)
            add("delivered", "push", "customer", customer_id)
        final = one_address(payload.get("stop_email")) or receiver_addresses()[-1:]
        email_customer("delivered", final)
        if driver_id:
            add("delivered", "in_app", "driver", driver_id)
        if merchant_id:
            add("delivered", "in_app", "merchant", merchant_id)
        email_merchant("delivered")
        return True

    if event_type == "order.stop_completed":
        if customer_id:
            add("delivered", "in_app", "customer", customer_id)
            add("delivered", "push", "customer", customer_id)
        stop_only = one_address(payload.get("stop_email") or payload.get("contact_email"))
        email_customer("delivered", stop_only)
        if merchant_id:
            add("delivered", "in_app", "merchant", merchant_id)
        return True

    if event_type in (DomainEventType.CHECKOUT_ABANDONED, "checkout.abandoned"):
        buyer = payload.get("email")
        recovery = payload.get("recovery_url")
        if (
            isinstance(buyer, str)
            and "@" in buyer
            and isinstance(recovery, str)
            and recovery.startswith("http")
        ):
            rid = str(payload.get("customer_id") or "") or str(
                uuid.uuid5(uuid.NAMESPACE_URL, buyer.strip().lower())
            )
            add("checkout_recovery", "email", "customer", rid, address=buyer.strip())
        return True

    if event_type == "order.failed":
        from porterchain_api.notification_engine.staff_fanout import staff_sentinel

        if customer_id:
            add("exception_opened", "in_app", "customer", customer_id, category="orders", pri="high")
            add("exception_opened", "push", "customer", customer_id, category="orders", pri="high")
        email_customer("exception_opened", category="orders", pri="high")
        if merchant_id:
            add("exception_opened", "in_app", "merchant", merchant_id, category="orders", pri="high")
        email_merchant("exception_opened", category="orders", pri="high")
        ops = staff_sentinel("ops")
        add("exception_opened", "in_app", "admin", ops, category="orders", pri="high")
        add("exception_opened", "push", "admin", ops, category="orders", pri="high")
        add("exception_opened", "email", "admin", ops, category="orders", pri="high")
        return True

    if event_type == DomainEventType.FLEETBASE_STATUS_UPDATED:
        state = str(payload.get("to_state") or payload.get("status") or "").upper()
        if state in _FLEETBASE_COVERED_STATES:
            return True
        return False
