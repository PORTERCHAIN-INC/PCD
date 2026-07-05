"""Row lock helper tests (DD-08)."""

from unittest.mock import MagicMock

from porterchain_api.booking_engine.row_locks import (
    lock_active_payment,
    lock_order,
    lock_order_by_quote,
    lock_payment,
    lock_quote,
)


def _chain(mock_query: MagicMock) -> MagicMock:
    mock_query.filter.return_value = mock_query
    mock_query.order_by.return_value = mock_query
    mock_query.with_for_update.return_value = mock_query
    mock_query.first.return_value = None
    return mock_query


def test_lock_quote_uses_for_update() -> None:
    db = MagicMock()
    query = _chain(db.query.return_value)
    lock_quote(db, "quote-1")
    query.with_for_update.assert_called_once()


def test_lock_order_by_quote_uses_for_update() -> None:
    db = MagicMock()
    query = _chain(db.query.return_value)
    lock_order_by_quote(db, "quote-1")
    query.with_for_update.assert_called_once()


def test_lock_active_payment_orders_and_locks() -> None:
    db = MagicMock()
    query = _chain(db.query.return_value)
    lock_active_payment(db, "quote-1")
    query.order_by.assert_called_once()
    query.with_for_update.assert_called_once()


def test_lock_payment_and_order() -> None:
    db = MagicMock()
    query = _chain(db.query.return_value)
    lock_payment(db, "pay-1")
    lock_order(db, "ord-1")
    assert query.with_for_update.call_count == 2
