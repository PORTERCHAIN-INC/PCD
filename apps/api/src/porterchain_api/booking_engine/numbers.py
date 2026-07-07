"""Canonical number generators for booking engine."""

from datetime import UTC, datetime
import secrets


def _suffix() -> str:
    return secrets.token_hex(3).upper()


def generate_tracking_number() -> str:
    date_part = datetime.now(UTC).strftime("%Y%m%d")
    return f"PC-{date_part}-{_suffix()}"


def generate_order_number() -> str:
    date_part = datetime.now(UTC).strftime("%Y%m%d")
    return f"ORD-{date_part}-{_suffix()}"


def generate_invoice_number() -> str:
    date_part = datetime.now(UTC).strftime("%Y%m%d")
    return f"INV-{date_part}-{_suffix()}"


def generate_booking_number() -> str:
    date_part = datetime.now(UTC).strftime("%Y%m%d")
    return f"BKG-{date_part}-{_suffix()}"


def generate_payment_reference() -> str:
    date_part = datetime.now(UTC).strftime("%Y%m%d")
    return f"PAY-{date_part}-{_suffix()}"


def generate_receipt_number() -> str:
    date_part = datetime.now(UTC).strftime("%Y%m%d")
    return f"RCPT-{date_part}-{_suffix()}"


def generate_customer_reference() -> str:
    return f"CUST-{secrets.token_hex(4).upper()}"
