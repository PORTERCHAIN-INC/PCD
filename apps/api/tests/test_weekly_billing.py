"""Ravi 2026-10-31: weekly billing. Mon-Sun Toronto week, invoiced Wednesday, due next Wednesday."""
from datetime import UTC, datetime
from types import SimpleNamespace

from porterchain_api.admin_engine.merchant_ar_cycles import is_weekly_billed_merchant
from porterchain_api.billing_engine import weekly_billing as wb
from porterchain_api.billing_engine.merchant_service import invoice_status


def test_week_is_monday_to_sunday_toronto() -> None:
    # Sat Oct 31 2026 9 AM Toronto -> week Mon Oct 26 00:00 EDT .. Mon Nov 2 00:00 EST
    start, end = wb.week_bounds(datetime(2026, 10, 31, 13, 0, tzinfo=UTC))
    assert start == datetime(2026, 10, 26, 4, 0) and end == datetime(2026, 11, 2, 5, 0)


def test_sunday_evening_toronto_is_still_that_week() -> None:
    start, end = wb.week_bounds(datetime(2026, 10, 26, 3, 0, tzinfo=UTC))  # Sun Oct 25 11 PM Toronto
    assert start == datetime(2026, 10, 19, 4, 0) and end == datetime(2026, 10, 26, 4, 0)


def test_previous_week_and_invoice_day() -> None:
    wed = datetime(2026, 11, 4, 14, 0, tzinfo=UTC)  # Wed Nov 4
    assert wb.previous_week_bounds(wed) == (datetime(2026, 10, 26, 4, 0), datetime(2026, 11, 2, 5, 0))
    assert wb.invoice_day_reached(wed)
    assert not wb.invoice_day_reached(datetime(2026, 11, 3, 14, 0, tzinfo=UTC))  # Tuesday waits


def test_due_is_the_following_wednesday_end_of_day() -> None:
    assert wb.due_at_for_issue(datetime(2026, 11, 4, 14, 0, tzinfo=UTC)) == datetime(2026, 11, 12, 4, 59, 59)
    # A Saturday manual invoice is due the next Wednesday.
    assert wb.due_at_for_issue(datetime(2026, 10, 31, 2, 39)) == datetime(2026, 11, 5, 4, 59, 59)


def test_merchant_invoice_not_overdue_before_wednesday() -> None:
    inv = SimpleNamespace(merchant_id="m1", created_at=datetime(2026, 10, 31, 2, 39), due_at=None,
                          amount_cents=1831, amount_paid_cents=0, tax_cents=0, fees_cents=0,
                          credit_notes=[], lines=[], voided_at=None)
    assert invoice_status(inv, None, None, terms="IMMEDIATE", now=datetime(2026, 10, 31, 3, 0)) != "overdue"
    assert invoice_status(inv, None, None, terms="IMMEDIATE", now=datetime(2026, 11, 5, 6, 0)) == "overdue"


def test_everyone_weekly_except_prepaid() -> None:
    assert is_weekly_billed_merchant(SimpleNamespace(payment_terms="IMMEDIATE"))
    assert is_weekly_billed_merchant(SimpleNamespace(payment_terms="NET_30"))
    assert not is_weekly_billed_merchant(SimpleNamespace(payment_terms="PREPAID"))


def test_email_terms_line() -> None:
    line = wb.terms_line(datetime(2026, 10, 26, 4), datetime(2026, 11, 2, 5), datetime(2026, 11, 12, 4, 59, 59))
    assert "Oct 26 - Nov 01, 2026" in line and "Wed Nov 11, 2026" in line and "20%" in line
