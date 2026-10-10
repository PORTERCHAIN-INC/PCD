"""Quote + geocode resolution for merchant route import. Public Maps APIs only."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from porterchain_pricing import GeoPoint, PricingRequest
from porterchain_services.maps.route_helpers import multi_stop_route_from_valhalla
from porterchain_services.maps.service import MapsService
from sqlalchemy.orm import Session

from porterchain_api.merchant_engine.import_errors import (
    route_row_error,
    stop_sheet_row,
)
from porterchain_api.merchant_engine.import_geocode import GeocodeResult, geocode_stop
from porterchain_api.merchant_engine.import_rows import packages_clean
from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_api.merchant_engine.service_area import assert_ontario_stop
from porterchain_api.pricing_engine import get_pricing_service
from porterchain_api.services.routing import resolve_route_distance

logger = logging.getLogger(__name__)


def split_route_quote(quote: dict[str, Any] | None) -> tuple[dict[str, Any] | None, Any]:
    """Keep the line-item picture off the Valhalla geometry blob."""
    if not isinstance(quote, dict):
        return quote, None
    data = dict(quote)
    geometry = data.pop("route_geometry", None)
    return data, geometry


def split_stops(
    stops: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    ordered = sorted(stops, key=lambda s: int(s.get("sequence") or 0))
    pickups = [s for s in ordered if s.get("stop_type") == "pickup"]
    drops = [s for s in ordered if s.get("stop_type") != "pickup"]
    if not pickups or not drops:
        raise ValueError("route_import_needs_pickup_and_drop")
    pickup = pickups[0]
    dropoff = drops[-1]
    additional = drops[:-1]
    return pickup, dropoff, additional


def explain_stops(stops: list[dict[str, Any]]) -> str:
    n_pick = sum(1 for s in stops if s.get("stop_type") == "pickup")
    n_drop = sum(1 for s in stops if s.get("stop_type") == "drop")
    return f"{n_pick} pickup, {n_drop} drops ordered by sequence; geocoded via Nominatim; distance via Valhalla/OSRM."


def geo_fields(geo: Any, *, sequence: Any, stop_type: Any) -> dict[str, Any]:
    return {
        "sequence": sequence,
        "stop_type": stop_type,
        "raw_address": geo.raw,
        "address": geo.raw,
        "formatted": geo.formatted,
        "unit": geo.unit,
        "lat": geo.lat,
        "lng": geo.lng,
        "place_id": geo.place_id,
        "geocode_source": geo.source,
        "geocode_status": geo.status,
        "confidence": geo.confidence,
        "geocode_query": geo.geocode_query,
        "issues": list(geo.issues),
        "city": geo.city,
        "postal": geo.postal,
    }


def resolve_stops(
    stops_in: list[dict[str, Any]], *, geocode_now: bool = False
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    normalized_in: list[dict[str, Any]] = []
    for i, s in enumerate(stops_in):
        st = str(s.get("stop_type") or ("pickup" if i == 0 else "drop")).lower()
        if st not in ("pickup", "drop"):
            st = "pickup" if i == 0 else "drop"
        normalized_in.append(
            {
                **s,
                "stop_type": st,
                "sequence": int(s.get("sequence") or i + 1),
                "address": s.get("address") or s.get("formatted") or s.get("raw_address") or "",
            }
        )
    normalized_in.sort(key=lambda x: int(x.get("sequence") or 0))

    resolved: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    for i, s in enumerate(normalized_in):
        has_coords = s.get("lat") is not None and s.get("lng") is not None
        if has_coords or geocode_now:
            geo = geocode_stop(
                address=str(s.get("address") or ""),
                unit=s.get("unit"),
                city=s.get("city"),
                province=s.get("province"),
                postal=s.get("postal"),
                lat=s.get("lat"),
                lng=s.get("lng"),
                place_id=s.get("place_id"),
                source=s.get("geocode_source"),
            )
        else:
            geo = GeocodeResult(
                lat=None,
                lng=None,
                formatted=None,
                status="pending",
                confidence=0.0,
                unit=s.get("unit"),
                raw=str(s.get("address") or ""),
                geocode_query=str(s.get("address") or ""),
                issues=[],
            )
        stop = {
            **geo_fields(geo, sequence=s.get("sequence"), stop_type=s.get("stop_type")),
            "id": s.get("id") or f"pc-stop-{s.get('sequence') or i + 1}",
            "row": s.get("row"),
            # Prefer values Nominatim/normalize just found when the CSV cell was freeform.
            "postal": geo.postal or s.get("postal"),
            "city": geo.city or s.get("city"),
            "province": s.get("province") or "ON",
            "contact_name": s.get("contact_name"),
            "contact_phone": s.get("contact_phone"),
            "contact_email": s.get("contact_email"),
            "external_ref": s.get("external_ref"),
            "notes": s.get("notes"),
            "packages": packages_clean(s.get("packages")),
            "time_window_start": s.get("time_window_start"),
            "time_window_end": s.get("time_window_end"),
        }
        resolved.append(stop)
        row = stop_sheet_row(s, i)
        if geo.status == "failed":
            codes = stop.get("issues") or ["stop.geocode_failed"]
            for code in codes:
                errors.append(route_row_error(row=row, code=str(code)))
        elif geo.status != "pending":
            area = assert_ontario_stop(
                label=f"stop {i + 1}",
                formatted=stop.get("formatted") or stop.get("address"),
                postal=stop.get("postal"),
            )
            if area:
                errors.append(route_row_error(row=row, code=str(area)))
    return resolved, errors


def quote_if_ready(
    db: Session,
    ctx: MerchantContext,
    vehicle_class: str,
    scheduled_at: Any,
    stops: list[dict[str, Any]],
    *,
    requires_liftgate: bool = False,
) -> dict[str, Any] | None:
    if not stops or any(
        s.get("geocode_status") in {"failed", "pending"} or s.get("lat") is None or s.get("lng") is None
        for s in stops
    ):
        return None
    try:
        pickup, dropoff, additional = split_stops(stops)
    except ValueError:
        return None

    def _geo(stop: dict[str, Any]) -> GeoPoint:
        return GeoPoint(
            lat=stop["lat"],
            lng=stop["lng"],
            formatted=stop.get("formatted"),
            postal=stop.get("postal") or "",
        )

    pickup_geo = _geo(pickup)
    dropoff_geo = _geo(dropoff)
    add_geo = [_geo(s) for s in additional]
    distance, duration_seconds, routing_source = resolve_route_distance(pickup_geo, dropoff_geo, add_geo)
    route_geometry = None
    points = [
        (pickup["lat"], pickup["lng"]),
        *[(s["lat"], s["lng"]) for s in additional],
        (dropoff["lat"], dropoff["lng"]),
    ]
    try:
        multi = MapsService().route_multi([(float(a), float(b)) for a, b in points])
        route_geometry = multi_stop_route_from_valhalla(multi)
        if route_geometry and route_geometry.get("distance_meters"):
            distance = int(route_geometry["distance_meters"])
            duration_seconds = int(route_geometry.get("duration_seconds") or 0) or duration_seconds
            routing_source = "valhalla"
    except Exception:
        logger.debug("multi-stop Valhalla preview unavailable", exc_info=True)

    if scheduled_at:
        try:
            sched = datetime.fromisoformat(str(scheduled_at).replace("Z", "+00:00"))
        except ValueError:
            sched = datetime.now(UTC)
    else:
        sched = datetime.now(UTC)

    request = PricingRequest(
        pickup=pickup_geo,
        dropoff=dropoff_geo,
        vehicle_class=vehicle_class,
        package_type="looseParcel",
        schedule_mode="schedule",
        scheduled_at=sched,
        additional_stops=add_geo,
        distance_meters=distance,
        estimated_duration_minutes=int(duration_seconds / 60) if duration_seconds else None,
        routing_source=routing_source,
        channel="merchant",
        merchant_id=ctx.merchant.id,
        requires_liftgate=requires_liftgate,
    )
    pricing = get_pricing_service(db)
    breakdown = pricing.calculate_merchant(request)
    meta = breakdown.metadata if isinstance(breakdown.metadata, dict) else {}
    if meta.get("fsa_refused"):
        # No price rather than a $0 preview; confirm → create_shipment refuses.
        return None
    from porterchain_api.merchant_engine.quote_snapshot import merchant_facing_quote

    picture = merchant_facing_quote(
        {
            **pricing.to_api_breakdown(breakdown),
            "vehicle_class": vehicle_class,
            "distance_meters": distance,
            "duration_seconds": duration_seconds,
            "total_pickups": 1,
            "total_drops": 1 + len(additional),
        }
    )
    return {
        **(picture or {}),
        "route_geometry": route_geometry,
    }
