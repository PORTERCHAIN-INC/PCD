"""Canonical number generators for booking engine."""

from datetime import datetime
import secrets
from zoneinfo import ZoneInfo

# L106: the date part is the Toronto business day, not the UTC day.
TORONTO = ZoneInfo("America/Toronto")


def _suffix() -> str:
    return secrets.token_hex(3).upper()


def _order_suffix() -> str:
    # 40 bits: 24 bits gave a ~50% chance of a same-day duplicate (unique index
    # violation) at ~5,000 orders/day (birthday bound). Fits the 32-char columns.
    return secrets.token_hex(5).upper()


def generate_tracking_number() -> str:
    date_part = datetime.now(TORONTO).strftime("%Y%m%d")
    return f"PC-{date_part}-{_order_suffix()}"


def generate_order_number() -> str:
    date_part = datetime.now(TORONTO).strftime("%Y%m%d")
    return f"ORD-{date_part}-{_order_suffix()}"


def generate_invoice_number(*, prefix: str | None = None) -> str:
    date_part = datetime.now(TORONTO).strftime("%Y%m%d")
    head = (prefix or "INV").strip().upper() or "INV"
    return f"{head}-{date_part}-{_suffix()}"


def generate_booking_number() -> str:
    date_part = datetime.now(TORONTO).strftime("%Y%m%d")
    return f"BKG-{date_part}-{_suffix()}"


def generate_payment_reference() -> str:
    date_part = datetime.now(TORONTO).strftime("%Y%m%d")
    return f"PAY-{date_part}-{_suffix()}"


def generate_receipt_number(*, prefix: str | None = None) -> str:
    date_part = datetime.now(TORONTO).strftime("%Y%m%d")
    head = (prefix or "RCP").strip().upper() or "RCP"
    return f"{head}-{date_part}-{_suffix()}"


def generate_customer_reference() -> str:
    return f"CUST-{secrets.token_hex(4).upper()}"
