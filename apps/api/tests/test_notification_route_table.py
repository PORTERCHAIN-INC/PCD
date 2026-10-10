"""Parcel route table: one booked mail, pickup and delivery mail, no address means no email."""

from porterchain_shared.events.catalog import DomainEventType

from porterchain_api.notification_engine.event_router import _specs_for_event


def _payload(**extra: object) -> dict:
    base = {
        "customer_id": "cust-1",
        "merchant_id": "merch-1",
        "driver_id": "drv-1",
        "email": "receiver@example.com",
        "merchant_email": "merchant@example.com",
        "order_id": "ord-1",
        "order_number": "ORD-1",
        "tracking_number": "TRK-1",
    }
    base.update(extra)
    return base


def _channels(event_type: str, **extra: object) -> set[tuple[str, str, str]]:
    specs = _specs_for_event(event_type, _payload(**extra))
    return {(s["recipient_type"], s["channel"], s["template_key"]) for s in specs}


def test_booked_email_includes_absolute_track_link() -> None:
    from porterchain_api.notification_engine.templates import render_email

    _subject, _text, html = render_email(
        "order_booked",
        {
            "order_number": "ORD-1",
            "tracking_number": "TRK-1",
            "public_track_url": "https://porterchain.com/track/TRK-1",
        },
    )
    assert "https://porterchain.com/track/TRK-1" in html
    assert "Track this shipment" in html
    assert "https://porterchain.com/track/TRK-1" in _text


def test_order_created_is_in_app_only() -> None:
    channels = _channels(DomainEventType.ORDER_CREATED)
    assert ("customer", "email", "order_created") not in channels
    assert ("customer", "in_app", "order_created") in channels
    assert ("merchant", "in_app", "order_created") in channels


def test_each_dropoff_contact_gets_a_booked_email() -> None:
    specs = _specs_for_event(
        DomainEventType.ORDER_BOOKED,
        {
            "customer_id": "cust-1",
            "merchant_id": "merch-1",
            "merchant_email": "merchant@example.com",
            "email": "buyer@example.com",
            "order_id": "ord-1",
            "receiver_emails": ["dock@example.com", "buyer@example.com"],
        },
    )
    emailed = {
        s["recipient_address"].lower()
        for s in specs
        if s["channel"] == "email" and s["template_key"] == "order_booked" and s["recipient_type"] != "merchant"
    }
    assert emailed == {"buyer@example.com", "dock@example.com"}


def test_pickup_emails_the_first_contact_and_delivery_emails_the_last() -> None:
    payload = {
        "customer_id": "cust-1",
        "email": "pickup@example.com",
        "order_id": "ord-1",
        "receiver_emails": ["dock@example.com"],
        "pickup_email": "pickup@example.com",
    }
    picked = {
        s["recipient_address"].lower()
        for s in _specs_for_event(DomainEventType.PARCEL_PICKED_UP, payload)
        if s["channel"] == "email"
    }
    assert picked == {"pickup@example.com"}
    delivered = {
        s["recipient_address"].lower()
        for s in _specs_for_event(DomainEventType.PARCEL_DELIVERED, payload)
        if s["channel"] == "email" and s["recipient_type"] != "merchant"
    }
    assert delivered == {"dock@example.com"}
    stop = _specs_for_event(
        "order.stop_completed",
        {**payload, "stop_email": "middle@example.com"},
    )
    stop_mail = [s["recipient_address"].lower() for s in stop if s["channel"] == "email"]
    assert stop_mail == ["middle@example.com"]
    channels = _channels(DomainEventType.ORDER_BOOKED)
    assert ("customer", "email", "order_booked") in channels
    assert ("merchant", "email", "order_booked") in channels
    assert ("customer", "in_app", "order_booked") in channels


def test_booking_confirmed_does_not_repeat_the_email() -> None:
    channels = _channels(DomainEventType.BOOKING_CONFIRMED)
    assert ("customer", "email", "booking_confirmed") not in channels
    assert ("customer", "in_app", "booking_confirmed") in channels


def test_merchant_booking_uses_the_booked_row() -> None:
    channels = _channels("merchant.booking_created")
    assert ("customer", "email", "order_booked") in channels
    assert ("merchant", "email", "order_booked") in channels


def test_pickup_and_delivery_email_both_sides() -> None:
    picked = _channels(DomainEventType.PARCEL_PICKED_UP)
    assert ("customer", "email", "parcel_picked_up") in picked
    assert ("merchant", "email", "parcel_picked_up") in picked
    delivered = _channels(DomainEventType.PARCEL_DELIVERED)
    assert ("customer", "email", "delivered") in delivered
    assert ("merchant", "email", "delivered") in delivered
    assert ("driver", "in_app", "delivered") in delivered


def test_email_skipped_without_address() -> None:
    specs = _specs_for_event(
        DomainEventType.ORDER_BOOKED,
        {
            "customer_id": "cust-1",
            "merchant_id": "merch-1",
            "order_number": "ORD-1",
        },
    )
    assert all(s["channel"] != "email" for s in specs)
    assert any(s["channel"] == "in_app" for s in specs)


def test_receiver_email_when_there_is_no_customer_account() -> None:
    specs = _specs_for_event(
        DomainEventType.ORDER_BOOKED,
        {
            "merchant_id": "merch-1",
            "merchant_email": "merchant@example.com",
            "receiver_email": "door@example.com",
            "order_id": "ord-1",
        },
    )
    consignee = [s for s in specs if s["recipient_type"] == "consignee"]
    assert len(consignee) == 1
    assert consignee[0]["recipient_address"] == "door@example.com"
    assert consignee[0]["channel"] == "email"


def test_cancel_merchant_email_requires_address() -> None:
    specs = _specs_for_event(
        DomainEventType.ORDER_CANCELLED,
        {"customer_id": "c1", "merchant_id": "m1", "email": "c@example.com"},
    )
    merchant_email = [s for s in specs if s["recipient_type"] == "merchant" and s["channel"] == "email"]
    assert merchant_email == []
    assert any(s["recipient_type"] == "customer" and s["channel"] == "email" for s in specs)


def test_skip_notification_sends_nothing() -> None:
    assert _specs_for_event(DomainEventType.PARCEL_DELIVERED, {**_payload(), "skip_notification": True}) == []


def test_checkout_abandoned_emails_when_a_recovery_link_exists() -> None:
    specs = _specs_for_event(
        "checkout.abandoned",
        {
            "email": "buyer@example.com",
            "quote_id": "quote-1",
            "recovery_url": "https://porterchain.com/sign-up?intent=quote&quote_id=quote-1",
        },
    )
    assert specs[0]["template_key"] == "checkout_recovery"
    assert specs[0]["channel"] == "email"
    assert specs[0]["recipient_address"] == "buyer@example.com"


def test_failed_delivery_reaches_customer_merchant_and_ops() -> None:
    for event in ("order.failed", "order.delivery_failed"):
        channels = _channels(event)
        assert ("customer", "email", "delivery_failed") in channels
        assert ("merchant", "in_app", "delivery_failed") in channels
        assert ("merchant", "email", "delivery_failed") in channels
        assert ("driver", "in_app", "delivery_failed") in channels
        assert ("admin", "email", "delivery_failed") in channels
        assert ("admin", "in_app", "delivery_failed") in channels


def test_high_priority_lead_stays_off_the_parcel_router() -> None:
    # Lead Agent owns the unassigned-high notice. A new quote is not a parcel status.
    assert _specs_for_event("lead.created", {"priority": "high", "company_name": "Acme", "lead_id": "lead-1"}) == []
    assert _specs_for_event("lead.created", {"priority": "low"}) == []
