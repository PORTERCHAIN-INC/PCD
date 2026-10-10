"""Driver's committed route + stop-level check-ins (arrived / picked_up / delivered / failed).

Check-ins are stored per plan stop key with GPS, move the order through the normal
state machine (walking intermediate states), refresh the driver's live position (ETA),
and feed re-planning (finished stop keys) and learned stop times.

Offline apps queue actions with a ``client_id``; replaying one is a no-op. Picked up /
delivered need every box scanned (``scan_gate``) unless the driver reports a short drop,
which opens a ``package_short_at_drop`` exception (the missing-item alert).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Callable

from sqlalchemy.orm import Session

PICKUP_KINDS = {"pickup", "return_pickup"}
DROP_KINDS = {"drop", "return_drop", "hub", "handoff"}
EVENTS = ("arrived", "picked_up", "delivered", "failed")
DONE_EVENTS = {"picked_up", "delivered"}
CHAIN = ["DRIVER_ASSIGNED", "DRIVER_ACCEPTED", "DRIVER_EN_ROUTE", "AT_PICKUP", "PICKED_UP",
         "IN_TRANSIT", "AT_DESTINATION", "DELIVERED"]
POD_KINDS = {"drop", "return_drop"}
#: ``(order, "pickup" | "delivery") -> {"complete", "missing_suffixes", "scanned", "required"}``
ScanGate = Callable[[Any, str], dict[str, Any]]


def place(key: str) -> str:
    parts = key.split(":")
    return parts[1] if len(parts) > 2 else key


def group(stops: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One physical stop per run of same order + kind + place (split pairs merge)."""
    out: list[dict[str, Any]] = []
    for s in stops:
        last = out[-1] if out else None
        if last and last["order_id"] == s["order_id"] and last["kind"] == s["kind"] and place(last["keys"][-1]) == place(s["key"]):
            last["keys"].append(s["key"])
            last["eta_s"] = s.get("eta_s", last["eta_s"])
        else:
            out.append({"keys": [s["key"]], "order_id": s["order_id"], "kind": s["kind"],
                        "fsa": s.get("fsa"), "eta_s": s.get("eta_s", 0), **({"meet": s["meet"]} if s.get("meet") else {})})
    return out


def stop_status(kind: str, events: set[str]) -> str:
    if "failed" in events:
        return "failed"
    final = "picked_up" if kind in PICKUP_KINDS else "delivered"
    if final in events:
        return "done"
    return "arrived" if "arrived" in events else "pending"


def allowed(kind: str, event: str, status: str) -> bool:
    if event not in EVENTS or status in {"done", "failed"}:
        return False
    if event == "failed" or event == "arrived":
        return event != "arrived" or status == "pending"
    return event == ("picked_up" if kind in PICKUP_KINDS else "delivered")


def walk_to(db: Session, order: Any, target: str, *, driver_id: str, payload: dict[str, Any]) -> list[str]:
    """Advance ``order`` one legal step at a time until it reaches ``target``."""
    from porterchain_api.booking_engine.order_transitions import transition_order_state
    from porterchain_api.domain.states import OrderState

    moved: list[str] = []
    if order.state not in CHAIN or target not in CHAIN:
        return moved
    while CHAIN.index(order.state) < CHAIN.index(target):
        nxt = CHAIN[CHAIN.index(order.state) + 1]
        order = transition_order_state(db, order, OrderState(nxt), event_type=f"order.{nxt.lower()}",
                                       actor_type="driver", actor_id=driver_id, payload=payload)
        moved.append(nxt)
    return moved


class DriverRouteService:
    def current_route(self, db: Session, driver_id: str) -> Any | None:
        from porterchain_api.dispatch_engine.models import DispatchPlan, DispatchRoute

        return (
            db.query(DispatchRoute)
            .join(DispatchPlan, DispatchPlan.id == DispatchRoute.plan_id)
            .filter(DispatchRoute.driver_id == driver_id, DispatchPlan.status == "committed")
            .order_by(DispatchPlan.committed_at.desc())
            .first()
        )

    def _events(self, db: Session, route_id: str) -> dict[str, set[str]]:
        from porterchain_api.dispatch_engine.models import DispatchStopEvent

        out: dict[str, set[str]] = {}
        for key, ev in db.query(DispatchStopEvent.stop_key, DispatchStopEvent.event).filter(
            DispatchStopEvent.route_id == route_id
        ):
            out.setdefault(key, set()).add(ev)
        return out

    def view(self, db: Session, driver_id: str) -> dict[str, Any]:
        from porterchain_api.booking_models import Order
        from porterchain_api.dispatch_engine.capabilities import order_needs_liftgate

        route = self.current_route(db, driver_id)
        if route is None:
            return {"route": None}
        events = self._events(db, route.id)
        orders = {o.id: o for o in db.query(Order).filter(Order.id.in_({s["order_id"] for s in route.stops}))}
        stops = []
        for g in group(route.stops):
            evs: set[str] = set().union(*(events.get(k, set()) for k in g["keys"]))
            o = orders.get(g["order_id"])
            addr = self._address(o, g)
            boxes = len(o.packages) if o is not None else 0
            stops.append({
                **g, "status": stop_status(g["kind"], evs), "order_number": o.order_number if o else None,
                "address": addr.get("formatted"), "lat": addr.get("lat"), "lng": addr.get("lng"),
                "boxes": boxes, "needs_pod": g["kind"] in POD_KINDS,
                "notes": (o.special_instructions or None) if o is not None else None,
                "liftgate": o is not None and order_needs_liftgate(o),
            })
        nxt = next((i for i, s in enumerate(stops) if s["status"] in {"pending", "arrived"}), None)
        done = sum(1 for s in stops if s["status"] in {"done", "failed"})
        return {"route": {"id": route.id, "vehicle_class": route.vehicle_class, "stops": stops,
                          "next_index": nxt, "done": done, "total": len(stops)}}

    @staticmethod
    def _address(order: Any, g: dict[str, Any]) -> dict[str, Any]:
        if g.get("meet"):
            return g["meet"]  # rescue handover: the broken van's position, not the order's pickup
        if order is None:
            return {}
        side = order.pickup if g["kind"] in PICKUP_KINDS else order.dropoff
        if not isinstance(side, dict):
            return {}
        stops = side.get("stops")
        if isinstance(stops, list) and stops:
            try:
                idx = int(place(g["keys"][0])[1:])
                return stops[idx] if 0 <= idx < len(stops) else {}
            except ValueError:
                return {}
        return side

    def check_in(self, db: Session, driver: Any, *, keys: list[str], event: str, lat: float | None = None,
                 lng: float | None = None, accuracy_m: float | None = None, note: str | None = None,
                 pod_photo: str | None = None, client_id: str | None = None, short_reason: str | None = None,
                 scan_gate: ScanGate | None = None, now: datetime | None = None) -> dict[str, Any]:
        from porterchain_api.booking_models import Order
        from porterchain_api.dispatch_engine.models import DispatchStopEvent

        now = now or datetime.now(UTC)
        if client_id and db.query(DispatchStopEvent.id).filter(DispatchStopEvent.client_id == client_id).first():
            return {"ok": True, "replayed": True, "moved": [], **self.view(db, driver.id)}
        route = self.current_route(db, driver.id)
        if route is None:
            raise LookupError("no_committed_route")
        by_key = {s["key"]: s for s in route.stops}
        if not keys or any(k not in by_key for k in keys):
            raise LookupError("stop_not_on_route")
        stop = by_key[keys[0]]
        if any(by_key[k]["order_id"] != stop["order_id"] or by_key[k]["kind"] != stop["kind"] for k in keys):
            raise ValueError("keys_must_be_one_stop")
        events = self._events(db, route.id)
        status = stop_status(stop["kind"], set().union(*(events.get(k, set()) for k in keys)))
        if not allowed(stop["kind"], event, status):
            raise ValueError(f"cannot_{event}_when_{status}")
        order = db.get(Order, stop["order_id"])
        if order is None or order.assigned_driver_id != driver.id:
            raise PermissionError("order_not_assigned_to_driver")

        if event in DONE_EVENTS and scan_gate is not None and stop["kind"] in PICKUP_KINDS | POD_KINDS:
            phase = "pickup" if stop["kind"] in PICKUP_KINDS else "delivery"
            progress = scan_gate(order, phase)
            if not progress.get("complete"):
                if phase == "pickup" or not short_reason:
                    raise PermissionError(f"scan_required:{phase}:" + ",".join(progress.get("missing_suffixes") or []))
                self._short_alert(db, order, driver.id, progress, short_reason)
        if event == "delivered" and stop["kind"] in POD_KINDS and not self._has_photo(db, order.id):
            if not pod_photo:
                raise PermissionError("pod_required:photo")
        if pod_photo:
            self._save_pod(db, order.id, driver.id, pod_photo)

        for i, k in enumerate(keys):
            db.add(DispatchStopEvent(route_id=route.id, stop_key=k, order_id=order.id, driver_id=driver.id,
                                     event=event, lat=lat, lng=lng, accuracy_m=accuracy_m,
                                     note=(note or None) and note[:500], at=now,
                                     client_id=(client_id if i == 0 else f"{client_id}:{i}") if client_id else None))
        db.flush()
        moved = self._advance(db, route, order, stop["kind"], event, driver.id, keys)
        if lat is not None and lng is not None:
            self._position(driver.id, lat, lng, accuracy_m, now)
        db.commit()
        return {"ok": True, "moved": moved, "order_state": db.get(Order, order.id).state, **self.view(db, driver.id)}

    def _advance(self, db: Session, route: Any, order: Any, kind: str, event: str, driver_id: str,
                 keys: list[str]) -> list[str]:
        from porterchain_api.booking_engine.order_transitions import transition_order_state
        from porterchain_api.domain.states import OrderState

        payload = {"route_id": route.id, "stop_keys": keys, "source": "dispatch_checkin"}
        if event == "failed":
            if order.state in {"DRIVER_EN_ROUTE", "AT_PICKUP", "PICKED_UP", "IN_TRANSIT", "AT_DESTINATION"}:
                transition_order_state(db, order, OrderState.FAILED, event_type="order.failed",
                                       actor_type="driver", actor_id=driver_id, payload=payload)
                return ["FAILED"]
            return []
        events = self._events(db, route.id)
        mine = [s for s in route.stops if s["order_id"] == order.id]

        def all_done(kinds: set[str], ev: str) -> bool:
            return all(ev in events.get(s["key"], set()) for s in mine if s["kind"] in kinds)

        if kind in PICKUP_KINDS:
            if event == "arrived":
                return walk_to(db, order, "AT_PICKUP", driver_id=driver_id, payload=payload)
            if all_done(PICKUP_KINDS, "picked_up"):
                return walk_to(db, order, "IN_TRANSIT", driver_id=driver_id, payload=payload)
            return walk_to(db, order, "AT_PICKUP", driver_id=driver_id, payload=payload)
        if event == "arrived":
            return walk_to(db, order, "AT_DESTINATION", driver_id=driver_id, payload=payload)
        if all_done(DROP_KINDS, "delivered"):
            return walk_to(db, order, "DELIVERED", driver_id=driver_id, payload=payload)
        return walk_to(db, order, "AT_DESTINATION", driver_id=driver_id, payload=payload)

    @staticmethod
    def _short_alert(db: Session, order: Any, driver_id: str, progress: dict[str, Any], reason: str) -> None:
        from porterchain_api.booking_models import OrderException

        db.add(OrderException(
            order_id=order.id, type="package_short_at_drop", status="open", reported_by_type="driver",
            reported_by_id=driver_id,
            evidence={"phase": "delivery", "missing_suffixes": progress.get("missing_suffixes") or [],
                      "scanned": progress.get("scanned"), "required": progress.get("required"),
                      "reason": reason.strip()[:200]},
        ))

    @staticmethod
    def _has_photo(db: Session, order_id: str) -> bool:
        from porterchain_api.driver_engine.pod_store import has_photo

        return has_photo(db, order_id)

    @staticmethod
    def _save_pod(db: Session, order_id: str, driver_id: str, data_url: str) -> None:
        from porterchain_api.driver_engine.pod_store import attach_photo

        attach_photo(db, order_id, driver_id, data_url)

    @staticmethod
    def _position(driver_id: str, lat: float, lng: float, acc: float | None, now: datetime) -> None:
        try:
            from porterchain_api.platform.last_known import write_last_known

            write_last_known(driver_id=driver_id, lat=lat, lng=lng, recorded_at=now, accuracy_m=acc)
        except Exception:  # noqa: BLE001 — Redis down must not block a check-in
            pass

    def done_keys(self, db: Session, route_ids: list[str]) -> set[str]:
        from porterchain_api.dispatch_engine.models import DispatchStopEvent

        if not route_ids:
            return set()
        rows = db.query(DispatchStopEvent.stop_key).filter(
            DispatchStopEvent.route_id.in_(route_ids), DispatchStopEvent.event.in_(tuple(DONE_EVENTS))
        )
        return {r[0] for r in rows}
