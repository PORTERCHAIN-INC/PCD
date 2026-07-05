"""Reference number generator tests."""

import re

from porterchain_api.booking_engine import numbers


def test_tracking_number_format() -> None:
    value = numbers.generate_tracking_number()
    assert re.match(r"^PC-\d{8}-[0-9A-F]{6}$", value)


def test_order_number_format() -> None:
    value = numbers.generate_order_number()
    assert value.startswith("ORD-")
