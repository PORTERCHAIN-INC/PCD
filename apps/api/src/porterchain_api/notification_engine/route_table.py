"""Parcel notice policy. One table. Email rows require an address.

Events not listed here stay in event_router until they move over.

Receiver-facing delivery moments (delivered, failed attempt) share a dedupe family
with the recipient-experience emails (customer_experience.notifications), so one
address gets one email per moment no matter which path fires first.
"""

from __future__ import annotations

import uuid
from typing import Any

from porterchain_shared.events.catalog import DomainEventType

#: A failed attempt email is one per order+address per 6 h (several events can fire).
ATTEMPT_WINDOW_SEC = 6 * 3600


def delivered_family(order_id: Any, address: str) -> str:
    return f"delivered|{order_id}|{address.strip().lower()}"


def attempt_family(order_id: Any, address: str, attempt: Any = None) -> str:
    """One missed-delivery email per attempt. Without an attempt number the 6 h window applies."""
    return f"attempt|{order_id}|{attempt if attempt not in (None, '') else 'x'}|{address.strip().lower()}"



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
        family: Any = None,
        window: int | None = None,
    ) -> None:
        chosen = receiver_addresses() if addresses is None else addresses
        if not chosen:
            return

        def fam(addr: str) -> dict[str, Any]:
            if family is None or not order_id:
                return {}
            return {"dedupe": family(order_id, addr), "dedupe_window": window}

        rest = chosen
        if customer_id:
            add(template, "email", "customer", customer_id, address=chosen[0], category=category, pri=pri, **fam(chosen[0]))
            rest = chosen[1:]
        for addr in rest:
            rid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{order_id or 'order'}:{addr.lower()}"))
            add(template, "email", "consignee", rid, address=addr, category=category, pri=pri, **fam(addr))

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
        email_customer("delivered", final, family=delivered_family)
        if driver_id:
            add("delivered", "in_app", "driver", driver_id)
        if merchant_id:
            add("delivered", "in_app", "merchant", merchant_id)
        email_merchant("delivered")
        # Customer fast-book: one Send-again email (eligibility set by customer_fast.mailer).
        if customer_id and payload.get("send_again_eligible") and payload.get("send_again_email"):
            add(
                "fast_send_again",
                "email",
                "customer",
                customer_id,
                address=payload["send_again_email"],
                category="reorder",
                pri="low",
            )
        return True

    if event_type == DomainEventType.CUSTOMER_REORDER_NUDGE:
        # Only reached after staff approval with reorder_nudges_enabled on (admin360).
        if customer_id and payload.get("send_again_email"):
            add(
                "fast_send_again",
                "email",
                "customer",
                customer_id,
                address=payload["send_again_email"],
                category="reorder",
                pri="low",
            )
        return True

    if event_type == "order.stop_completed":
        if customer_id:
            add("delivered", "in_app", "customer", customer_id)
            add("delivered", "push", "customer", customer_id)
        stop_only = one_address(payload.get("stop_email") or payload.get("contact_email"))
        email_customer("delivered", stop_only, family=delivered_family)
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

    if event_type in ("order.failed", "order.delivery_failed"):
        from porterchain_api.notification_engine.staff_fanout import staff_sentinel

        template = "delivery_failed"
        if customer_id:
            add(template, "in_app", "customer", customer_id, category="orders", pri="high")
            add(template, "push", "customer", customer_id, category="orders", pri="high")
        # Receiver: the recipient-experience "attempted" email (with one-tap reschedule)
        # normally wins this family; this is the fallback when that stream is off.
        attempt_no = payload.get("attempts")
        email_customer(
            template,
            category="orders",
            pri="high",
            family=lambda oid, addr: attempt_family(oid, addr, attempt_no),
            window=None if attempt_no not in (None, "") else ATTEMPT_WINDOW_SEC,
        )
        if merchant_id:
            add(template, "in_app", "merchant", merchant_id, category="orders", pri="high")
        email_merchant(template, category="orders", pri="high")
        if driver_id:
            add(template, "in_app", "driver", driver_id, category="orders")
        ops = staff_sentinel("ops")
        add(template, "in_app", "admin", ops, category="orders", pri="high")
        add(template, "push", "admin", ops, category="orders", pri="high")
        add(template, "email", "admin", ops, category="orders", pri="high")
        return True

    if event_type == "order.rescheduled":
        from porterchain_api.notification_engine.staff_fanout import staff_sentinel

        template = "order_rescheduled"
        if customer_id:
            add(template, "in_app", "customer", customer_id, category="tracking")
        # Receiver confirmation is the recipient-experience "rescheduled" email.
        if merchant_id:
            add(template, "in_app", "merchant", merchant_id, category="orders")
        email_merchant(template, category="orders")
        if driver_id:
            add(template, "in_app", "driver", driver_id, category="orders")
        ops = staff_sentinel("ops")
        add(template, "in_app", "admin", ops, category="orders")
        add(template, "email", "admin", ops, category="orders")
        return True
