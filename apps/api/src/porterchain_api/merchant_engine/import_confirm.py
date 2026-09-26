"""Confirm a route-import job into a merchant booking + Fleetbase stop payload."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.config import Settings
from porterchain_api.domain.customer_goods import persist_vehicle_class
from porterchain_api.domain.merchant_states import BulkImportStatus
from porterchain_api.domain.states import OrderSource
from porterchain_api.merchant_engine.booking_service import MerchantBookingService
from porterchain_api.merchant_engine.import_mapping_profiles import save_profile
from porterchain_api.merchant_engine.import_quote import split_stops
from porterchain_api.merchant_engine.import_rows import optional_float, optional_text
from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_api.merchant_engine.stop_cargo import fleetbase_stop
from porterchain_api.merchant_models import BulkImportJob
from porterchain_api.schemas_merchant import AddressInput, MerchantBookDeliveryRequest

logger = logging.getLogger(__name__)


def driver_notes(stops: list[dict[str, Any]]) -> str | None:
    bits: list[str] = []
    for s in stops:
        unit = s.get("unit")
        if unit:
            bits.append(f"Stop {s.get('sequence')}: unit {unit}")
        if s.get("notes"):
            bits.append(f"Stop {s.get('sequence')}: {s['notes']}")
    return " | ".join(bits) if bits else None


def _address_input(stop: dict[str, Any]) -> AddressInput:
    """The geocoded point, as the booking's pickup/dropoff and ``addresses`` row."""
    return AddressInput(
        formatted=stop.get("formatted") or stop.get("raw_address") or "",
        lat=stop.get("lat"),
        lng=stop.get("lng"),
        place_id=stop.get("place_id"),
        postal=stop.get("postal"),
    )


def attach_route_cargo(
    db: Session,
    order: Any,
    stops: list[dict[str, Any]],
    cfg: dict[str, Any],
    *,
    job_id: str | None = None,
) -> None:
    """Persist sequenced stops + parcels for Fleetbase without a parcels table."""
    compliance = dict(order.compliance_metadata or {})
    compliance["stops"] = [fleetbase_stop(stop) for stop in stops]
    if cfg.get("weight_kg") is not None:
        compliance["weight_kg"] = cfg.get("weight_kg")
    if cfg.get("dimensions"):
        compliance["dimensions"] = cfg.get("dimensions")
    if cfg.get("vehicle_class"):
        compliance["vehicle_class"] = cfg.get("vehicle_class")
    if job_id:
        compliance["route_import_job_id"] = job_id
    if cfg.get("quote"):
        compliance["quote"] = cfg.get("quote")
    if cfg.get("requires_liftgate") is not None:
        compliance["requires_liftgate"] = bool(cfg.get("requires_liftgate"))
    order.compliance_metadata = compliance
    db.add(order)
    db.commit()


def confirm_import(
    db: Session,
    settings: Settings,
    ctx: MerchantContext,
    job: BulkImportJob,
    booking: MerchantBookingService,
) -> BulkImportJob:
    if job.status == BulkImportStatus.CONFIRMED.value:
        return job

    cfg = dict(job.job_config or {})
    stops = list(cfg.get("stops") or [])
    if any(s.get("geocode_status") in {"failed", "pending"} for s in stops):
        raise ValueError("route_import_geocode_incomplete")
    if cfg.get("optimize_status") == "pending":
        raise ValueError("route_import_optimize_pending")
    if cfg.get("quote") is None:
        raise ValueError("route_import_quote_missing")

    pickup, dropoff, additional = split_stops(stops)
    scheduled_raw = cfg.get("scheduled_at")
    if scheduled_raw:
        try:
            scheduled = datetime.fromisoformat(str(scheduled_raw).replace("Z", "+00:00"))
        except ValueError:
            scheduled = datetime.now(UTC)
    else:
        scheduled = datetime.now(UTC)

    body = MerchantBookDeliveryRequest(
        pickup=_address_input(pickup),
        dropoff=_address_input(dropoff),
        additional_stops=[_address_input(s) for s in additional] or None,
        vehicle_class=persist_vehicle_class(cfg.get("vehicle_class")),
        package_type=cfg.get("package_type") or "looseParcel",
        weight_kg=optional_float(cfg.get("weight_kg")),
        dimensions=optional_text(cfg.get("dimensions")),
        requires_liftgate=bool(cfg.get("requires_liftgate")),
        site_access_notes=optional_text(cfg.get("site_access_notes")),
        scheduled_at=scheduled,
        internal_reference=cfg.get("internal_reference"),
        cost_centre=cfg.get("cost_centre"),
        special_instructions=driver_notes(stops),
    )
    order = booking.create_shipment(
        db,
        settings,
        ctx,
        body,
        order_source=OrderSource.CSV.value,
        sandbox=bool(cfg.get("is_sandbox")),
    )
    attach_route_cargo(db, order, stops, cfg, job_id=job.id)
    # Cargo lands after create_shipment's first package sync — rewrite from the rich stops.
    from porterchain_api.merchant_engine.package_service import PackageService

    PackageService().sync_from_order(db, order)
    db.commit()
    db.refresh(order)

    job.status = BulkImportStatus.CONFIRMED.value
    job.order_ids = [order.id]
    cfg["order_id"] = order.id
    job.job_config = cfg
    db.commit()
    db.refresh(job)

    mapping = list(cfg.get("mapping") or [])
    headers = list(cfg.get("headers") or [])
    if mapping and headers and not cfg.get("mapping_profile_id"):
        try:
            entry = save_profile(
                db,
                ctx.merchant,
                name=f"Auto · {job.filename}"[:120],
                headers=headers,
                mapping=mapping,
            )
            cfg["mapping_profile_id"] = entry.get("id")
            job.job_config = cfg
            db.commit()
            db.refresh(job)
        except Exception:  # noqa: BLE001
            logger.debug("auto-save mapping profile skipped", exc_info=True)

    return job
