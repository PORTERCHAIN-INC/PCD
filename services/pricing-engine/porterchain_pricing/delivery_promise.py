"""Checkout delivery promise: cut-off times + wave schedule (+ FSA tier) -> date window.

Pure, no DB. The API stores the config in `system_config.delivery_promise`
(super-admin settings). Disabled or absent config -> `None`, and callers keep
their previous fixed window, so nothing changes until ops turn it on.

Model (all times local to `timezone`):

* `waves`: each wave has a `cutoff` (order by this time to make the wave) and a
  delivery window `start`..`end` on the same day.
* A wave is offered on an operating day that is not a holiday. Today: only
  waves whose cutoff has not passed. Later days: the first wave.
* `fsa_tiers`: destination FSA prefixes that cannot get same-day
  (`same_day: false`) and/or add `extra_days` to the promise.
"""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

SAME_DAY = "same_day"
NEXT_DAY = "next_day"
SCHEDULED = "scheduled"

#: EXAMPLE values awaiting an ops decision. The 11:00 -> 14:00-21:00 wave and Mon-Sat days
#: were approved by Ravi on 2026-10-09 ("Order by 11 AM. Delivered 2-9 PM same day, Mon-Sat").
PLACEHOLDER_PATHS: tuple[str, ...] = (
    "holidays",
    "fsa_tiers",
)

_DEFAULT: dict[str, Any] = {
    "schema": 1,
    "enabled": False,
    "timezone": "America/Toronto",
    # Order by 11:00 -> delivered 14:00-21:00 the same day; later -> next operating day.
    "waves": [{"code": "pm", "cutoff": "11:00", "start": "14:00", "end": "21:00"}],
    # Python weekday numbers: Monday=0 ... Sunday=6. Default Mon-Sat (Sunday off).
    "operating_weekdays": [0, 1, 2, 3, 4, 5],
    # ISO dates with no deliveries (e.g. statutory holidays).
    "holidays": [],
    # e.g. {"name": "outer", "prefixes": ["L9", "L0"], "same_day": false, "extra_days": 0}
    "fsa_tiers": [],
    # Never promise further out than this (safety net for a misconfigured calendar).
    "max_days_ahead": 14,
    "services": {
        SAME_DAY: {
            "name": "PorterChain Same Day",
            "code": "porterchain_same_day",
            "description": "Order by {cutoff} for delivery today {start}-{end}",
        },
        NEXT_DAY: {
            "name": "PorterChain Next Day",
            "code": "porterchain_next_day",
            "description": "Delivered tomorrow {start}-{end}",
        },
        SCHEDULED: {
            "name": "PorterChain Scheduled",
            "code": "porterchain_scheduled",
            "description": "Delivered {weekday} {start}-{end}",
        },
    },
}

_HHMM = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")
_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def default_delivery_promise() -> dict[str, Any]:
    return copy.deepcopy(_DEFAULT)


def _hhmm(value: Any, path: str) -> str:
    text = str(value or "").strip()
    if not _HHMM.match(text):
        raise ValueError(f"delivery_promise_invalid:{path}")
    return text


def _to_time(text: str) -> time:
    h, m = text.split(":")
    return time(int(h), int(m))


def normalize_delivery_promise(raw: Any) -> dict[str, Any]:
    """Validate and fill defaults. Raises ValueError('delivery_promise_invalid:<path>')."""
    out = default_delivery_promise()
    if raw is None:
        return out
    if not isinstance(raw, dict):
        raise ValueError("delivery_promise_invalid:root")
    if "enabled" in raw:
        out["enabled"] = bool(raw["enabled"])
    if raw.get("timezone"):
        tz = str(raw["timezone"])
        try:
            ZoneInfo(tz)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError("delivery_promise_invalid:timezone") from exc
        out["timezone"] = tz
    if "waves" in raw:
        waves = raw["waves"]
        if not isinstance(waves, list) or not waves or len(waves) > 8:
            raise ValueError("delivery_promise_invalid:waves")
        clean = []
        for i, w in enumerate(waves):
            if not isinstance(w, dict):
                raise ValueError(f"delivery_promise_invalid:waves.{i}")
            cutoff = _hhmm(w.get("cutoff"), f"waves.{i}.cutoff")
            start = _hhmm(w.get("start"), f"waves.{i}.start")
            end = _hhmm(w.get("end"), f"waves.{i}.end")
            if _to_time(end) <= _to_time(start):
                raise ValueError(f"delivery_promise_invalid:waves.{i}.end")
            code = re.sub(r"[^a-z0-9_]", "", str(w.get("code") or f"w{i + 1}").lower())[:16] or f"w{i + 1}"
            clean.append({"code": code, "cutoff": cutoff, "start": start, "end": end})
        out["waves"] = sorted(clean, key=lambda w: w["cutoff"])
    if "operating_weekdays" in raw:
        days = raw["operating_weekdays"]
        if not isinstance(days, list):
            raise ValueError("delivery_promise_invalid:operating_weekdays")
        try:
            clean_days = sorted({int(d) for d in days})
        except (TypeError, ValueError) as exc:
            raise ValueError("delivery_promise_invalid:operating_weekdays") from exc
        if not clean_days or any(d < 0 or d > 6 for d in clean_days):
            raise ValueError("delivery_promise_invalid:operating_weekdays")
        out["operating_weekdays"] = clean_days
    if "holidays" in raw:
        hols = raw["holidays"]
        if not isinstance(hols, list) or len(hols) > 100:
            raise ValueError("delivery_promise_invalid:holidays")
        clean_h = []
        for h in hols:
            text = str(h).strip()
            if not _ISO_DATE.match(text):
                raise ValueError("delivery_promise_invalid:holidays")
            try:
                date.fromisoformat(text)
            except ValueError as exc:
                raise ValueError("delivery_promise_invalid:holidays") from exc
            clean_h.append(text)
        out["holidays"] = sorted(set(clean_h))
    if "fsa_tiers" in raw:
        tiers = raw["fsa_tiers"]
        if not isinstance(tiers, list) or len(tiers) > 20:
            raise ValueError("delivery_promise_invalid:fsa_tiers")
        clean_t = []
        for i, t in enumerate(tiers):
            if not isinstance(t, dict):
                raise ValueError(f"delivery_promise_invalid:fsa_tiers.{i}")
            prefixes = t.get("prefixes")
            if not isinstance(prefixes, list):
                raise ValueError(f"delivery_promise_invalid:fsa_tiers.{i}.prefixes")
            clean_p = sorted(
                {re.sub(r"[^A-Z0-9]", "", str(p).upper())[:3] for p in prefixes} - {""}
            )
            try:
                extra = int(t.get("extra_days") or 0)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"delivery_promise_invalid:fsa_tiers.{i}.extra_days") from exc
            if extra < 0 or extra > 7:
                raise ValueError(f"delivery_promise_invalid:fsa_tiers.{i}.extra_days")
            clean_t.append(
                {
                    "name": str(t.get("name") or f"tier_{i + 1}")[:32],
                    "prefixes": clean_p,
                    "same_day": bool(t.get("same_day", True)),
                    "extra_days": extra,
                }
            )
        out["fsa_tiers"] = clean_t
    if "max_days_ahead" in raw:
        try:
            n = int(raw["max_days_ahead"])
        except (TypeError, ValueError) as exc:
            raise ValueError("delivery_promise_invalid:max_days_ahead") from exc
        if n < 1 or n > 31:
            raise ValueError("delivery_promise_invalid:max_days_ahead")
        out["max_days_ahead"] = n
    if isinstance(raw.get("services"), dict):
        for kind, svc in raw["services"].items():
            if kind not in out["services"] or not isinstance(svc, dict):
                continue
            for key in ("name", "description"):
                if svc.get(key):
                    out["services"][kind][key] = str(svc[key])[:120]
    return out


@dataclass(frozen=True)
class DeliveryPromise:
    kind: str  # same_day | next_day | scheduled
    service_name: str
    service_code: str
    description: str
    window_start: datetime
    window_end: datetime
    wave_code: str
    tier: str | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "service_name": self.service_name,
            "service_code": self.service_code,
            "description": self.description,
            "window_start": self.window_start.isoformat(),
            "window_end": self.window_end.isoformat(),
            "wave_code": self.wave_code,
            "tier": self.tier,
        }


def _tier_for(cfg: dict[str, Any], dest_fsa: str | None) -> dict[str, Any] | None:
    fsa = re.sub(r"[^A-Z0-9]", "", str(dest_fsa or "").upper())[:3]
    if not fsa:
        return None
    best: tuple[int, dict[str, Any]] | None = None
    for tier in cfg.get("fsa_tiers") or []:
        for prefix in tier.get("prefixes") or []:
            if fsa.startswith(prefix) and (best is None or len(prefix) > best[0]):
                best = (len(prefix), tier)
    return best[1] if best else None


def _fmt_time(t: str) -> str:
    h, m = (int(x) for x in t.split(":"))
    suffix = "am" if h < 12 else "pm"
    h12 = h % 12 or 12
    return f"{h12}{suffix}" if m == 0 else f"{h12}:{m:02d}{suffix}"


def compute_delivery_promise(
    config: Any,
    *,
    now: datetime,
    dest_fsa: str | None = None,
) -> DeliveryPromise | None:
    """Earliest wave this order can make. None when disabled (caller keeps old behaviour)."""
    if not isinstance(config, dict) or not config.get("enabled"):
        return None
    cfg = normalize_delivery_promise(config)
    tz = ZoneInfo(cfg["timezone"])
    local_now = now.astimezone(tz) if now.tzinfo else now.replace(tzinfo=tz)
    today = local_now.date()
    tier = _tier_for(cfg, dest_fsa)
    same_day_ok = tier is None or tier.get("same_day", True)
    extra_days = int((tier or {}).get("extra_days") or 0)
    holidays = set(cfg["holidays"])
    weekdays = set(cfg["operating_weekdays"])
    waves = cfg["waves"]

    def _operating(d: date) -> bool:
        return d.weekday() in weekdays and d.isoformat() not in holidays

    chosen: tuple[date, dict[str, Any]] | None = None
    for offset in range(cfg["max_days_ahead"] + 1):
        day = today + timedelta(days=offset)
        if not _operating(day):
            continue
        if offset == 0:
            if not same_day_ok:
                continue
            open_waves = [w for w in waves if local_now.time() <= _to_time(w["cutoff"])]
            if open_waves:
                chosen = (day, open_waves[0])
                break
            continue
        chosen = (day, waves[0])
        break
    if chosen is None:
        return None
    day, wave = chosen
    # FSA tier extra days move the promise to later operating days.
    remaining = extra_days
    guard = 0
    while remaining > 0 and guard < 31:
        guard += 1
        day = day + timedelta(days=1)
        if _operating(day):
            remaining -= 1
    delta = (day - today).days
    kind = SAME_DAY if delta == 0 else NEXT_DAY if delta == 1 else SCHEDULED
    svc = cfg["services"][kind]
    start = datetime.combine(day, _to_time(wave["start"]), tzinfo=tz)
    end = datetime.combine(day, _to_time(wave["end"]), tzinfo=tz)
    description = svc["description"].format(
        cutoff=_fmt_time(wave["cutoff"]),
        start=_fmt_time(wave["start"]),
        end=_fmt_time(wave["end"]),
        weekday=day.strftime("%A"),
        date=day.isoformat(),
    )
    return DeliveryPromise(
        kind=kind,
        service_name=svc["name"],
        service_code=svc["code"],
        description=description,
        window_start=start,
        window_end=end,
        wave_code=wave["code"],
        tier=(tier or {}).get("name"),
    )


def available_windows(
    config: Any,
    *,
    now: datetime,
    days: int = 7,
    dest_fsa: str | None = None,
) -> list[dict[str, Any]]:
    """Every wave a delivery recipient may pick over the next ``days`` operating days.

    Used by recipient self-scheduling. It reads the same calendar as the checkout
    promise (waves, weekdays, holidays, FSA tiers) but ignores ``enabled``: the
    self-service toggle is per merchant, so a disabled checkout promise still
    yields the (placeholder) default waves.
    """
    cfg = normalize_delivery_promise(config if isinstance(config, dict) else None)
    tz = ZoneInfo(cfg["timezone"])
    local_now = now.astimezone(tz) if now.tzinfo else now.replace(tzinfo=tz)
    today = local_now.date()
    tier = _tier_for(cfg, dest_fsa)
    same_day_ok = tier is None or tier.get("same_day", True)
    extra_days = int((tier or {}).get("extra_days") or 0)
    holidays = set(cfg["holidays"])
    weekdays = set(cfg["operating_weekdays"])

    def _operating(d: date) -> bool:
        return d.weekday() in weekdays and d.isoformat() not in holidays

    # Earliest day: FSA extra days push the first offered operating day out.
    earliest = today + timedelta(days=1) if not same_day_ok else today
    remaining = extra_days
    guard = 0
    while remaining > 0 and guard < 31:
        guard += 1
        earliest = earliest + timedelta(days=1)
        if _operating(earliest):
            remaining -= 1

    want = max(1, min(int(days or 1), 21))
    out: list[dict[str, Any]] = []
    seen_days = 0
    for offset in range(cfg["max_days_ahead"] + want + 1):
        day = today + timedelta(days=offset)
        if day < earliest or not _operating(day):
            continue
        waves = cfg["waves"]
        if day == today:
            waves = [w for w in waves if local_now.time() <= _to_time(w["cutoff"])]
        if not waves:
            continue
        for wave in waves:
            start = datetime.combine(day, _to_time(wave["start"]), tzinfo=tz)
            end = datetime.combine(day, _to_time(wave["end"]), tzinfo=tz)
            out.append(
                {
                    "code": f"{day.isoformat()}:{wave['code']}",
                    "date": day.isoformat(),
                    "wave_code": wave["code"],
                    "window_start": start.isoformat(),
                    "window_end": end.isoformat(),
                    "label": f"{day.strftime('%a %b')} {day.day}, {_fmt_time(wave['start'])}-{_fmt_time(wave['end'])}",
                }
            )
        seen_days += 1
        if seen_days >= want:
            break
    return out
