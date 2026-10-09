from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from porterchain_pricing.delivery_promise import (
    NEXT_DAY,
    SAME_DAY,
    SCHEDULED,
    compute_delivery_promise,
    default_delivery_promise,
    normalize_delivery_promise,
)

TZ = ZoneInfo("America/Toronto")


def _cfg(**over):
    cfg = default_delivery_promise()
    cfg["enabled"] = True
    cfg.update(over)
    return cfg


def _at(y, m, d, hh, mm=0):
    return datetime(y, m, d, hh, mm, tzinfo=TZ)


def test_disabled_or_missing_returns_none_so_caller_keeps_old_window():
    assert compute_delivery_promise(None, now=_at(2026, 10, 7, 9)) is None
    assert compute_delivery_promise(default_delivery_promise(), now=_at(2026, 10, 7, 9)) is None


def test_before_cutoff_is_same_day_wave():
    p = compute_delivery_promise(_cfg(), now=_at(2026, 10, 7, 10, 59))  # Wednesday
    assert p.kind == SAME_DAY
    assert p.service_name == "PorterChain Same Day"
    assert p.window_start == _at(2026, 10, 7, 14)
    assert p.window_end == _at(2026, 10, 7, 21)
    assert "11am" in p.description


def test_after_cutoff_rolls_to_next_operating_day():
    p = compute_delivery_promise(_cfg(), now=_at(2026, 10, 7, 11, 1))
    assert p.kind == NEXT_DAY
    assert p.service_code == "porterchain_next_day"
    assert p.window_start == _at(2026, 10, 8, 14)


def test_saturday_after_cutoff_skips_sunday():
    p = compute_delivery_promise(_cfg(), now=_at(2026, 10, 10, 15))  # Saturday
    assert p.kind == SCHEDULED
    assert p.window_start.date().isoformat() == "2026-10-12"  # Monday
    assert "Monday" in p.description


def test_holiday_is_skipped():
    p = compute_delivery_promise(
        _cfg(holidays=["2026-10-12"]), now=_at(2026, 10, 10, 15)
    )
    assert p.window_start.date().isoformat() == "2026-10-13"


def test_second_wave_catches_late_morning_orders():
    waves = [
        {"code": "am", "cutoff": "08:00", "start": "10:00", "end": "14:00"},
        {"code": "pm", "cutoff": "13:00", "start": "16:00", "end": "21:00"},
    ]
    p = compute_delivery_promise(_cfg(waves=waves), now=_at(2026, 10, 7, 9))
    assert p.kind == SAME_DAY and p.wave_code == "pm"


def test_fsa_tier_blocks_same_day_and_adds_days():
    tiers = [{"name": "outer", "prefixes": ["L9"], "same_day": False, "extra_days": 0}]
    p = compute_delivery_promise(_cfg(fsa_tiers=tiers), now=_at(2026, 10, 7, 9), dest_fsa="L9T")
    assert p.kind == NEXT_DAY and p.tier == "outer"
    core = compute_delivery_promise(_cfg(fsa_tiers=tiers), now=_at(2026, 10, 7, 9), dest_fsa="M5V")
    assert core.kind == SAME_DAY and core.tier is None
    tiers2 = [{"name": "far", "prefixes": ["K"], "same_day": True, "extra_days": 2}]
    far = compute_delivery_promise(_cfg(fsa_tiers=tiers2), now=_at(2026, 10, 7, 9), dest_fsa="K1A")
    assert far.window_start.date().isoformat() == "2026-10-09"


def test_validation_rejects_bad_config():
    with pytest.raises(ValueError, match="waves.0.cutoff"):
        normalize_delivery_promise({"waves": [{"cutoff": "25:00", "start": "10:00", "end": "11:00"}]})
    with pytest.raises(ValueError, match="waves.0.end"):
        normalize_delivery_promise({"waves": [{"cutoff": "09:00", "start": "12:00", "end": "11:00"}]})
    with pytest.raises(ValueError, match="holidays"):
        normalize_delivery_promise({"holidays": ["2026-13-01"]})
    with pytest.raises(ValueError, match="operating_weekdays"):
        normalize_delivery_promise({"operating_weekdays": [7]})
    with pytest.raises(ValueError, match="timezone"):
        normalize_delivery_promise({"timezone": "Mars/Base"})


def test_no_operating_day_in_range_returns_none():
    assert compute_delivery_promise(
        _cfg(operating_weekdays=[6], max_days_ahead=1), now=_at(2026, 10, 7, 9)
    ) is None
