"""Route import orchestration — ingest → map → quote → confirm.

Quote math lives in import_quote; Fleetbase stop payload in import_confirm;
worker apply_* in import_jobs. This module owns job CRUD and HTTP-shaped responses.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.config import Settings
from porterchain_api.domain.merchant_states import BulkImportStatus
from porterchain_api.merchant_engine.booking_service import MerchantBookingService
from porterchain_api.merchant_engine.import_column_mapper import (
    adapt_mapping_to_headers,
    apply_mapping,
    mapping_confidence_ok,
    mapping_to_dicts,
    suggest_mapping,
)
from porterchain_api.merchant_engine.import_confirm import confirm_import, driver_notes
from porterchain_api.merchant_engine.import_errors import (
    normalize_route_errors,
    route_import_error_message,
    route_row_error,
)
from porterchain_api.merchant_engine.import_geocode import geocode_stop
from porterchain_api.merchant_engine.import_ingest import parse_upload
from porterchain_api.merchant_engine.import_jobs import apply_geocode_job as _apply_geocode_job
from porterchain_api.merchant_engine.import_jobs import apply_optimize_job as _apply_optimize_job
from porterchain_api.merchant_engine.import_mapping_profiles import (
    find_matching_profile,
    get_profile,
    list_profiles,
)
from porterchain_api.merchant_engine.import_patch import (
    apply_mapping_profile as _apply_mapping_profile,
    patch_mapping as _patch_mapping,
    patch_stop as _patch_stop,
    save_mapping_profile as _save_mapping_profile,
)
from porterchain_api.merchant_engine.import_views import job_payload, list_jobs as _list_jobs
from porterchain_api.merchant_engine.import_quote import (
    explain_stops,
    geo_fields,
    quote_if_ready,
    resolve_stops,
    split_route_quote,
    split_stops,
)
from porterchain_api.merchant_engine.import_rows import (
    legacy_cargo_from_stops,
    rows_to_stops,
)
from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_api.merchant_engine.stop_cargo import fleetbase_stop
from porterchain_api.merchant_models import BulkImportJob

logger = logging.getLogger(__name__)

SCHEMA_VERSION = "route_import.v1"
KIND_ROUTE_V1 = "route_v1"

__all__ = [
    "KIND_ROUTE_V1",
    "MerchantRouteImportService",
    "SCHEMA_VERSION",
    "geocode_stop",
    "normalize_route_errors",
    "route_import_error_message",
    "route_row_error",
    "split_route_quote",
]


class MerchantRouteImportService:
    def __init__(self) -> None:
        self._booking = MerchantBookingService()

    def create_from_json(
        self,
        db: Session,
        ctx: MerchantContext,
        body: dict[str, Any],
    ) -> BulkImportJob:
        idem = (body.get("idempotency_key") or "").strip() or None
        if idem:
            existing = self._find_by_idempotency(db, ctx.merchant.id, idem)
            if existing is not None:
                return existing

        vehicle_class = body.get("vehicle_class") or "cargoVan"
        scheduled_at = body.get("scheduled_at")
        stops_in = list(body.get("stops") or [])
        if len(stops_in) < 2:
            raise ValueError("route_import_needs_two_stops")

        resolved, errors = self._resolve_stops(stops_in)
        quote, geometry = split_route_quote(
            self._quote_if_ready(
                db,
                ctx,
                vehicle_class,
                scheduled_at,
                resolved,
                requires_liftgate=bool(body.get("requires_liftgate")),
            )
        )

        job_config = {
            "schema_version": SCHEMA_VERSION,
            "source": body.get("source") or "api",
            "idempotency_key": body.get("idempotency_key"),
            "vehicle_class": vehicle_class,
            "scheduled_at": scheduled_at,
            "package_type": body.get("package_type") or "looseParcel",
            "internal_reference": body.get("internal_reference"),
            "cost_centre": body.get("cost_centre"),
            "weight_kg": body.get("weight_kg"),
            "dimensions": body.get("dimensions"),
            "requires_liftgate": bool(body.get("requires_liftgate")),
            "site_access_notes": body.get("site_access_notes"),
            "mapping": [],
            "route_explanation": self._explain(resolved),
            "quote": quote,
            "route_geometry": geometry,
            "stops": resolved,
        }
        job = self._persist_job(
            db,
            ctx,
            filename=body.get("filename") or "route-import.json",
            total_rows=len(stops_in),
            resolved=resolved,
            errors=errors,
            job_config=job_config,
        )
        self._enqueue_geocode(job.id, resolved)
        return job

    def create_from_file(
        self,
        db: Session,
        ctx: MerchantContext,
        *,
        filename: str,
        data: bytes,
        vehicle_class: str,
        scheduled_at: str | None,
        package_type: str = "looseParcel",
        requires_liftgate: bool = False,
        site_access_notes: str | None = None,
        mapping_profile_id: str | None = None,
    ) -> BulkImportJob:
        sheet = parse_upload(filename, data)
        if not sheet.rows:
            raise ValueError("route_import_empty_file")

        saved = None
        if mapping_profile_id:
            saved = get_profile(ctx.merchant, mapping_profile_id)
            if not saved:
                raise ValueError("mapping_profile_not_found")
        else:
            saved = find_matching_profile(ctx.merchant, sheet.headers)
        if saved and saved.get("mapping"):
            mapping_dicts = adapt_mapping_to_headers(list(saved["mapping"]), sheet.headers)
            mapped_rows = apply_mapping(sheet.rows, mapping_dicts)
            mapping_ok = mapping_confidence_ok(mapping_dicts)
            profile_applied = saved.get("id")
        else:
            mapping = suggest_mapping(sheet.headers)
            mapping_dicts = mapping_to_dicts(mapping)
            mapped_rows = apply_mapping(sheet.rows, mapping)
            mapping_ok = mapping_confidence_ok(mapping)
            profile_applied = None

        stops_in = self._rows_to_stops(mapped_rows)
        resolved: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []

        if not mapping_ok:
            errors.append(route_row_error(row=None, code="mapping.address_low_confidence"))
        else:
            if len(stops_in) < 2:
                raise ValueError("route_import_needs_two_stops")
            resolved, errors = self._resolve_stops(stops_in)

        quote, geometry = split_route_quote(
            self._quote_if_ready(
                db,
                ctx,
                vehicle_class,
                scheduled_at,
                resolved,
                requires_liftgate=requires_liftgate,
            )
            if resolved
            else None
        )
        weight_kg, dimensions = legacy_cargo_from_stops(resolved)

        job_config = {
            "schema_version": SCHEMA_VERSION,
            "source": "portal",
            "vehicle_class": vehicle_class,
            "scheduled_at": scheduled_at,
            "package_type": package_type,
            "weight_kg": weight_kg,
            "dimensions": dimensions,
            "requires_liftgate": requires_liftgate,
            "site_access_notes": site_access_notes,
            "headers": sheet.headers,
            "raw_rows": sheet.rows[:500],
            "mapping": mapping_dicts,
            "mapping_profile_id": profile_applied,
            "mapping_profile_name": (saved or {}).get("name") if profile_applied else None,
            "sheet_name": sheet.sheet_name,
            "route_explanation": self._explain(resolved) if resolved else None,
            "quote": quote,
            "stops": resolved,
            "route_geometry": geometry,
        }
        job = self._persist_job(
            db,
            ctx,
            filename=filename,
            total_rows=len(sheet.rows),
            resolved=resolved,
            errors=errors,
            job_config=job_config,
        )
        self._enqueue_geocode(job.id, resolved)
        return job

    def list_jobs(
        self,
        db: Session,
        ctx: MerchantContext,
        *,
        on_date: str | None = None,
        construction: bool = False,
        vehicle_class: str | None = None,
        status: str | None = None,
        search: str | None = None,
    ) -> dict[str, Any]:
        return _list_jobs(
            db,
            ctx,
            on_date=on_date,
            construction=construction,
            vehicle_class=vehicle_class,
            status=status,
            search=search,
        )

    def get_job(self, db: Session, ctx: MerchantContext, job_id: str) -> BulkImportJob:
        job = (
            db.query(BulkImportJob)
            .filter(
                BulkImportJob.id == job_id,
                BulkImportJob.merchant_id == ctx.merchant.id,
                BulkImportJob.kind == KIND_ROUTE_V1,
            )
            .first()
        )
        if not job:
            raise LookupError("route_import_not_found")
        return job

    def _assert_unconfirmed(self, job: BulkImportJob) -> None:
        if job.status == BulkImportStatus.CONFIRMED.value:
            raise ValueError("route_import_already_confirmed")

    def patch_mapping(
        self,
        db: Session,
        ctx: MerchantContext,
        job_id: str,
        mapping: list[dict[str, Any]],
    ) -> BulkImportJob:
        return _patch_mapping(self, db, ctx, job_id, mapping)

    def patch_stop(
        self,
        db: Session,
        ctx: MerchantContext,
        job_id: str,
        index: int,
        patch: dict[str, Any],
    ) -> BulkImportJob:
        return _patch_stop(self, db, ctx, job_id, index, patch)

    def optimize(self, db: Session, ctx: MerchantContext, job_id: str) -> BulkImportJob:
        """Accept the reorder request. NN + quote run in the worker, not this POST."""
        job = self.get_job(db, ctx, job_id)
        self._assert_unconfirmed(job)
        cfg = dict(job.job_config or {})
        stops = list(cfg.get("stops") or [])
        if any(s.get("geocode_status") in {"failed", "pending"} for s in stops):
            raise ValueError("route_import_geocode_incomplete")
        cfg["optimize_status"] = "pending"
        cfg["optimized"] = False
        job.job_config = cfg
        db.commit()
        db.refresh(job)
        self._enqueue_optimize(job.id)
        return job

    def save_mapping_profile(self, db: Session, ctx: MerchantContext, job_id: str, name: str) -> dict[str, Any]:
        return _save_mapping_profile(self, db, ctx, job_id, name)

    def list_mapping_profiles(self, ctx: MerchantContext) -> list[dict[str, Any]]:
        return list_profiles(ctx.merchant)

    def apply_mapping_profile(
        self, db: Session, ctx: MerchantContext, job_id: str, profile_id: str
    ) -> BulkImportJob:
        return _apply_mapping_profile(self, db, ctx, job_id, profile_id)

    def confirm(
        self, db: Session, settings: Settings, ctx: MerchantContext, job_id: str
    ) -> BulkImportJob:
        job = self.get_job(db, ctx, job_id)
        return confirm_import(db, settings, ctx, job, self._booking)

    def job_response(self, job: BulkImportJob, order: Any | None = None) -> dict[str, Any]:
        return job_payload(job, order)

    def _find_by_idempotency(self, db: Session, merchant_id: str, idempotency_key: str) -> BulkImportJob | None:
        rows = (
            db.query(BulkImportJob)
            .filter(BulkImportJob.merchant_id == merchant_id, BulkImportJob.kind == KIND_ROUTE_V1)
            .order_by(BulkImportJob.created_at.desc())
            .limit(50)
            .all()
        )
        for row in rows:
            cfg = row.job_config if isinstance(row.job_config, dict) else {}
            if cfg.get("idempotency_key") == idempotency_key:
                return row
        return None

    def _persist_job(
        self,
        db: Session,
        ctx: MerchantContext,
        *,
        filename: str,
        total_rows: int,
        resolved: list[dict[str, Any]],
        errors: list[dict[str, Any]],
        job_config: dict[str, Any],
    ) -> BulkImportJob:
        job = BulkImportJob(
            id=str(uuid.uuid4()),
            merchant_id=ctx.merchant.id,
            status=BulkImportStatus.PREVIEW.value,
            kind=KIND_ROUTE_V1,
            filename=filename,
            total_rows=total_rows,
            valid_rows=sum(1 for s in resolved if s.get("geocode_status") not in {"failed", "pending"}),
            error_rows=len(errors),
            duplicate_rows=0,
            preview=resolved,
            errors=normalize_route_errors(errors),
            order_ids=[],
            job_config=job_config,
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        return job

    def _enqueue_geocode(self, job_id: str, stops: list[dict[str, Any]] | None = None) -> None:
        if stops is not None and not any(s.get("geocode_status") == "pending" for s in stops):
            return
        try:
            from porterchain_api.fleetbase_engine.routing_jobs import enqueue_routing_job

            enqueue_routing_job({"action": "geocode_import", "job_id": job_id})
        except Exception as exc:  # noqa: BLE001
            logger.info("geocode_import enqueue failed: %s", exc)

    def _enqueue_optimize(self, job_id: str) -> None:
        try:
            from porterchain_api.fleetbase_engine.routing_jobs import enqueue_routing_job

            enqueue_routing_job({"action": "optimize_import", "job_id": job_id})
        except Exception as exc:  # noqa: BLE001
            logger.info("optimize_import enqueue failed: %s", exc)

    def apply_geocode_job(self, db: Session, job_id: str) -> None:
        _apply_geocode_job(db, job_id)

    def apply_optimize_job(self, db: Session, job_id: str) -> None:
        _apply_optimize_job(db, job_id)

    def _rows_to_stops(self, mapped_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return rows_to_stops(mapped_rows)

    def _resolve_stops(
        self, stops_in: list[dict[str, Any]], *, geocode_now: bool = False
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        return resolve_stops(stops_in, geocode_now=geocode_now)

    def _geo_fields(self, geo: Any, *, sequence: Any, stop_type: Any) -> dict[str, Any]:
        return geo_fields(geo, sequence=sequence, stop_type=stop_type)

    def _quote_if_ready(self, db: Session, ctx: MerchantContext, vehicle_class: str, scheduled_at: Any, stops: list[dict[str, Any]], *, requires_liftgate: bool = False) -> dict[str, Any] | None:
        return quote_if_ready(
            db, ctx, vehicle_class, scheduled_at, stops, requires_liftgate=requires_liftgate
        )

    def _split_stops(
        self, stops: list[dict[str, Any]]
    ) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
        return split_stops(stops)

    def _explain(self, stops: list[dict[str, Any]]) -> str:
        return explain_stops(stops)

    def _fleetbase_stop(self, stop: dict[str, Any]) -> dict[str, Any]:
        return fleetbase_stop(stop)

    def _driver_notes(self, stops: list[dict[str, Any]]) -> str | None:
        return driver_notes(stops)
