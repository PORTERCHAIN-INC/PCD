"""Worker apply_* for route-import geocode and drop-order optimize."""

from __future__ import annotations

from sqlalchemy.orm import Session

from porterchain_api.domain.merchant_states import BulkImportStatus, MerchantRole
from porterchain_api.merchant_engine.import_errors import normalize_route_errors
from porterchain_api.merchant_engine.import_quote import (
    explain_stops,
    quote_if_ready,
    resolve_stops,
    split_route_quote,
)
from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_api.merchant_models import BulkImportJob, Merchant, MerchantUser
from porterchain_services.maps.sequence import optimize_drop_order_with_source


def _owner_ctx(db: Session, job: BulkImportJob) -> MerchantContext | None:
    merchant = db.get(Merchant, job.merchant_id)
    if not merchant:
        return None
    user = db.query(MerchantUser).filter(MerchantUser.merchant_id == merchant.id).first()
    return MerchantContext(merchant=merchant, user=user, role=MerchantRole.OWNER)


def apply_geocode_job(db: Session, job_id: str) -> None:
    """Worker: Nominatim (with throttle) + quote after the request returned pending."""
    job = db.get(BulkImportJob, job_id)
    if not job or job.status == BulkImportStatus.CONFIRMED.value:
        return
    ctx = _owner_ctx(db, job)
    if not ctx:
        return
    cfg = dict(job.job_config or {})
    stops_in = list(cfg.get("stops") or job.preview or [])
    resolved, errors = resolve_stops(stops_in, geocode_now=True)
    quote, geometry = split_route_quote(
        quote_if_ready(
            db,
            ctx,
            cfg.get("vehicle_class") or "cargoVan",
            cfg.get("scheduled_at"),
            resolved,
            requires_liftgate=bool(cfg.get("requires_liftgate")),
        )
    )
    cfg["stops"] = resolved
    cfg["quote"] = quote
    if geometry is not None:
        cfg["route_geometry"] = geometry
    cfg["route_explanation"] = explain_stops(resolved)
    job.job_config = cfg
    job.preview = resolved
    job.errors = normalize_route_errors(errors)
    job.valid_rows = sum(1 for s in resolved if s.get("geocode_status") not in {"failed", "pending"})
    job.error_rows = len(errors)
    db.commit()


def apply_optimize_job(db: Session, job_id: str) -> None:
    """Worker: one Valhalla/OSRM matrix + labeled NN, then quote. Not 2-opt."""
    job = db.get(BulkImportJob, job_id)
    if not job or job.status == BulkImportStatus.CONFIRMED.value:
        return
    ctx = _owner_ctx(db, job)
    if not ctx:
        return
    cfg = dict(job.job_config or {})
    stops = list(cfg.get("stops") or job.preview or [])
    if any(s.get("geocode_status") in {"failed", "pending"} for s in stops):
        cfg["optimize_status"] = "error"
        cfg["route_explanation"] = explain_stops(stops) + " Drop order skipped — geocode incomplete."
        job.job_config = cfg
        db.commit()
        return
    reordered, optimize_source = optimize_drop_order_with_source(stops)
    quote, geometry = split_route_quote(
        quote_if_ready(
            db,
            ctx,
            cfg.get("vehicle_class") or "cargoVan",
            cfg.get("scheduled_at"),
            reordered,
            requires_liftgate=bool(cfg.get("requires_liftgate")),
        )
    )
    cfg["stops"] = reordered
    cfg["quote"] = quote
    cfg["route_geometry"] = geometry
    cfg["optimize_source"] = optimize_source
    cfg["optimize_status"] = "ready"
    cfg["optimized"] = True
    cfg["route_explanation"] = (
        explain_stops(reordered)
        + f" Drop order updated (nearest-neighbor, source={optimize_source})."
        + " Not Fleetbase VROOM — merchant route-import UX only."
    )
    job.job_config = cfg
    job.preview = reordered
    db.commit()
