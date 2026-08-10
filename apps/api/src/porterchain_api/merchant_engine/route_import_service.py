"""Route import orchestration — ingest → map → Nominatim → Valhalla/GTA quote → confirm."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.config import Settings
from porterchain_api.domain.merchant_states import BulkImportStatus
from porterchain_api.domain.states import OrderSource
from porterchain_api.merchant_engine.address_normalize import compose_raw_from_parts
from porterchain_api.merchant_engine.booking_service import MerchantBookingService
from porterchain_api.merchant_engine.import_column_mapper import (
    apply_mapping,
    mapping_confidence_ok,
    mapping_to_dicts,
    suggest_mapping,
)
from porterchain_api.merchant_engine.import_geocode import geocode_stop
from porterchain_api.merchant_engine.import_ingest import parse_upload
from porterchain_api.merchant_engine.import_mapping_profiles import (
    find_matching_profile,
    list_profiles,
    save_profile,
)
from porterchain_api.merchant_engine.import_route_optimize import optimize_drop_order
from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_api.merchant_models import BulkImportJob
from porterchain_api.pricing_engine import get_pricing_service
from porterchain_api.schemas_merchant import AddressInput, MerchantBookDeliveryRequest
from porterchain_api.services.routing import resolve_route_distance
from porterchain_pricing import GeoPoint, PricingRequest
from porterchain_services.maps.route_helpers import multi_stop_route_from_valhalla
from porterchain_services.maps.service import MapsService

logger = logging.getLogger(__name__)

SCHEMA_VERSION = "route_import.v1"
KIND_ROUTE_V1 = "route_v1"


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
        quote = self._quote_if_ready(db, ctx, vehicle_class, scheduled_at, resolved)

        job_config = {
            "schema_version": SCHEMA_VERSION,
            "source": body.get("source") or "api",
            "idempotency_key": body.get("idempotency_key"),
            "vehicle_class": vehicle_class,
            "scheduled_at": scheduled_at,
            "package_type": body.get("package_type") or "looseParcel",
            "internal_reference": body.get("internal_reference"),
            "cost_centre": body.get("cost_centre"),
            "mapping": [],
            "route_explanation": self._explain(resolved),
            "quote": quote,
            "route_geometry": (quote or {}).get("route_geometry"),
            "stops": resolved,
        }
        return self._persist_job(
            db,
            ctx,
            filename=body.get("filename") or "route-import.json",
            total_rows=len(stops_in),
            resolved=resolved,
            errors=errors,
            job_config=job_config,
        )

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
    ) -> BulkImportJob:
        sheet = parse_upload(filename, data)
        if not sheet.rows:
            raise ValueError("route_import_empty_file")

        saved = find_matching_profile(ctx.merchant, sheet.headers)
        if saved and saved.get("mapping"):
            mapping_dicts = list(saved["mapping"])
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
            errors.append(
                {
                    "code": "mapping.address_low_confidence",
                    "message": "Could not confidently map an address column — review mapping",
                }
            )
        else:
            if len(stops_in) < 2:
                raise ValueError("route_import_needs_two_stops")
            resolved, errors = self._resolve_stops(stops_in)

        quote = self._quote_if_ready(db, ctx, vehicle_class, scheduled_at, resolved) if resolved else None

        job_config = {
            "schema_version": SCHEMA_VERSION,
            "source": "portal",
            "vehicle_class": vehicle_class,
            "scheduled_at": scheduled_at,
            "package_type": package_type,
            "headers": sheet.headers,
            "raw_rows": sheet.rows[:500],
            "mapping": mapping_dicts,
            "mapping_profile_id": profile_applied,
            "sheet_name": sheet.sheet_name,
            "route_explanation": self._explain(resolved) if resolved else None,
            "quote": quote,
            "stops": resolved,
            "route_geometry": (quote or {}).get("route_geometry"),
        }
        return self._persist_job(
            db,
            ctx,
            filename=filename,
            total_rows=len(sheet.rows),
            resolved=resolved,
            errors=errors,
            job_config=job_config,
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

    def patch_mapping(
        self,
        db: Session,
        ctx: MerchantContext,
        job_id: str,
        mapping: list[dict[str, Any]],
    ) -> BulkImportJob:
        job = self.get_job(db, ctx, job_id)
        cfg = dict(job.job_config or {})
        raw_rows = list(cfg.get("raw_rows") or [])
        if not raw_rows:
            raise ValueError("route_import_no_raw_rows")

        mapped_rows = apply_mapping(raw_rows, mapping)
        stops_in = self._rows_to_stops(mapped_rows)
        if len(stops_in) < 2:
            raise ValueError("route_import_needs_two_stops")

        resolved, errors = self._resolve_stops(stops_in)
        quote = self._quote_if_ready(
            db,
            ctx,
            cfg.get("vehicle_class") or "cargoVan",
            cfg.get("scheduled_at"),
            resolved,
        )
        cfg["mapping"] = mapping
        cfg["stops"] = resolved
        cfg["quote"] = quote
        cfg["route_explanation"] = self._explain(resolved)
        job.job_config = cfg
        job.preview = resolved
        job.errors = errors
        job.valid_rows = sum(1 for s in resolved if s.get("geocode_status") != "failed")
        job.error_rows = len(errors)
        job.status = BulkImportStatus.PREVIEW.value
        db.commit()
        db.refresh(job)
        return job

    def patch_stop(
        self,
        db: Session,
        ctx: MerchantContext,
        job_id: str,
        index: int,
        patch: dict[str, Any],
    ) -> BulkImportJob:
        job = self.get_job(db, ctx, job_id)
        cfg = dict(job.job_config or {})
        stops = list(cfg.get("stops") or [])
        if index < 0 or index >= len(stops):
            raise LookupError("route_import_stop_not_found")

        stop = dict(stops[index])
        stop.update({k: v for k, v in patch.items() if v is not None})
        geo = geocode_stop(
            address=str(stop.get("address") or stop.get("raw_address") or ""),
            unit=stop.get("unit"),
            city=stop.get("city"),
            province=stop.get("province"),
            postal=stop.get("postal"),
            lat=stop.get("lat"),
            lng=stop.get("lng"),
        )
        stop.update(self._geo_fields(geo, sequence=stop.get("sequence"), stop_type=stop.get("stop_type")))
        stops[index] = stop
        errors = [
            {"index": i, "codes": s.get("issues") or []}
            for i, s in enumerate(stops)
            if s.get("geocode_status") == "failed"
        ]
        quote = self._quote_if_ready(
            db,
            ctx,
            cfg.get("vehicle_class") or "cargoVan",
            cfg.get("scheduled_at"),
            stops,
        )
        cfg["stops"] = stops
        cfg["quote"] = quote
        cfg["route_explanation"] = self._explain(stops)
        job.job_config = cfg
        job.preview = stops
        job.errors = errors
        job.valid_rows = sum(1 for s in stops if s.get("geocode_status") != "failed")
        job.error_rows = len(errors)
        db.commit()
        db.refresh(job)
        return job

    def optimize(
        self,
        db: Session,
        ctx: MerchantContext,
        job_id: str,
    ) -> BulkImportJob:
        job = self.get_job(db, ctx, job_id)
        cfg = dict(job.job_config or {})
        stops = list(cfg.get("stops") or [])
        if any(s.get("geocode_status") == "failed" for s in stops):
            raise ValueError("route_import_geocode_incomplete")
        reordered = optimize_drop_order(stops)
        quote = self._quote_if_ready(
            db,
            ctx,
            cfg.get("vehicle_class") or "cargoVan",
            cfg.get("scheduled_at"),
            reordered,
        )
        cfg["stops"] = reordered
        cfg["quote"] = quote
        cfg["route_geometry"] = (quote or {}).get("route_geometry")
        cfg["route_explanation"] = (
            self._explain(reordered) + " Drop order optimized (nearest-neighbor + 2-opt)."
        )
        cfg["optimized"] = True
        job.job_config = cfg
        job.preview = reordered
        db.commit()
        db.refresh(job)
        return job

    def save_mapping_profile(
        self,
        db: Session,
        ctx: MerchantContext,
        job_id: str,
        name: str,
    ) -> dict[str, Any]:
        job = self.get_job(db, ctx, job_id)
        cfg = dict(job.job_config or {})
        mapping = list(cfg.get("mapping") or [])
        headers = list(cfg.get("headers") or [])
        if not mapping or not headers:
            raise ValueError("route_import_no_mapping_to_save")
        return save_profile(db, ctx.merchant, name=name, headers=headers, mapping=mapping)

    def list_mapping_profiles(self, ctx: MerchantContext) -> list[dict[str, Any]]:
        return list_profiles(ctx.merchant)

    def confirm(
        self,
        db: Session,
        settings: Settings,
        ctx: MerchantContext,
        job_id: str,
    ) -> BulkImportJob:
        job = self.get_job(db, ctx, job_id)
        if job.status == BulkImportStatus.CONFIRMED.value:
            return job

        cfg = dict(job.job_config or {})
        stops = list(cfg.get("stops") or [])
        if any(s.get("geocode_status") == "failed" for s in stops):
            raise ValueError("route_import_geocode_incomplete")
        if cfg.get("quote") is None:
            raise ValueError("route_import_quote_missing")

        pickup, dropoff, additional = self._split_stops(stops)
        scheduled_raw = cfg.get("scheduled_at")
        if scheduled_raw:
            try:
                scheduled = datetime.fromisoformat(str(scheduled_raw).replace("Z", "+00:00"))
            except ValueError:
                scheduled = datetime.now(UTC)
        else:
            scheduled = datetime.now(UTC)

        body = MerchantBookDeliveryRequest(
            pickup=AddressInput(
                formatted=pickup["formatted"] or pickup.get("raw_address") or "",
                lat=pickup.get("lat"),
                lng=pickup.get("lng"),
            ),
            dropoff=AddressInput(
                formatted=dropoff["formatted"] or dropoff.get("raw_address") or "",
                lat=dropoff.get("lat"),
                lng=dropoff.get("lng"),
            ),
            additional_stops=[
                AddressInput(
                    formatted=s.get("formatted") or s.get("raw_address") or "",
                    lat=s.get("lat"),
                    lng=s.get("lng"),
                )
                for s in additional
            ]
            or None,
            vehicle_class=cfg.get("vehicle_class") or "cargoVan",
            package_type=cfg.get("package_type") or "looseParcel",
            scheduled_at=scheduled,
            internal_reference=cfg.get("internal_reference"),
            cost_centre=cfg.get("cost_centre"),
            special_instructions=self._driver_notes(stops),
        )
        order = self._booking.create_shipment(
            db, settings, ctx, body, order_source=OrderSource.CSV.value
        )
        job.status = BulkImportStatus.CONFIRMED.value
        job.order_ids = [order.id]
        cfg["order_id"] = order.id
        job.job_config = cfg
        db.commit()
        db.refresh(job)

        # Persist successful column mapping for next upload with the same headers.
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

    def job_response(self, job: BulkImportJob) -> dict[str, Any]:
        cfg = dict(job.job_config or {})
        return {
            "schema_version": cfg.get("schema_version") or SCHEMA_VERSION,
            "job_id": job.id,
            "status": job.status,
            "source": cfg.get("source"),
            "vehicle_class": cfg.get("vehicle_class"),
            "scheduled_at": cfg.get("scheduled_at"),
            "mapping": cfg.get("mapping") or [],
            "headers": cfg.get("headers") or [],
            "mapping_profile_id": cfg.get("mapping_profile_id"),
            "optimized": bool(cfg.get("optimized")),
            "stops": cfg.get("stops") or job.preview or [],
            "quote": cfg.get("quote"),
            "route_geometry": cfg.get("route_geometry")
            or (cfg.get("quote") or {}).get("route_geometry"),
            "route_explanation": cfg.get("route_explanation"),
            "errors": job.errors or [],
            "order_ids": job.order_ids or [],
            "filename": job.filename,
            "total_rows": job.total_rows,
            "valid_rows": job.valid_rows,
            "error_rows": job.error_rows,
        }

    def _find_by_idempotency(
        self, db: Session, merchant_id: str, idempotency_key: str
    ) -> BulkImportJob | None:
        """Return newest route_v1 job with matching idempotency_key in job_config."""
        rows = (
            db.query(BulkImportJob)
            .filter(
                BulkImportJob.merchant_id == merchant_id,
                BulkImportJob.kind == KIND_ROUTE_V1,
            )
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
            valid_rows=sum(1 for s in resolved if s.get("geocode_status") != "failed"),
            error_rows=len(errors),
            duplicate_rows=0,
            preview=resolved,
            errors=errors,
            order_ids=[],
            job_config=job_config,
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        return job

    def _rows_to_stops(self, mapped_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        stops: list[dict[str, Any]] = []
        for i, row in enumerate(mapped_rows):
            address = compose_raw_from_parts(row)
            if not address:
                continue
            stop_type = str(row.get("stop_type") or "").strip().lower()
            if stop_type in ("pickup", "pick", "pu", "origin"):
                st = "pickup"
            elif stop_type in ("drop", "dropoff", "delivery", "do", "dest"):
                st = "drop"
            else:
                st = "pickup" if i == 0 else "drop"
            seq = row.get("sequence")
            try:
                sequence = int(seq) if seq not in (None, "") else i + 1
            except (TypeError, ValueError):
                sequence = i + 1
            lat = lng = None
            try:
                if row.get("lat") not in (None, ""):
                    lat = float(row["lat"])
                if row.get("lng") not in (None, ""):
                    lng = float(row["lng"])
            except (TypeError, ValueError):
                lat = lng = None
            stops.append(
                {
                    "sequence": sequence,
                    "stop_type": st,
                    "address": address,
                    "unit": row.get("unit"),
                    "city": row.get("city"),
                    "province": row.get("province"),
                    "postal": row.get("postal"),
                    "contact_name": row.get("contact_name"),
                    "contact_phone": row.get("contact_phone"),
                    "external_ref": row.get("external_ref"),
                    "notes": row.get("notes"),
                    "lat": lat,
                    "lng": lng,
                }
            )
        stops.sort(key=lambda s: int(s.get("sequence") or 0))
        # ensure exactly one pickup
        pickups = [s for s in stops if s["stop_type"] == "pickup"]
        if not pickups and stops:
            stops[0]["stop_type"] = "pickup"
        elif len(pickups) > 1:
            first = True
            for s in stops:
                if s["stop_type"] == "pickup":
                    if first:
                        first = False
                    else:
                        s["stop_type"] = "drop"
        return stops

    def _resolve_stops(
        self, stops_in: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        # normalize stop_type / sequence for API JSON
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
                    "address": s.get("address") or s.get("formatted") or "",
                }
            )
        normalized_in.sort(key=lambda x: int(x.get("sequence") or 0))

        resolved: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []
        for i, s in enumerate(normalized_in):
            geo = geocode_stop(
                address=str(s.get("address") or ""),
                unit=s.get("unit"),
                city=s.get("city"),
                province=s.get("province"),
                postal=s.get("postal"),
                lat=s.get("lat"),
                lng=s.get("lng"),
            )
            stop = {
                **self._geo_fields(geo, sequence=s.get("sequence"), stop_type=s.get("stop_type")),
                "contact_name": s.get("contact_name"),
                "contact_phone": s.get("contact_phone"),
                "external_ref": s.get("external_ref"),
                "notes": s.get("notes"),
            }
            resolved.append(stop)
            if geo.status == "failed":
                errors.append({"index": i, "codes": stop.get("issues") or ["stop.geocode_failed"]})
        return resolved, errors

    def _geo_fields(self, geo: Any, *, sequence: Any, stop_type: Any) -> dict[str, Any]:
        return {
            "sequence": sequence,
            "stop_type": stop_type,
            "raw_address": geo.raw,
            "address": geo.raw,
            "formatted": geo.formatted,
            "unit": geo.unit,
            "lat": geo.lat,
            "lng": geo.lng,
            "geocode_status": geo.status,
            "confidence": geo.confidence,
            "geocode_query": geo.geocode_query,
            "issues": list(geo.issues),
        }

    def _quote_if_ready(
        self,
        db: Session,
        ctx: MerchantContext,
        vehicle_class: str,
        scheduled_at: Any,
        stops: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        if not stops or any(s.get("geocode_status") == "failed" for s in stops):
            return None
        try:
            pickup, dropoff, additional = self._split_stops(stops)
        except ValueError:
            return None

        pickup_geo = GeoPoint(lat=pickup["lat"], lng=pickup["lng"], formatted=pickup.get("formatted"))
        dropoff_geo = GeoPoint(lat=dropoff["lat"], lng=dropoff["lng"], formatted=dropoff.get("formatted"))
        add_geo = [
            GeoPoint(lat=s["lat"], lng=s["lng"], formatted=s.get("formatted")) for s in additional
        ]
        distance, duration_seconds, routing_source = resolve_route_distance(
            pickup_geo, dropoff_geo, add_geo
        )
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
                # Prefer multi-waypoint Valhalla summary when available
                distance = int(route_geometry["distance_meters"])
                duration_seconds = int(route_geometry.get("duration_seconds") or 0) or duration_seconds
                routing_source = "valhalla"
        except Exception:  # noqa: BLE001
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
        )
        breakdown = get_pricing_service(db).calculate_merchant(request)
        return {
            "amount_cents": breakdown.final_cents,
            "subtotal_cents": breakdown.subtotal_cents,
            "tax_cents": breakdown.tax_cents,
            "currency": "CAD",
            "distance_meters": distance,
            "duration_seconds": duration_seconds,
            "routing_source": routing_source,
            "vehicle_class": vehicle_class,
            "total_pickups": 1,
            "total_drops": 1 + len(additional),
            "line_items": [
                {"code": li.code, "label": li.label, "amount_cents": li.amount_cents}
                for li in (breakdown.items or [])
            ],
            "route_geometry": route_geometry,
        }

    def _split_stops(
        self, stops: list[dict[str, Any]]
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

    def _explain(self, stops: list[dict[str, Any]]) -> str:
        n_pick = sum(1 for s in stops if s.get("stop_type") == "pickup")
        n_drop = sum(1 for s in stops if s.get("stop_type") == "drop")
        return f"{n_pick} pickup, {n_drop} drops ordered by sequence; geocoded via Nominatim; distance via Valhalla/OSRM."

    def _driver_notes(self, stops: list[dict[str, Any]]) -> str | None:
        bits: list[str] = []
        for s in stops:
            unit = s.get("unit")
            if unit:
                bits.append(f"Stop {s.get('sequence')}: unit {unit}")
            if s.get("notes"):
                bits.append(f"Stop {s.get('sequence')}: {s['notes']}")
        return " | ".join(bits) if bits else None
