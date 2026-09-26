"""Commercial stop/parcel amend — BOOKED or DISPATCH_READY, no driver.

Parcels sync to ``packages``; JSON stops remain dual-write until cutover.
A change re-quotes through the existing merchant pricing engine.
"""

from __future__ import annotations

import logging
from types import SimpleNamespace
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.config import Settings
from porterchain_api.domain.customer_goods import persist_vehicle_class
from porterchain_api.merchant_engine import events as E
from porterchain_api.merchant_engine.route_import_service import (
    KIND_ROUTE_V1,
    MerchantRouteImportService,
    split_route_quote,
)
from porterchain_api.merchant_models import BulkImportJob, Merchant
from porterchain_api.booking_models import Order
from porterchain_api.order_engine.buckets import WAITING_DISPATCH

logger = logging.getLogger(__name__)

AMENDABLE_STATES = frozenset(WAITING_DISPATCH)
PARCEL_AMEND_LOCKED = "parcel_amend_locked"
PARCEL_AMEND_LOCKED_DRIVER = (
    "This route cannot be changed after a driver is assigned. Cancel it and book again."
)
PARCEL_AMEND_LOCKED_STATE = (
    "This route cannot be changed once it is in progress. Cancel it and book again."
)
PARCEL_AMEND_GEOCODE = "parcel_amend_geocode_failed"
PARCEL_AMEND_GEOCODE_MSG = (
    "One or more stops could not be located. Check the addresses and try again."
)
PARCEL_AMEND_QUOTE = "parcel_amend_quote_failed"
PARCEL_AMEND_QUOTE_MSG = "Could not price this route. Check the stops and try again."
PARCEL_AMEND_STOPS = "parcel_amend_needs_pickup_and_drop"
PARCEL_AMEND_STOPS_MSG = "A route needs a pickup and at least one drop."


class ParcelAmendError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(code)
        self.code = code
        self.message = message


def parcel_amend_http(exc: BaseException) -> tuple[int, str]:
    if isinstance(exc, ParcelAmendError):
        status = 409 if exc.code == PARCEL_AMEND_LOCKED else 400
        return status, exc.message
    return 400, str(exc)


def parcel_amendable(order: Order) -> bool:
    if order.assigned_driver_id:
        return False
    return str(order.state) in AMENDABLE_STATES


def assert_parcel_amendable(order: Order) -> None:
    if order.assigned_driver_id:
        raise ParcelAmendError(PARCEL_AMEND_LOCKED, PARCEL_AMEND_LOCKED_DRIVER)
    if str(order.state) not in AMENDABLE_STATES:
        raise ParcelAmendError(PARCEL_AMEND_LOCKED, PARCEL_AMEND_LOCKED_STATE)


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _addr_stop(addr: Any, *, sequence: int, stop_type: str) -> dict[str, Any]:
    data = addr if isinstance(addr, dict) else {"formatted": str(addr or "")}
    formatted = str(data.get("formatted") or data.get("address") or "")
    return {
        "sequence": sequence,
        "stop_type": stop_type,
        "address": formatted,
        "formatted": formatted,
        "lat": data.get("lat"),
        "lng": data.get("lng"),
        "postal": data.get("postal") or data.get("postal_code"),
        "city": data.get("city"),
        "unit": data.get("unit"),
        "notes": data.get("notes"),
        "packages": list(data.get("packages") or []) if isinstance(data.get("packages"), list) else [],
    }


def _normalize_stop_type(raw: Any, *, index: int) -> str:
    kind = str(raw or "").strip().lower()
    if kind in ("dropoff", "drop", "delivery", "do", "dest"):
        return "drop"
    if kind in ("pickup", "pick", "pu", "origin"):
        return "pickup"
    return "pickup" if index == 0 else "drop"


def commercial_stops(order: Order) -> list[dict[str, Any]]:
    """Pickup + drops with nested packages — SSOT for route job and Order 360."""
    meta = _as_dict(order.compliance_metadata)
    rich = meta.get("stops")
    if isinstance(rich, list) and rich:
        ordered = sorted(
            (s for s in rich if isinstance(s, dict)),
            key=lambda s: int(s.get("sequence") or 0),
        )
        out: list[dict[str, Any]] = []
        for i, stop in enumerate(ordered):
            formatted = str(stop.get("formatted") or stop.get("address") or "")
            out.append(
                {
                    "id": stop.get("id"),
                    "sequence": int(stop.get("sequence") or i + 1),
                    "stop_type": _normalize_stop_type(stop.get("stop_type") or stop.get("type"), index=i),
                    "address": formatted,
                    "formatted": formatted,
                    "unit": stop.get("unit"),
                    "city": stop.get("city"),
                    "province": stop.get("province"),
                    "postal": stop.get("postal") or stop.get("postal_code"),
                    "lat": stop.get("lat"),
                    "lng": stop.get("lng"),
                    "contact_name": stop.get("contact_name"),
                    "contact_phone": stop.get("contact_phone"),
                    "contact_email": stop.get("contact_email"),
                    "notes": stop.get("notes"),
                    "time_window_start": stop.get("time_window_start"),
                    "time_window_end": stop.get("time_window_end"),
                    "packages": list(stop.get("packages") or [])
                    if isinstance(stop.get("packages"), list)
                    else [],
                }
            )
        return out

    from porterchain_api.order_engine.platform_detail import resolve_order_additional_stops

    pickup = _as_dict(order.pickup)
    dropoff = _as_dict(order.dropoff)
    middles = resolve_order_additional_stops(order)
    stops = [_addr_stop(pickup, sequence=1, stop_type="pickup")]
    seq = 2
    for middle in middles:
        stops.append(_addr_stop(middle, sequence=seq, stop_type="drop"))
        seq += 1
    stops.append(_addr_stop(dropoff, sequence=seq, stop_type="drop"))
    return stops


def packages_from_order(order: Order) -> list[dict[str, Any]]:
    packages: list[dict[str, Any]] = []
    for stop in commercial_stops(order):
        for pkg in stop.get("packages") or []:
            if not isinstance(pkg, dict):
                continue
            packages.append(
                {
                    **pkg,
                    "stop_sequence": stop.get("sequence"),
                    "stop_type": stop.get("stop_type"),
                    "stop_formatted": stop.get("formatted"),
                }
            )
    return packages


def route_import_job_id(order: Order) -> str | None:
    meta = _as_dict(order.compliance_metadata)
    raw = meta.get("route_import_job_id")
    return str(raw) if raw else None


class ParcelAmendService:
    def __init__(self) -> None:
        self._routes = MerchantRouteImportService()

    def apply(
        self,
        db: Session,
        order: Order,
        stops_in: list[dict[str, Any]],
        merchant: Merchant,
        *,
        actor_type: str,
        actor_id: str | None,
        vehicle_class: str | None = None,
        settings: Settings | None = None,
    ) -> dict[str, Any]:
        assert_parcel_amendable(order)
        incoming = []
        for i, raw in enumerate(stops_in):
            if not isinstance(raw, dict):
                continue
            incoming.append(
                {
                    **raw,
                    "address": raw.get("address") or raw.get("formatted") or "",
                    "stop_type": _normalize_stop_type(raw.get("stop_type") or raw.get("type"), index=i),
                    "sequence": raw.get("sequence") or i + 1,
                }
            )
        resolved, errors = self._routes._resolve_stops(incoming, geocode_now=True)
        if errors:
            raise ParcelAmendError(PARCEL_AMEND_GEOCODE, PARCEL_AMEND_GEOCODE_MSG)
        try:
            pickup, dropoff, additional = self._routes._split_stops(resolved)
        except ValueError as exc:
            raise ParcelAmendError(PARCEL_AMEND_STOPS, PARCEL_AMEND_STOPS_MSG) from exc

        meta = _as_dict(order.compliance_metadata)
        vehicle = persist_vehicle_class(vehicle_class or meta.get("vehicle_class"))
        liftgate = bool(meta.get("requires_liftgate"))
        ctx = SimpleNamespace(merchant=merchant, user=SimpleNamespace(id=actor_id or "system"))
        quote, geometry = split_route_quote(
            self._routes._quote_if_ready(
                db,
                ctx,
                str(vehicle),
                order.scheduled_at,
                resolved,
                requires_liftgate=liftgate,
            )
        )
        if quote is None:
            raise ParcelAmendError(PARCEL_AMEND_QUOTE, PARCEL_AMEND_QUOTE_MSG)

        amount_cents = int(quote.get("amount_cents") or 0)
        order.amount_cents = amount_cents
        order.pickup = {
            "formatted": pickup.get("formatted") or pickup.get("address"),
            "lat": pickup.get("lat"),
            "lng": pickup.get("lng"),
            "postal": pickup.get("postal"),
            "city": pickup.get("city"),
        }
        order.dropoff = {
            "formatted": dropoff.get("formatted") or dropoff.get("address"),
            "lat": dropoff.get("lat"),
            "lng": dropoff.get("lng"),
            "postal": dropoff.get("postal"),
            "city": dropoff.get("city"),
        }
        compliance = dict(meta)
        compliance["stops"] = [self._routes._fleetbase_stop(stop) for stop in resolved]
        compliance["additional_stops"] = [
            {
                "formatted": s.get("formatted") or s.get("address"),
                "lat": s.get("lat"),
                "lng": s.get("lng"),
                "postal": s.get("postal"),
            }
            for s in additional
        ]
        compliance["vehicle_class"] = vehicle
        compliance["quote"] = quote
        weights = [
            float(pkg["weight_kg"])
            for stop in resolved
            for pkg in (stop.get("packages") or [])
            if isinstance(pkg, dict) and pkg.get("weight_kg") not in (None, "")
        ]
        if weights:
            compliance["weight_kg"] = round(sum(weights), 3)
        order.compliance_metadata = compliance
        notes = self._routes._driver_notes(resolved)
        if notes:
            order.special_instructions = notes

        from porterchain_api.booking_engine._core import emit_event

        emit_event(
            db,
            event_type=E.MERCHANT_PARCELS_AMENDED,
            aggregate_type="order",
            aggregate_id=order.id,
            correlation_id=merchant.id,
            actor_type=actor_type,
            actor_id=actor_id,
            payload={
                "amount_cents": amount_cents,
                "stop_count": len(resolved),
                "previous_state": order.state,
            },
        )

        job = self._linked_job(db, order)
        if job is not None:
            cfg = dict(job.job_config or {})
            cfg["stops"] = resolved
            cfg["quote"] = quote
            if geometry is not None:
                cfg["route_geometry"] = geometry
            cfg["vehicle_class"] = vehicle
            job.job_config = cfg
            job.preview = resolved
            db.add(job)

        db.add(order)
        db.flush()
        from porterchain_api.merchant_engine.package_service import PackageService

        PackageService().sync_from_order(db, order)
        db.commit()
        db.refresh(order)

        if settings is not None:
            try:
                from porterchain_api.fleetbase_engine.booking_sync_service import BookingSyncService

                BookingSyncService().push_order(db, settings, order)
            except Exception:  # noqa: BLE001 — commercial amend must not fail on Fleetbase
                logger.debug("fleetbase cargo sync skipped after parcel amend", exc_info=True)

        return {
            "order_id": order.id,
            "state": order.state,
            "amount_cents": order.amount_cents,
            "quote": quote,
            "stops": commercial_stops(order),
            "parcel_amendable": parcel_amendable(order),
        }

    def _linked_job(self, db: Session, order: Order) -> BulkImportJob | None:
        job_id = route_import_job_id(order)
        if job_id:
            job = db.query(BulkImportJob).filter(BulkImportJob.id == job_id).first()
            if job:
                return job
        if not order.merchant_id:
            return None
        rows = (
            db.query(BulkImportJob)
            .filter(
                BulkImportJob.merchant_id == order.merchant_id,
                BulkImportJob.kind == KIND_ROUTE_V1,
            )
            .order_by(BulkImportJob.created_at.desc())
            .limit(50)
            .all()
        )
        for row in rows:
            if order.id in (row.order_ids or []):
                return row
        return None
