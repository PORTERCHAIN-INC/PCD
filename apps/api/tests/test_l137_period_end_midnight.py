from datetime import datetime

from porterchain_api.admin_engine.merchant_ar_service import _end_of_day, _toronto_wall_to_utc


def test_picker_2330_rounds_to_toronto_midnight():
    assert _end_of_day(datetime(2026, 10, 25, 23, 30)) == datetime(2026, 10, 26, 0, 0)
    assert _end_of_day(datetime(2026, 10, 25, 23, 59, 59)) == datetime(2026, 10, 26, 0, 0)
    # EDT: Toronto midnight = 04:00 UTC
    assert _toronto_wall_to_utc(_end_of_day(datetime(2026, 10, 25, 23, 30))) == datetime(2026, 10, 26, 4, 0)


def test_explicit_daytime_end_is_kept():
    assert _end_of_day(datetime(2026, 10, 25, 17, 0)) == datetime(2026, 10, 25, 17, 0)
