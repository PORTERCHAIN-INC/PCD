"""Mapping and stop patches for an unconfirmed route-import job."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.domain.customer_goods import persist_vehicle_class
from porterchain_api.domain.merchant_states import BulkImportStatus
from porterchain_api.merchant_engine.import_column_mapper import (
    adapt_mapping_to_headers,
    apply_mapping,
)
from porterchain_api.merchant_engine.import_errors import (
    route_row_error,
    stop_sheet_row,
)
from porterchain_api.merchant_engine.import_geocode import geocode_stop
from porterchain_api.merchant_engine.import_mapping_profiles import (
    get_profile,
    save_profile,
)
from porterchain_api.merchant_engine.import_quote import split_route_quote
from porterchain_api.merchant_engine.import_rows import (
    packages_clean,
    write_legacy_cargo_cfg,
)
from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_api.merchant_models import BulkImportJob


def patch_mapping(
    svc: Any,
    db: Session,
    ctx: MerchantContext,
    job_id: str,
    mapping: list[dict[str, Any]],
) -> BulkImportJob:
    job = svc.get_job(db, ctx, job_id)
    svc._assert_unconfirmed(job)
    cfg = dict(job.job_config or {})
    raw_rows = list(cfg.get("raw_rows") or [])
    if not raw_rows:
        raise ValueError("route_import_no_raw_rows")

    mapped_rows = apply_mapping(raw_rows, mapping)
    stops_in = svc._rows_to_stops(mapped_rows)
    if len(stops_in) < 2:
        raise ValueError("route_import_needs_two_stops")

    resolved, errors = svc._resolve_stops(stops_in)
    quote, geometry = split_route_quote(
        svc._quote_if_ready(
            db,
            ctx,
            persist_vehicle_class(cfg.get("vehicle_class")),
            cfg.get("scheduled_at"),
            resolved,
            requires_liftgate=bool(cfg.get("requires_liftgate")),
        )
    )
    cfg["mapping"] = mapping
    cfg["stops"] = resolved
    write_legacy_cargo_cfg(cfg, resolved)
    cfg["quote"] = quote
    if geometry is not None:
        cfg["route_geometry"] = geometry
    cfg["route_explanation"] = svc._explain(resolved)
    job.job_config = cfg
    job.preview = resolved
    job.errors = errors
    job.valid_rows = sum(1 for s in resolved if s.get("geocode_status") not in {"failed", "pending"})
    job.error_rows = len(errors)
    job.status = BulkImportStatus.PREVIEW.value
    db.commit()
    db.refresh(job)
    svc._enqueue_geocode(job.id, resolved)
    return job


def patch_stop(
    svc: Any,
    db: Session,
    ctx: MerchantContext,
    job_id: str,
    index: int,
    patch: dict[str, Any],
) -> BulkImportJob:
    job = svc.get_job(db, ctx, job_id)
    svc._assert_unconfirmed(job)
    cfg = dict(job.job_config or {})
    stops = list(cfg.get("stops") or [])
    if index < 0 or index >= len(stops):
        raise LookupError("route_import_stop_not_found")

    stop = dict(stops[index])
    packages = patch.get("packages")
    new_address = patch.get("address")
    address_changed = new_address is not None and str(new_address).strip() != str(
        stop.get("address") or stop.get("raw_address") or ""
    ).strip()
    if address_changed and (patch.get("lat") is None or patch.get("lng") is None):
        # The old pin belongs to the old address.
        for key in ("lat", "lng", "place_id", "geocode_source"):
            stop[key] = None
    stop.update({k: v for k, v in patch.items() if v is not None and k != "packages"})
    if packages is not None:
        stop["packages"] = packages_clean(packages)
    has_coords = stop.get("lat") is not None and stop.get("lng") is not None
    if has_coords:
        geo = geocode_stop(
            address=str(stop.get("address") or stop.get("raw_address") or ""),
            unit=stop.get("unit"),
            city=stop.get("city"),
            province=stop.get("province"),
            postal=stop.get("postal"),
            lat=stop.get("lat"),
            lng=stop.get("lng"),
            place_id=stop.get("place_id"),
            source=stop.get("geocode_source"),
        )
        stop.update(svc._geo_fields(geo, sequence=stop.get("sequence"), stop_type=stop.get("stop_type")))
        if geo.postal:
            stop["postal"] = geo.postal
        if geo.city:
            stop["city"] = geo.city
    else:
        stop["geocode_status"] = "pending"
        stop["lat"] = None
        stop["lng"] = None
    stops[index] = stop
    errors = []
    for i, s in enumerate(stops):
        if s.get("geocode_status") != "failed":
            continue
        codes = s.get("issues") or ["stop.geocode_failed"]
        row = stop_sheet_row(s, i)
        for code in codes:
            errors.append(route_row_error(row=row, code=str(code)))
    quote, geometry = split_route_quote(
        svc._quote_if_ready(
            db,
            ctx,
            persist_vehicle_class(cfg.get("vehicle_class")),
            cfg.get("scheduled_at"),
            stops,
            requires_liftgate=bool(cfg.get("requires_liftgate")),
        )
    )
    cfg["stops"] = stops
    cfg["quote"] = quote
    if geometry is not None:
        cfg["route_geometry"] = geometry
    cfg["route_explanation"] = svc._explain(stops)
    job.job_config = cfg
    job.preview = stops
    job.errors = errors
    job.valid_rows = sum(1 for s in stops if s.get("geocode_status") not in {"failed", "pending"})
    job.error_rows = len(errors)
    db.commit()
    db.refresh(job)
    svc._enqueue_geocode(job.id, stops)
    return job


def save_mapping_profile(svc: Any, db: Session, ctx: MerchantContext, job_id: str, name: str) -> dict[str, Any]:
    job = svc.get_job(db, ctx, job_id)
    cfg = dict(job.job_config or {})
    mapping = list(cfg.get("mapping") or [])
    headers = list(cfg.get("headers") or [])
    if not mapping or not headers:
        raise ValueError("route_import_no_mapping_to_save")
    entry = save_profile(db, ctx.merchant, name=name, headers=headers, mapping=mapping)
    cfg["mapping_profile_id"] = entry.get("id")
    cfg["mapping_profile_name"] = entry.get("name")
    job.job_config = cfg
    db.commit()
    db.refresh(job)
    return entry


def apply_mapping_profile(svc: Any, db: Session, ctx: MerchantContext, job_id: str, profile_id: str) -> BulkImportJob:
    profile = get_profile(ctx.merchant, profile_id)
    if not profile or not profile.get("mapping"):
        raise LookupError("mapping_profile_not_found")
    job = svc.get_job(db, ctx, job_id)
    cfg = dict(job.job_config or {})
    headers = list(cfg.get("headers") or [])
    mapping = adapt_mapping_to_headers(list(profile["mapping"]), headers)
    job = svc.patch_mapping(db, ctx, job_id, mapping)
    cfg = dict(job.job_config or {})
    cfg["mapping_profile_id"] = profile.get("id")
    cfg["mapping_profile_name"] = profile.get("name")
    job.job_config = cfg
    db.commit()
    db.refresh(job)
    return job
