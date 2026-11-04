"""Booking request helpers: idempotency key parsing, error detail, confirm replay payload.

Split from ``booking_service`` (ENG-G2 ≤500 LOC); re-exported there unchanged.
"""

from __future__ import annotations

from porterchain_api.booking_models import Order


def parse_idempotency_key(raw: str | None, *, max_len: int = 128) -> str | None:
    key = (raw or "").strip() or None
    if key and len(key) > max_len:
        raise ValueError("idempotency_key_too_long")
    return key


def booking_value_error_detail(exc: BaseException) -> str:
    detail = str(exc)
    if detail == "quote_expired":
        return "This quote expired. Request a new price before booking."
    return detail


def confirm_replay_payload(order: Order) -> dict:
    from porterchain_api.domain.sandbox import order_is_sandbox

    sandbox = order_is_sandbox(order)
    return {
        "order_id": order.id,
        "order_number": order.order_number,
        "tracking_number": order.tracking_number,
        "amount_cents": order.amount_cents,
        "preview": {"valid": True, "amount_cents": order.amount_cents},
        "is_sandbox": sandbox,
        "public_track_url": None,
        "consignee_email": None,
        "consignee_emailed": False,
    }
