"""HTTP-shaped list and job payloads for merchant route import."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.domain.merchant_states import BulkImportStatus
from porterchain_api.merchant_engine.import_errors import normalize_route_errors
from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_api.merchant_models import BulkImportJob

SCHEMA_VERSION = "route_import.v1"
KIND_ROUTE_V1 = "route_v1"


def list_item(job: BulkImportJob) -> dict[str, Any]:
    cfg = job.job_config if isinstance(job.job_config, dict) else {}
    stops = list(cfg.get("stops") or job.preview or [])
    drops = [s for s in stops if isinstance(s, dict) and s.get("stop_type") != "pickup"]
    pickup = next((s for s in stops if isinstance(s, dict) and s.get("stop_type") == "pickup"), None)
    notes = str(cfg.get("site_access_notes") or "")
    scheduled = str(cfg.get("scheduled_at") or "")
    created = job.created_at.isoformat() if job.created_at else ""
    quote = cfg.get("quote") if isinstance(cfg.get("quote"), dict) else {}
    label = ""
    if pickup:
        label = str(pickup.get("formatted") or pickup.get("address") or pickup.get("city") or "")
    if drops:
        last = drops[-1]
        dest = str(last.get("formatted") or last.get("address") or last.get("city") or "")
        label = f"{label} → {dest}" if label else dest
    return {
        "job_id": job.id,
        "label": label or job.filename or job.id,
        "status": job.status,
        "vehicle_class": cfg.get("vehicle_class"),
        "stops": len(stops),
        "drops": len(drops),
        "amount_cents": quote.get("amount_cents"),
        "internal_reference": cfg.get("internal_reference"),
        "construction_site": "construction" in notes.lower() or "site" in notes.lower(),
        "created_on": created[:10] if created else "",
        "scheduled_on": scheduled[:10] if scheduled else "",
        "filename": job.filename,
    }


def list_jobs(
    db: Session,
    ctx: MerchantContext,
    *,
    on_date: str | None = None,
    construction: bool = False,
    vehicle_class: str | None = None,
    status: str | None = None,
    search: str | None = None,
) -> dict[str, Any]:
    rows = (
        db.query(BulkImportJob)
        .filter(
            BulkImportJob.merchant_id == ctx.merchant.id,
            BulkImportJob.kind == KIND_ROUTE_V1,
        )
        .order_by(BulkImportJob.created_at.desc())
        .limit(300)
        .all()
    )
    today = datetime.now(UTC).date().isoformat()
    summaries = [list_item(row) for row in rows]
    today_count = sum(1 for item in summaries if item["created_on"] == today)
    construction_count = sum(1 for item in summaries if item["construction_site"])
    filtered = summaries
    if on_date:
        filtered = [item for item in filtered if item["created_on"] == on_date or item["scheduled_on"] == on_date]
    if construction:
        filtered = [item for item in filtered if item["construction_site"]]
    if vehicle_class:
        filtered = [item for item in filtered if item["vehicle_class"] == vehicle_class]
    if status:
        filtered = [item for item in filtered if item["status"] == status]
    if search:
        needle = search.strip().lower()
        filtered = [
            item
            for item in filtered
            if needle in item["label"].lower() or needle in (item["internal_reference"] or "").lower()
        ]
    return {
        "total": len(summaries),
        "today": today_count,
        "construction": construction_count,
        "routes": filtered[:100],
    }


def job_payload(job: BulkImportJob, order: Any | None = None) -> dict[str, Any]:
    from porterchain_api.merchant_engine.parcel_amend_service import commercial_stops, parcel_amendable

    cfg = dict(job.job_config or {})
    quote = cfg.get("quote")
    if isinstance(quote, dict):
        from porterchain_api.merchant_engine.quote_snapshot import merchant_facing_quote

        geometry = quote.get("route_geometry")
        quote = merchant_facing_quote(quote) or {k: v for k, v in quote.items() if k != "routing_source"}
        if geometry and "route_geometry" not in (cfg or {}):
            cfg["route_geometry"] = cfg.get("route_geometry") or geometry
    stops = cfg.get("stops") or job.preview or []
    order_id = (job.order_ids or [None])[0]
    payload: dict[str, Any] = {
        "schema_version": cfg.get("schema_version") or SCHEMA_VERSION,
        "job_id": job.id,
        "status": job.status,
        "source": cfg.get("source"),
        "vehicle_class": cfg.get("vehicle_class"),
        "scheduled_at": cfg.get("scheduled_at"),
        "mapping": cfg.get("mapping") or [],
        "headers": cfg.get("headers") or [],
        "mapping_profile_id": cfg.get("mapping_profile_id"),
        "mapping_profile_name": cfg.get("mapping_profile_name"),
        "optimized": bool(cfg.get("optimized")),
        "optimize_status": cfg.get("optimize_status") or ("ready" if cfg.get("optimized") else "idle"),
        "stops": stops,
        "quote": quote,
        "route_geometry": cfg.get("route_geometry") or (cfg.get("quote") or {}).get("route_geometry"),
        "route_explanation": cfg.get("route_explanation"),
        "errors": normalize_route_errors(job.errors),
        "order_ids": job.order_ids or [],
        "order_id": order_id,
        "filename": job.filename,
        "total_rows": job.total_rows,
        "valid_rows": job.valid_rows,
        "error_rows": job.error_rows,
        "order_state": None,
        "assigned_driver_id": None,
        "parcel_amendable": job.status != BulkImportStatus.CONFIRMED.value,
        "geocode": (
            "pending"
            if any(isinstance(s, dict) and s.get("geocode_status") == "pending" for s in stops)
            else "ready"
        ),
    }
    if order is not None:
        cargo = commercial_stops(order)
        if cargo:
            payload["stops"] = cargo
        payload["order_state"] = order.state
        payload["assigned_driver_id"] = order.assigned_driver_id
        payload["parcel_amendable"] = parcel_amendable(order)
        payload["order_id"] = order.id
        if isinstance(quote, dict):
            payload["quote"] = {**quote, "amount_cents": order.amount_cents}
        elif order.amount_cents is not None:
            payload["quote"] = {"amount_cents": order.amount_cents}
    return payload
