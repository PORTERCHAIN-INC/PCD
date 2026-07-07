"""Order metadata helper tests."""

from porterchain_api.booking_engine.order_metadata import (
    resolve_executor_type,
    resolve_order_type,
    retail_order_source,
)
from porterchain_api.domain.states import OrderSource, OrderType


def test_retail_order_source() -> None:
    assert retail_order_source() == OrderSource.WEBSITE.value


def test_resolve_order_type_express() -> None:
    assert resolve_order_type(schedule_mode="now", is_rush=True) == OrderType.EXPRESS.value


def test_resolve_executor_type_default() -> None:
    assert resolve_executor_type(None) == "human_driver"
