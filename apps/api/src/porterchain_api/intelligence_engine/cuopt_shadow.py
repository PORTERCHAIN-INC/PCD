"""cuOpt shadow A/B vs PorterChain OR-Tools — never mutates commit SoT.

Builds a Valhalla cost matrix for pool stop coords, calls NVIDIA cuOpt Catalog,
compares estimated totals to the day-plan scorecard. Gated by ``phase2_cuopt_shadow``.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

_MAX_LOCATIONS = 24  # Catalog free-tier friendly; depot + stops


def cuopt_shadow_enabled(settings: Any | None = None) -> bool:
    from porterchain_api.config import get_settings

    s = settings or get_settings()
    return bool(getattr(s, "phase2_cuopt_shadow", False))


def run_cuopt_shadow(
    db: Session,
    *,
    order_ids: list[str] | None,
    vroom_metrics: dict[str, Any] | None,
    vehicle_count: int = 1,
) -> dict[str, Any]:
    """Compare cuOpt vs VROOM on the same Valhalla matrix. Never commits.

    Returns a JSON-serialisable shadow report for optimize ``metrics.cuopt_shadow``.
    """
    from porterchain_api.intelligence_engine.cuopt_client import (
        cuopt_configured,
        cuopt_status,
        optimize_routing,
    )
    from porterchain_api.intelligence_engine.usage import record_ai_usage

    if not cuopt_shadow_enabled():
        return {"status": "disabled", "note": "Set PORTERCHAIN_PHASE2_CUOPT_SHADOW=true"}
    if not cuopt_configured():
        return {
            "status": "unavailable",
            "reason": "nvidia_api_key_missing",
            **cuopt_status(),
        }

    coords = _order_coords(db, order_ids or [])
    if len(coords) < 2:
        return {
            "status": "skipped",
            "reason": "need_geocoded_stops",
            "location_count": len(coords),
        }

    # Cap for free Catalog RPM / payload size (depot = first point).
    points = coords[:_MAX_LOCATIONS]
    matrix = _maps_duration_matrix(points)
    if matrix is None:
        return {
            "status": "skipped",
            "reason": "valhalla_matrix_unavailable",
            "location_count": len(points),
        }

    vroom = dict(vroom_metrics or {})
    vroom_km = _as_float(vroom.get("after_distance_km"))
    if vroom_km is None and vroom.get("after_distance_m") is not None:
        try:
            vroom_km = float(vroom["after_distance_m"]) / 1000.0
        except (TypeError, ValueError):
            vroom_km = None

    try:
        parsed = optimize_routing(
            cost_matrix=matrix,
            vehicle_count=max(1, int(vehicle_count or 1)),
        )
    except ValueError as exc:
        return {"status": "unavailable", "reason": str(exc), **cuopt_status()}
    except RuntimeError as exc:
        reason = str(exc)
        try:
            record_ai_usage(
                db,
                provider="nvidia_cuopt",
                model="cuOpt_OptimizedRouting",
                feature="cuopt_shadow",
                status="error",
                error=reason[:500],
                meta={"location_count": len(points)},
            )
        except Exception:  # noqa: BLE001
            logger.debug("cuopt usage ledger skip", exc_info=True)
        return {
            "status": "unavailable",
            "reason": reason,
            "fallback": "ortools_only",
            **cuopt_status(),
        }

    cuopt_cost = parsed.get("total_cost")
    # Matrix cells are meters → treat total_cost as meters when plausible.
    cuopt_km = None
    if isinstance(cuopt_cost, (int, float)):
        cuopt_km = round(float(cuopt_cost) / 1000.0, 2)

    delta_km = None
    winner = "tie"
    if vroom_km is not None and cuopt_km is not None:
        delta_km = round(float(vroom_km) - float(cuopt_km), 2)
        if delta_km > 0.05:
            winner = "cuopt"
        elif delta_km < -0.05:
            winner = "ortools"

    report = {
        "status": "ok" if parsed.get("ok") else "partial",
        "location_count": len(points),
        "vehicle_count": max(1, int(vehicle_count or 1)),
        "ortools_distance_km": vroom_km,
        "vroom_distance_km": vroom_km,  # alias for one release
        "cuopt_distance_km": cuopt_km,
        "delta_km_ortools_minus_cuopt": delta_km,
        "winner": winner,
        "cuopt_latency_ms": parsed.get("latency_ms"),
        "cuopt_vehicle_count_used": parsed.get("vehicle_count_used"),
        "commit_sot": "porterchain_ortools",
        "note": (
            "Shadow A/B only. Human may inspect; day plan commit stays OR-Tools "
            "until a promote flag after measured GTA wins."
        ),
    }
    try:
        record_ai_usage(
            db,
            provider="nvidia_cuopt",
            model="cuOpt_OptimizedRouting",
            feature="cuopt_shadow",
            status="ok",
            latency_ms=parsed.get("latency_ms"),
            meta={
                "winner": winner,
                "vroom_km": vroom_km,
                "cuopt_km": cuopt_km,
                "locations": len(points),
            },
        )
    except Exception:  # noqa: BLE001
        logger.debug("cuopt usage ledger skip", exc_info=True)
    return report


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _order_coords(db: Session, order_ids: list[str]) -> list[tuple[float, float]]:
    """Pickup coords for pool orders (depot = first). Dropoffs omitted to keep N small."""
    from porterchain_api.booking_models import Order

    if not order_ids:
        return []
    rows = db.query(Order).filter(Order.id.in_(list(order_ids)[:_MAX_LOCATIONS])).all()
    by_id = {str(o.id): o for o in rows}
    points: list[tuple[float, float]] = []
    for oid in order_ids:
        order = by_id.get(str(oid))
        if not order:
            continue
        pt = _point_from_order(order)
        if pt:
            points.append(pt)
    return points


def _point_from_order(order: Any) -> tuple[float, float] | None:
    for attr in ("pickup", "pickup_address", "origin"):
        raw = getattr(order, attr, None)
        pt = _coords(raw)
        if pt:
            return pt
    meta = getattr(order, "metadata_json", None) or getattr(order, "meta", None)
    if isinstance(meta, dict):
        for key in ("pickup", "origin", "pickup_coords"):
            pt = _coords(meta.get(key))
            if pt:
                return pt
    return None


def _coords(raw: Any) -> tuple[float, float] | None:
    if not isinstance(raw, dict):
        return None
    lat = raw.get("lat") or raw.get("latitude")
    lng = raw.get("lng") or raw.get("lon") or raw.get("longitude")
    if lat is None or lng is None:
        nested = raw.get("location") or raw.get("coords") or raw.get("address")
        if isinstance(nested, dict):
            return _coords(nested)
        return None
    try:
        return float(lat), float(lng)
    except (TypeError, ValueError):
        return None


def _maps_duration_matrix(
    points: list[tuple[float, float]],
) -> list[list[float]] | None:
    from porterchain_services.maps.service import MapsService

    maps = MapsService()
    matrix, source = maps.matrix_durations(points, points)
    if not matrix or source is None or len(matrix) != len(points):
        return None
    out: list[list[float]] = []
    for i, row in enumerate(matrix):
        if not isinstance(row, list) or len(row) != len(points):
            return None
        parsed: list[float] = []
        for j, cell in enumerate(row):
            if i == j:
                parsed.append(0.0)
                continue
            seconds, meters = cell if isinstance(cell, tuple) else (None, None)
            if meters is not None:
                parsed.append(float(meters))
            elif seconds is not None:
                # ~30 km/h urban proxy — labeled cost only for solver input
                parsed.append(float(seconds) * 8.33)
            else:
                return None
        out.append(parsed)
    return out
