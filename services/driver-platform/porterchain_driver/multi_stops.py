"""Every stop of a multi-stop order (hub & spoke 1->N, multi pickup/drop N->N) for the driver.

One order carries its whole stop plan (``booking_engine.stop_sync.stop_plan``). The driver
sees and works each stop in plan order straight from the order -- no committed dispatch
route needed.

Stop ids stay backward compatible: the first pickup is ``{order}-pickup`` and the final drop
is ``{order}-dropoff`` (both drive the order state machine exactly as before). Stops in
between are ``{order}-pickup.{key}`` / ``{order}-dropoff.{key}``; their progress is kept per
stop in ``DriverStopMeta.meta["stops"][key]`` and never moves the order past IN_TRANSIT.

Rules (strict plan order inside one order):
* only the first open stop is actionable; later open stops are ``locked``;
* a middle drop needs the pickup done; arriving at (or starting) the first drop moves the
  order to IN_TRANSIT, so the receiver's live tracking starts exactly as on a single job;
* each middle drop needs its own photo or signature (tagged with the stop key) when POD is
  enforced; the final drop keeps the order-level POD rules and is ``earlier_stops_open``
  until every middle stop is done.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from porterchain_driver.types import StopView

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

_KEY_RE = re.compile(r"[^A-Za-z0-9_]+")
_DONE_PICKUP = {"picked_up"}
_DONE_DROP = {"delivered", "pod_completed", "completed"}


@dataclass
class PlanStop:
    key: str
    leg: str  # pickup | dropoff
    role: str  # first_pickup | final_drop | mid
    blob: dict[str, Any]
    index: int
    total: int

    def stop_id(self, order_id: str) -> str:
        if self.role == "first_pickup":
            return f"{order_id}-pickup"
        if self.role == "final_drop":
            return f"{order_id}-dropoff"
        return f"{order_id}-{self.leg}.{self.key}"


def split_stop_id(stop_id: str) -> tuple[str, str, str | None]:
    """``"o1-dropoff.s2"`` -> ``("o1", "dropoff", "s2")``; plain ids give key ``None``."""
    order_id, _, tail = stop_id.rpartition("-")
    leg, _, key = tail.partition(".")
    return order_id, leg, (key or None)


def is_mid_stop_id(stop_id: str) -> bool:
    return split_stop_id(stop_id)[2] is not None


def plan_for(order: Any) -> list[PlanStop] | None:
    """Ordered stops for a multi-stop order; ``None`` for a plain pickup -> drop order."""
    from porterchain_api.booking_engine.stop_sync import stop_plan

    try:
        rows = stop_plan(order)
    except Exception:  # noqa: BLE001 -- odd metadata must never break the driver app
        return None
    if len(rows) <= 2:
        return None
    total = len(rows)
    kinds = [kind for _, kind, _ in rows]
    first_pickup = kinds.index("pickup") if "pickup" in kinds else 0
    drops = [i for i, k in enumerate(kinds) if k != "pickup" and i != first_pickup]
    final_drop = drops[-1] if drops else total - 1
    out: list[PlanStop] = []
    used: set[str] = set()
    for i, (seq, kind, blob) in enumerate(rows):
        raw = str((blob or {}).get("id") or "") if isinstance(blob, dict) else ""
        key = _KEY_RE.sub("_", raw).strip("_")[:40] or f"s{seq}"
        if key in used:
            key = f"{key}_{i}"
        used.add(key)
        role = "first_pickup" if i == first_pickup else "final_drop" if i == final_drop else "mid"
        leg = "pickup" if kind == "pickup" else "dropoff"
        out.append(PlanStop(key, leg, role, dict(blob) if isinstance(blob, dict) else {}, i, total))
    return out


def _meta(db: Any, order_id: str) -> dict[str, Any]:
    from porterchain_api.driver_models import DriverStopMeta

    row = db.query(DriverStopMeta).filter(DriverStopMeta.order_id == order_id).first()
    return dict(row.meta or {}) if row else {}


def _progress(db: Any, order_id: str) -> dict[str, dict[str, Any]]:
    stops = _meta(db, order_id).get("stops")
    return {str(k): dict(v) for k, v in stops.items() if isinstance(v, dict)} if isinstance(stops, dict) else {}


def _address(blob: dict[str, Any], fallback: Any) -> dict[str, Any]:
    addr = {k: v for k, v in blob.items() if k not in {"id", "type", "kind", "sequence"}}
    if not addr.get("formatted"):
        addr["formatted"] = blob.get("formatted_address") or blob.get("address") or ""
    if not addr.get("formatted") and isinstance(fallback, dict):
        return dict(fallback)
    return addr


def _done(stop: PlanStop, state: str, progress: dict[str, dict[str, Any]]) -> bool:
    from porterchain_driver.job_legs import stop_status_for_leg

    if stop.role == "mid":
        return bool(progress.get(stop.key, {}).get("completed_at"))
    status = stop_status_for_leg(state, stop.leg)
    return status in (_DONE_PICKUP if stop.leg == "pickup" else _DONE_DROP)


def stop_views(db: Any, order: Any, *, sequence_start: int = 0) -> list[StopView] | None:
    """All stops of a multi-stop order in plan order with per-stop status; ``None`` if single."""
    from porterchain_driver.job_legs import stop_status_for_leg

    plan = plan_for(order)
    if plan is None:
        return None
    state = str(order.state)
    progress = _progress(db, str(order.id))
    pickup_done = stop_status_for_leg(state, "pickup") in _DONE_PICKUP
    views: list[StopView] = []
    current_found = False
    for i, stop in enumerate(plan):
        if _done(stop, state, progress):
            status = "picked_up" if stop.leg == "pickup" else "delivered"
        elif current_found:
            status = "locked"
        else:
            current_found = True
            if stop.role != "mid":
                status = stop_status_for_leg(state, stop.leg)
            elif not pickup_done:
                status = "locked"
            else:
                status = "arrived" if progress.get(stop.key, {}).get("arrived_at") else "pending"
        fallback = order.pickup if stop.role == "first_pickup" else order.dropoff if stop.role == "final_drop" else None
        label = (stop.blob.get("label") or stop.blob.get("name") or stop.blob.get("contact_name") or "")
        note = stop.blob.get("notes") or stop.blob.get("instructions")
        is_drop = stop.leg == "dropoff"
        views.append(
            StopView(
                stop_id=stop.stop_id(str(order.id)), order_id=str(order.id),
                sequence=sequence_start + i, stop_type=stop.leg, status=status,
                address=_address(stop.blob, fallback), scheduled_at=order.scheduled_at,
                tracking_number=order.tracking_number,
                order_number=order.order_number or order.tracking_number,
                special_instructions=str(note) if note else order.special_instructions,
                otp_required=is_drop and stop.role == "final_drop", pod_required=is_drop,
                stop_key=stop.key, stop_index=i + 1, stop_total=len(plan),
                stop_label=str(label) if label else None,
            )
        )
    return views


def leg_groups(db: Any, order: Any, *, sequence_start: int = 0) -> tuple[list[StopView], list[StopView]] | None:
    """(stops before the first drop, the rest) so a day plan's pickup/dropoff waypoints expand."""
    views = stop_views(db, order, sequence_start=sequence_start)
    if views is None:
        return None
    cut = next((i for i, v in enumerate(views) if v.stop_type == "dropoff"), len(views))
    return views[:cut], views[cut:]


def _find(views: list[StopView], stop_id: str) -> StopView:
    for v in views:
        if v.stop_id == stop_id:
            return v
    raise LookupError("stop_not_found")


def assert_final_drop_ready(db: Any, order: Any) -> None:
    """The final drop waits for every earlier stop (raises ``earlier_stops_open``)."""
    views = stop_views(db, order)
    if not views:
        return
    if any(is_mid_stop_id(v.stop_id) and v.status not in ("picked_up", "delivered") for v in views):
        raise ValueError("earlier_stops_open")


def _actionable(db: Any, order: Any, stop_id: str) -> StopView:
    views = stop_views(db, order)
    if views is None:
        raise LookupError("stop_not_found")
    view = _find(views, stop_id)
    if view.status in ("picked_up", "delivered"):
        raise ValueError("stop_already_completed")
    if view.status == "locked":
        from porterchain_driver.job_legs import stop_status_for_leg

        if stop_status_for_leg(str(order.state), "pickup") not in _DONE_PICKUP:
            raise ValueError("pickup_required")
        raise ValueError("earlier_stops_open")
    return view


def _save(db: Any, order: Any, driver_id: str, key: str, field: str) -> None:
    from porterchain_api.driver_models import DriverStopMeta

    row = db.query(DriverStopMeta).filter(DriverStopMeta.order_id == order.id).first()
    meta = dict(row.meta or {}) if row else {}
    stops = dict(meta.get("stops") or {})
    entry = dict(stops.get(key) or {})
    entry.setdefault(field, datetime.now(UTC).isoformat())
    entry["driver_id"] = driver_id
    stops[key] = entry
    meta["stops"] = stops
    if row:
        row.meta = meta
    else:
        db.add(DriverStopMeta(order_id=order.id, driver_id=driver_id, meta=meta))
    db.flush()


def _start_delivery_chain(db: Any, order: Any, driver_id: str) -> None:
    if str(order.state).upper() != "PICKED_UP":
        return
    from porterchain_driver.stops import _START_DELIVERY_STEPS, _apply_state_chain

    _apply_state_chain(db, order, _START_DELIVERY_STEPS, actor_type="driver", actor_id=driver_id)


def _refresh(db: Any, order: Any, stop_id: str) -> StopView:
    return _find(stop_views(db, order) or [], stop_id)


def arrive(db: "Session", driver: Any, order: Any, stop_id: str, *, skip_presence: bool = False) -> StopView:
    view = _actionable(db, order, stop_id)
    if not skip_presence:
        from porterchain_driver.navigation import assert_driver_inside_point

        assert_driver_inside_point(driver.id, view.address.get("lat"), view.address.get("lng"))
    if view.stop_type == "dropoff":
        _start_delivery_chain(db, order, driver.id)  # receiver tracking starts at the first drop
    _save(db, order, driver.id, view.stop_key or "", "arrived_at")
    return _refresh(db, order, stop_id)


def start_delivery(db: "Session", driver: Any, order: Any, stop_id: str) -> StopView:
    view = _actionable(db, order, stop_id)
    if view.stop_type != "dropoff":
        raise ValueError("not_a_delivery_stop")
    _start_delivery_chain(db, order, driver.id)
    return _refresh(db, order, stop_id)


def deliver(db: "Session", driver: Any, order: Any, stop_id: str, *, pod_override: bool = False,
            duty_override: bool = False) -> StopView:
    view = _actionable(db, order, stop_id)
    key = view.stop_key or ""
    if view.stop_type == "dropoff":
        if not duty_override:
            from porterchain_driver.pod_policy import assert_on_duty

            assert_on_duty(db, driver)
        from porterchain_driver.stops import _pod_enforced

        if _pod_enforced() and not pod_override and not _has_stop_proof(db, order.id, key):
            from porterchain_driver.pod_policy import PodMissing

            raise PodMissing(["photo_or_signature"])
        _start_delivery_chain(db, order, driver.id)
    _save(db, order, driver.id, key, "arrived_at")
    _save(db, order, driver.id, key, "completed_at")
    return _refresh(db, order, stop_id)


def _has_stop_proof(db: Any, order_id: str, key: str) -> bool:
    proofs = _meta(db, order_id).get("proofs") or []
    return any(
        isinstance(p, dict) and p.get("stop_key") == key and p.get("type") in ("photo", "signature")
        for p in proofs
    )
