from datetime import UTC, datetime

from porterchain_pricing.delivery_promise import available_windows

# Friday 2026-10-09
MORNING = datetime(2026, 10, 9, 13, 0, tzinfo=UTC)  # 09:00 Toronto
EVENING = datetime(2026, 10, 9, 23, 0, tzinfo=UTC)  # 19:00 Toronto

CFG = {
    "enabled": False,  # self-scheduling ignores the checkout toggle
    "waves": [
        {"code": "am", "cutoff": "07:00", "start": "09:00", "end": "13:00"},
        {"code": "pm", "cutoff": "11:00", "start": "14:00", "end": "21:00"},
    ],
    "operating_weekdays": [0, 1, 2, 3, 4, 5],
    "holidays": ["2026-10-12"],
}


def test_default_placeholder_waves_when_unset() -> None:
    out = available_windows(None, now=MORNING, days=2)
    assert [w["code"] for w in out] == ["2026-10-09:pm", "2026-10-10:pm"]
    assert out[0]["label"] == "Fri Oct 9, 2pm-9pm"


def test_today_only_open_waves_and_skips_sunday_and_holiday() -> None:
    out = available_windows(CFG, now=MORNING, days=3)
    assert [w["code"] for w in out] == [
        "2026-10-09:pm",
        "2026-10-10:am",
        "2026-10-10:pm",
        "2026-10-13:am",
        "2026-10-13:pm",
    ]
    late = available_windows(CFG, now=EVENING, days=1)
    assert [w["date"] for w in late] == ["2026-10-10", "2026-10-10"]


def test_fsa_tier_without_same_day_and_extra_days() -> None:
    cfg = {**CFG, "fsa_tiers": [{"name": "outer", "prefixes": ["L9"], "same_day": False, "extra_days": 1}]}
    out = available_windows(cfg, now=MORNING, days=1, dest_fsa="L9T")
    # Not today; next operating day is Sat 10th, +1 operating day (Sun off, Mon holiday) -> Tue 13th.
    assert {w["date"] for w in out} == {"2026-10-13"}


def test_days_is_clamped() -> None:
    assert len({w["date"] for w in available_windows(None, now=MORNING, days=99)}) == 21
