"""Learned stop times: median seconds on site per exact place, then FSA, per pickup/drop.

Learned nightly from driver check-ins (``arrived`` → ``picked_up``/``delivered`` on the
same plan stop). Lookups fall back place → FSA → the fleet default (minutes per stop).
"""

from __future__ import annotations

import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

MIN_S, MAX_S = 30, 3600  # ignore taps in a row and forgotten check-ins
MIN_SAMPLES = 3
WINDOW_DAYS = 60


def kind_of(stop_kind: str) -> str:
    return "pickup" if stop_kind in {"pickup", "return_pickup"} else "drop"


def place_key(lat: float | None, lng: float | None) -> str | None:
    """~10 m grid cell; an address-level key that carries no name or street."""
    if lat is None or lng is None:
        return None
    return f"{float(lat):.4f},{float(lng):.4f}"


def durations(rows: list[tuple[str, str, str, datetime]]) -> dict[tuple[str, str], int]:
    """``(route_id, stop_key, event, at)`` → seconds on site per (route_id, stop_key)."""
    arrived: dict[tuple[str, str], datetime] = {}
    done: dict[tuple[str, str], datetime] = {}
    for route_id, key, event, at in rows:
        k = (route_id, key)
        if event == "arrived":
            arrived[k] = min(at, arrived.get(k, at))
        elif event in {"picked_up", "delivered"}:
            done[k] = max(at, done.get(k, at))
    out: dict[tuple[str, str], int] = {}
    for k, a in arrived.items():
        if k in done:
            s = int((done[k] - a).total_seconds())
            if MIN_S <= s <= MAX_S:
                out[k] = s
    return out


def learn(db: Session, *, now: datetime | None = None) -> dict[str, int]:
    """Nightly: recompute medians from the last ``WINDOW_DAYS`` of check-ins (upsert)."""
    from porterchain_api.dispatch_engine.models import DispatchRoute, DispatchStopEvent, DispatchStopTime

    now = now or datetime.now(UTC)
    rows = (
        db.query(DispatchStopEvent.route_id, DispatchStopEvent.stop_key, DispatchStopEvent.event, DispatchStopEvent.at)
        .filter(DispatchStopEvent.at >= now - timedelta(days=WINDOW_DAYS), DispatchStopEvent.route_id.isnot(None))
        .all()
    )
    secs = durations([(r[0], r[1], r[2], r[3]) for r in rows])
    stops: dict[tuple[str, str], dict[str, Any]] = {}
    for route in db.query(DispatchRoute).filter(DispatchRoute.id.in_({r for r, _ in secs})).all():
        for s in route.stops or []:
            stops[(route.id, s["key"])] = s
    samples: dict[tuple[str, str, str], list[int]] = defaultdict(list)
    for k, s in secs.items():
        stop = stops.get(k)
        if not stop:
            continue
        kind = kind_of(stop.get("kind", "drop"))
        if stop.get("fsa"):
            samples[("fsa", stop["fsa"], kind)].append(s)
        if stop.get("place"):
            samples[("place", stop["place"], kind)].append(s)
    existing = {(r.scope, r.scope_key, r.kind): r for r in db.query(DispatchStopTime).all()}
    written = 0
    for key, vals in samples.items():
        if len(vals) < MIN_SAMPLES:
            continue
        row = existing.get(key) or DispatchStopTime(scope=key[0], scope_key=key[1], kind=key[2])
        row.median_s, row.samples, row.updated_at = int(statistics.median(vals)), len(vals), now
        db.add(row)
        written += 1
    db.commit()
    return {"stops_measured": len(secs), "keys_written": written}


@dataclass
class StopTimes:
    """In-memory lookup for one plan or ETA pass."""

    default_s: int
    table: dict[tuple[str, str, str], int] = field(default_factory=dict)

    def seconds(self, stop_kind: str, *, fsa: str | None = None, place: str | None = None) -> int:
        kind = kind_of(stop_kind)
        for scope, key in (("place", place), ("fsa", fsa)):
            if key and (scope, key, kind) in self.table:
                return self.table[(scope, key, kind)]
        return self.default_s

    def source(self, stop_kind: str, *, fsa: str | None = None, place: str | None = None) -> str:
        kind = kind_of(stop_kind)
        for scope, key in (("place", place), ("fsa", fsa)):
            if key and (scope, key, kind) in self.table:
                return scope
        return "default"


def load(db: Session, default_s: int) -> StopTimes:
    from porterchain_api.dispatch_engine.models import DispatchStopTime

    rows = db.query(DispatchStopTime).all()
    return StopTimes(default_s=int(default_s), table={(r.scope, r.scope_key, r.kind): int(r.median_s) for r in rows})
