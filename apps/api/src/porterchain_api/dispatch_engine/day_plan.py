"""Valhalla cost matrix and the one-line draw after a plan is accepted."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from porterchain_services.maps.costing import valhalla_costing_for_vehicle_class

_TORONTO = ZoneInfo("America/Toronto")


def toronto_window_seconds(scheduled_at: datetime, *, day: date) -> int | None:
    """Clock seconds in America/Toronto. Another calendar day is not a window."""
    local = scheduled_at.astimezone(_TORONTO)
    if local.date() != day:
        return None
    return local.hour * 3600 + local.minute * 60 + local.second


def drive_seconds(
    points: list[tuple[float, float]],
    *,
    vehicle_class: str | None,
) -> tuple[list[list[int]] | None, str | None]:
    """Call Valhalla sources_to_targets. Service time is not in these cells.

    A matrix whose source is not ``valhalla`` is not a cost. The caller must
    keep the current stop list.
    """
    from porterchain_services.maps.service import MapsService

    raw, source = MapsService().matrix_durations(points, points, vehicle_class=vehicle_class)
    if source != "valhalla" or not raw:
        return None, source
    seconds = [[0 if cell[0] is None else int(cell[0]) for cell in row] for row in raw]
    return seconds, source


def costing_for(vehicle_class: str | None) -> str:
    return valhalla_costing_for_vehicle_class(vehicle_class)


_PICKED_UP = frozenset({"PICKED_UP", "EN_ROUTE", "ARRIVED"})


def payload_from_orders(
    orders: list[Any],
    *,
    vehicle_class: str | None,
    driver_id: str,
    insert_order_id: str | None = None,
    apply_on_ready: bool = True,
    origin: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """One van's stops. Service time sits on the stop. The road cell stays drive seconds."""
    stops: list[dict[str, Any]] = []
    jobs: list[dict[str, Any]] = []
    order_ids: list[str] = []
    today = datetime.now(_TORONTO).date()
    for order in orders:
        oid = str(order.id)
        order_ids.append(oid)
        pickup = _pair(getattr(order, "pickup", None))
        dropoff = _pair(getattr(order, "dropoff", None))
        window = None
        scheduled = getattr(order, "scheduled_at", None)
        if isinstance(scheduled, datetime):
            window = toronto_window_seconds(scheduled, day=today)
        service = int(getattr(order, "service_minutes", 0) or 0) * 60
        pickup_id = f"{oid}:pickup"
        dropoff_id = f"{oid}:dropoff"
        stops.append(
            {
                "id": pickup_id,
                "lat": None if pickup is None else pickup[0],
                "lng": None if pickup is None else pickup[1],
                "service_seconds": service,
                "window_end_s": window,
            }
        )
        stops.append(
            {
                "id": dropoff_id,
                "lat": None if dropoff is None else dropoff[0],
                "lng": None if dropoff is None else dropoff[1],
                "service_seconds": service,
                "window_end_s": window,
            }
        )
        state = str(getattr(order, "state", "") or "")
        inserted = insert_order_id is not None and oid == str(insert_order_id)
        jobs.append(
            {
                "id": oid,
                "pickup_id": pickup_id,
                "dropoff_id": dropoff_id,
                "kg": float(getattr(order, "weight_kg", 0) or 0),
                "volume_m3": float(getattr(order, "volume_m3", 0) or 0),
                "pallets": float(getattr(order, "pallets", 0) or 0),
                "parcels": float(getattr(order, "parcels", 0) or 0),
                "picked_up": state in _PICKED_UP and not inserted,
            }
        )
    return {
        "stops": stops,
        "jobs": jobs,
        "order_ids": order_ids,
        "vehicle_class": vehicle_class,
        "pc_driver_id": driver_id,
        "apply_on_ready": apply_on_ready,
        "origin": origin,
        "current_order": [stop["id"] for stop in stops],
    }


def _pair(addr: Any) -> tuple[float, float] | None:
    if not isinstance(addr, dict):
        return None
    lat = addr.get("lat") if addr.get("lat") is not None else addr.get("latitude")
    lng = addr.get("lng") if addr.get("lng") is not None else addr.get("lon") or addr.get("longitude")
    if lat is None or lng is None:
        return None
    return float(lat), float(lng)


def finish_porterchain_run(db: Any, run_id: str, rec: dict[str, Any]) -> dict[str, Any]:
    """Worker entry for one van. Accept draws the stored order and does not search."""
    from porterchain_api.dispatch_engine.optimize_run_store import write_optimize_run

    del db
    if rec.get("phase") == "accept":
        line = accept_line(list(rec.get("points") or []), vehicle_class=rec.get("vehicle_class"))
        stored = {**rec, "status": "ready", "geometry": line, "searched": False, "engine": "porterchain"}
        write_optimize_run(run_id, stored)
        return stored

    from porterchain_api.dispatch_engine.capacity import VehicleCapacity
    from porterchain_api.dispatch_engine.sequencer import DayJob, DayStop, solve_day

    stops = [
        DayStop(
            id=str(row["id"]),
            lat=row.get("lat"),
            lng=row.get("lng"),
            service_seconds=int(row.get("service_seconds") or 0),
            window_start_s=row.get("window_start_s"),
            window_end_s=row.get("window_end_s"),
        )
        for row in rec.get("stops") or []
    ]
    jobs = [
        DayJob(
            id=str(row["id"]),
            pickup_id=str(row["pickup_id"]),
            dropoff_id=str(row["dropoff_id"]),
            extra_ids=tuple(row.get("extra_ids") or ()),
            kg=float(row.get("kg") or 0),
            volume_m3=float(row.get("volume_m3") or 0),
            pallets=float(row.get("pallets") or 0),
            parcels=float(row.get("parcels") or 0),
            skill=row.get("skill"),
            locked=bool(row.get("locked")),
            picked_up=bool(row.get("picked_up")),
        )
        for row in rec.get("jobs") or []
    ]
    origin = rec.get("origin") if isinstance(rec.get("origin"), dict) else None
    if origin and origin.get("lat") is not None and origin.get("lng") is not None:
        start = (float(origin["lat"]), float(origin["lng"]))
    else:
        start = next(
            ((float(stop.lat), float(stop.lng)) for stop in stops if stop.lat is not None and stop.lng is not None),
            (0.0, 0.0),
        )
    points = [start]
    points.extend((float(stop.lat or 0), float(stop.lng or 0)) for stop in stops)
    matrix, source = drive_seconds(points, vehicle_class=rec.get("vehicle_class"))
    caps = rec.get("capacity") or {}
    plan = solve_day(
        stops=stops,
        jobs=jobs,
        matrix=matrix,
        matrix_source=source,
        on_break=bool(rec.get("on_break")),
        capacity=VehicleCapacity(
            kg=caps.get("kg"),
            volume_m3=caps.get("volume_m3"),
            pallets=caps.get("pallets"),
            parcels=caps.get("parcels"),
        ),
        vehicle_class=rec.get("vehicle_class"),
        current_order=list(rec.get("current_order") or [stop.id for stop in stops]),
        time_limit_s=int(rec.get("time_limit_s") or 3),
    )
    stored = {
        **rec,
        "status": "ready",
        "engine": "porterchain",
        "waypoints": plan.waypoints,
        "unassigned": plan.unassigned,
        "label": plan.label,
        "added_minutes": plan.added_minutes,
        "matrix_source": plan.matrix_source,
        "assignments": _assignments(plan.waypoints),
        "line_points": _line_points(plan.waypoints, stops),
        "metrics": {
            "engine": "porterchain",
            "label": plan.label,
            **({"same_role": "greedy"} if plan.label == "insertion" else {}),
        },
    }
    write_optimize_run(run_id, stored)
    return stored


def queue_one_van(payload: dict[str, Any]) -> dict[str, Any]:
    """Store one van's stops and let the worker search. This does not search."""
    from uuid import uuid4

    from porterchain_api.dispatch_engine.optimize_run_store import (
        enqueue_optimize_job,
        write_optimize_run,
    )

    run_id = str(uuid4())
    rec = {
        **payload,
        "run_id": run_id,
        "status": "pending",
        "ok": True,
        "engine": "porterchain",
        "mode": "optimize_routes",
        "assignments": [],
        "metrics": {"engine": "porterchain"},
    }
    write_optimize_run(run_id, rec)
    enqueue_optimize_job(run_id)
    return rec


def _assignments(waypoints: list[str]) -> list[dict[str, Any]]:
    rows = []
    for seq, stop_id in enumerate(waypoints):
        order_id, sep, leg = str(stop_id).rpartition(":")
        if not sep:
            order_id, leg = str(stop_id), "stop"
        rows.append(
            {
                "sequence": seq,
                "order_id": order_id,
                "porterchain_order_id": order_id,
                "stops": [{"type": leg, "stop_type": leg}],
            }
        )
    return rows


def _line_points(waypoints: list[str], stops: list[Any]) -> list[list[float]]:
    by_id = {stop.id: stop for stop in stops}
    points = []
    for stop_id in waypoints:
        stop = by_id.get(stop_id)
        if stop is None or stop.lat is None or stop.lng is None:
            continue
        points.append([float(stop.lat), float(stop.lng)])
    return points


def accept_line(
    points: list[tuple[float, float]],
    *,
    vehicle_class: str | None,
) -> dict[str, Any] | None:
    """Draw the stored order once. This does not search."""
    from porterchain_services.maps.route_helpers import multi_stop_route_from_valhalla
    from porterchain_services.maps.service import MapsService

    raw = MapsService().route_multi(points, vehicle_class=vehicle_class)
    return multi_stop_route_from_valhalla(raw)
