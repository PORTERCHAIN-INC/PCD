"""Control Tower Optimize — wrap Fleetbase orchestrator for PC order ids.

Maps Porterchain queue orders → fleetbase_order_id, runs allocate/optimize,
and commits assignment plans (creates Fleetbase manifests). Never rebuilds
sequencing engines locally.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from porterchain_api.admin_models import Driver, Vehicle
from porterchain_api.config import get_settings
from porterchain_api.domain.admin_states import DriverStatus
from porterchain_api.fleetbase_engine.optimize_run_store import (
    STATUS_ERROR,
    STATUS_PENDING,
    STATUS_READY,
    enqueue_optimize_job,
    read_optimize_run,
    write_optimize_run,
)
from porterchain_api.fleetbase_engine.public_ids import is_consumable_public_id
from porterchain_api.booking_models import Order
from porterchain_api.services.fleetbase_integration import get_fleetbase_integration
import porterchain_api.user_models as _user_models  # noqa: F401 — Driver.porterchain_user_id FK

logger = logging.getLogger(__name__)

COMMIT_CACHE_KEY = "porterchain:optimize_commit:{run_id}"
COMMIT_CACHE_TTL_SECONDS = 24 * 60 * 60


def _read_commit_cache(run_id: str) -> dict[str, Any] | None:
    try:
        import json

        from porterchain_shared.redis_client import get_redis_client

        raw = get_redis_client().get(COMMIT_CACHE_KEY.format(run_id=run_id))
        if not raw:
            return None
        data = json.loads(raw)
        return data if isinstance(data, dict) else None
    except Exception as exc:  # noqa: BLE001
        logger.debug("optimize commit cache read failed: %s", exc)
        return None


def _write_commit_cache(run_id: str, payload: dict[str, Any]) -> None:
    try:
        import json

        from porterchain_shared.redis_client import get_redis_client

        get_redis_client().setex(
            COMMIT_CACHE_KEY.format(run_id=run_id),
            COMMIT_CACHE_TTL_SECONDS,
            json.dumps(payload),
        )
    except Exception as exc:  # noqa: BLE001
        logger.debug("optimize commit cache write failed: %s", exc)


# Unassigned / retryable pool eligible for Optimize.
OPTIMIZE_STATES = frozenset(
    {"BOOKED", "DISPATCH_READY", "DRIVER_REJECTED", "FAILED", "DRIVER_ASSIGNED", "DRIVER_ACCEPTED"}
)
# Preview cap — do not dump the whole queue into VROOM on one click.
PREVIEW_ORDER_CAP = 20


class OrchestratorOpsService:
    def pool(self, db: Session, *, limit: int = 100, offset: int = 0) -> dict[str, Any]:
        from porterchain_api.admin_engine.optimize_pool import build_optimize_pool

        vehicle_ids, driver_ids = self._synced_fleet(db)
        return build_optimize_pool(
            db,
            limit=limit,
            offset=offset,
            vehicle_ids=vehicle_ids,
            driver_ids=driver_ids,
            is_live_id=is_consumable_public_id,
        )

    def _shape_order_ids(
        self,
        db: Session,
        *,
        shape: str,
        order_ids: list[str] | None,
        merchant_id: str | None,
        offset: int = 0,
    ) -> list[str] | None:
        """Filter order ids for merchant-wise / fleet shaping (Fleetbase input only)."""
        if order_ids:
            base = list(order_ids)
        else:
            pool = self.pool(db, limit=PREVIEW_ORDER_CAP, offset=offset)
            base = [row["id"] for row in pool["orders"] if row.get("id")]
        if shape != "merchant" or not merchant_id:
            return base or None
        orders = db.query(Order).filter(Order.id.in_(base)).all() if base else []
        shaped = [o.id for o in orders if o.merchant_id == merchant_id]
        return shaped or None

    def _synced_fleet(self, db: Session) -> tuple[list[str], list[str]]:
        """Fleetbase vehicle/driver ids already linked on PC rows."""
        vehicles = (
            db.query(Vehicle)
            .filter(Vehicle.is_active.is_(True), Vehicle.fleetbase_vehicle_id.isnot(None))
            .all()
        )
        vehicle_ids = [
            v.fleetbase_vehicle_id
            for v in vehicles
            if is_consumable_public_id(v.fleetbase_vehicle_id)
        ]
        drivers = (
            db.query(Driver)
            .filter(
                Driver.status == DriverStatus.APPROVED.value,
                Driver.fleetbase_driver_id.isnot(None),
            )
            .all()
        )
        driver_ids = [
            d.fleetbase_driver_id
            for d in drivers
            if is_consumable_public_id(d.fleetbase_driver_id)
        ]
        return vehicle_ids, driver_ids

    def _resolve_fleetbase_ids(
        self, db: Session, order_ids: list[str] | None
    ) -> tuple[list[str], dict[str, str], list[str]]:
        """Return (fleetbase_ids, fb→pc map, missing_pc_ids)."""
        if order_ids:
            orders = db.query(Order).filter(Order.id.in_(order_ids)).all()
        else:
            pool = self.pool(db, limit=PREVIEW_ORDER_CAP)
            orders = [
                db.get(Order, row["id"])
                for row in pool["orders"]
                if row.get("id")
            ]
            orders = [o for o in orders if o]

        fb_ids: list[str] = []
        fb_to_pc: dict[str, str] = {}
        missing: list[str] = []
        for o in orders:
            if not o:
                continue
            if not is_consumable_public_id(o.fleetbase_order_id):
                missing.append(o.id)
                continue
            fb_ids.append(o.fleetbase_order_id)
            fb_to_pc[o.fleetbase_order_id] = o.id
        if not order_ids:
            fb_ids = fb_ids[:PREVIEW_ORDER_CAP]
        return fb_ids, fb_to_pc, missing

    def enqueue_run(
        self,
        db: Session,
        *,
        order_ids: list[str] | None = None,
        mode: str = "allocate",
        engine: str | None = "vroom",  # fleetbase-first:ok — Fleetbase orchestrator engine id
        vehicle_ids: list[str] | None = None,
        driver_ids: list[str] | None = None,
        shape: str = "fleet",
        merchant_id: str | None = None,
        prior_assignments: list[dict[str, Any]] | None = None,
        pc_driver_id: str | None = None,
        apply_on_ready: bool = True,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Accept a preview request. Fleetbase HTTP runs in the worker only.

        Optional ``vehicle_ids`` / ``driver_ids`` lock scope (driver optimize).
        ``shape=merchant`` filters to one merchant's synced orders.
        ``prior_assignments`` locks already-assigned orders for post-pickup reopt.
        ``pc_driver_id`` scopes the run to a PorterChain driver.
        ``apply_on_ready`` (default True) writes the sequence when the worker
        finishes — set False for driver Preview→Accept UX.
        """
        shaped_orders = self._shape_order_ids(
            db, shape=shape, order_ids=order_ids, merchant_id=merchant_id, offset=offset
        )
        fb_ids, _fb_to_pc, missing = self._resolve_fleetbase_ids(db, shaped_orders)
        if not fb_ids:
            return {
                "ok": False,
                "status": STATUS_ERROR,
                "error": "no_synced_orders",
                "message": (
                    "No orders with a live Fleetbase id in the optimize pool. "
                    "Placeholder ids like fb-123 are skipped."
                ),
                "missing_sync": missing,
                "assignments": [],
                "unassigned": [],
                "metrics": {},
            }
        fleet_vehicle_ids, fleet_driver_ids = self._synced_fleet(db)
        if shape == "vehicle":
            if not vehicle_ids:
                return {
                    "ok": False,
                    "status": STATUS_ERROR,
                    "error": "vehicle_shape_requires_vehicle_ids",
                    "message": "Vehicle-wise optimize needs at least one synced Fleetbase vehicle id.",
                    "missing_sync": missing,
                    "assignments": [],
                    "unassigned": [],
                    "metrics": {},
                }
            scoped_vehicles = [v for v in vehicle_ids if is_consumable_public_id(v)]
        else:
            scoped_vehicles = (
                [v for v in vehicle_ids if is_consumable_public_id(v)]
                if vehicle_ids is not None
                else fleet_vehicle_ids
            )
        scoped_drivers = (
            [d for d in driver_ids if is_consumable_public_id(d)]
            if driver_ids is not None
            else fleet_driver_ids
        )
        if not scoped_vehicles:
            return {
                "ok": False,
                "status": STATUS_ERROR,
                "error": "no_synced_vehicles",
                "message": (
                    "No vehicles synced to Fleetbase. Attach a cargo van to an "
                    "approved driver and wait for Fleetbase sync."
                ),
                "missing_sync": missing,
                "assignments": [],
                "unassigned": [],
                "metrics": {},
            }

        run_id = str(uuid4())
        pending: dict[str, Any] = {
            "run_id": run_id,
            "status": STATUS_PENDING,
            "ok": True,
            "mode": mode,
            "engine": engine,
            "shape": shape,
            "merchant_id": merchant_id,
            "order_ids": list(shaped_orders) if shaped_orders else None,
            "vehicle_ids": scoped_vehicles,
            "driver_ids": scoped_drivers,
            "prior_assignments": list(prior_assignments) if prior_assignments else None,
            "pc_driver_id": pc_driver_id,
            "apply_on_ready": bool(apply_on_ready),
            "missing_sync": missing,
            "assignments": [],
            "unassigned": [],
            "metrics": {},
            "queued_at": datetime.now(UTC).isoformat(),
        }
        try:
            write_optimize_run(run_id, pending)
            enqueue_optimize_job(run_id)
            if not pc_driver_id:
                from porterchain_api.fleetbase_engine.optimize_run_store import mark_fleet_optimize_open

                mark_fleet_optimize_open()
            from porterchain_api.fleetbase_engine.optimize_events import emit_enqueued

            emit_enqueued(
                run_id,
                engine=engine or "vroom",  # fleetbase-first:ok — passthrough to Fleetbase
                shape=shape,
                order_count=len(fb_ids),
                pc_driver_id=pc_driver_id,
            )
        except Exception as exc:
            logger.warning("optimize enqueue failed: %s", exc)
            pending = {
                **pending,
                "status": STATUS_ERROR,
                "ok": False,
                "error": "optimize_enqueue_failed",
                "message": "Could not queue the preview. Try again.",
            }
            try:
                write_optimize_run(run_id, pending)
            except Exception:
                logger.debug("optimize enqueue error-store failed", exc_info=True)
            from porterchain_api.fleetbase_engine.optimize_events import emit_rejected

            emit_rejected(run_id, error="optimize_enqueue_failed")
        return pending

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        return read_optimize_run(run_id)

    def execute_queued_run(self, db: Session, run_id: str) -> dict[str, Any]:
        """Worker only — Fleetbase orchestrator HTTP."""
        rec = read_optimize_run(run_id)
        if not rec:
            return {"ok": False, "status": STATUS_ERROR, "error": "run_not_found", "assignments": []}
        if rec.get("status") != STATUS_PENDING:
            return rec
        result = self.run(
            db,
            order_ids=rec.get("order_ids"),
            mode=str(rec.get("mode") or "allocate"),
            engine=rec.get("engine") or "vroom",  # fleetbase-first:ok — passthrough to Fleetbase
            vehicle_ids=rec.get("vehicle_ids"),
            driver_ids=rec.get("driver_ids"),
            prior_assignments=rec.get("prior_assignments"),
        )
        status = STATUS_READY if result.get("ok") else STATUS_ERROR
        merged = {**rec, **result, "run_id": run_id, "status": status}
        if status == STATUS_READY:
            try:
                from porterchain_api.intelligence_engine.cuopt_shadow import (
                    cuopt_shadow_enabled,
                    run_cuopt_shadow,
                )

                if cuopt_shadow_enabled():
                    shadow = run_cuopt_shadow(
                        db,
                        order_ids=list(rec.get("order_ids") or result.get("order_ids") or []),
                        vroom_metrics=merged.get("metrics")  # fleetbase-first:ok — compare-only shadow input
                        if isinstance(merged.get("metrics"), dict)
                        else {},
                        vehicle_count=len(merged.get("vehicle_ids") or []) or 1,
                    )
                    metrics = dict(merged.get("metrics") or {})
                    metrics["cuopt_shadow"] = shadow
                    merged["metrics"] = metrics
            except Exception as exc:  # noqa: BLE001 — shadow must never fail the run
                logger.warning("cuOpt shadow failed run_id=%s: %s", run_id, exc)
                metrics = dict(merged.get("metrics") or {})
                metrics["cuopt_shadow"] = {
                    "status": "error",
                    "reason": str(exc)[:200],
                    "commit_sot": "fleetbase_vroom",  # fleetbase-first:ok — label only
                }
                merged["metrics"] = metrics
        try:
            write_optimize_run(run_id, merged)
        except Exception as exc:
            logger.warning("optimize result store failed: %s", exc)
        pc_driver_id = merged.get("pc_driver_id") or rec.get("pc_driver_id")
        if not pc_driver_id:
            from porterchain_api.fleetbase_engine.optimize_run_store import clear_fleet_optimize_open

            clear_fleet_optimize_open()
        if status == STATUS_READY:
            from porterchain_api.fleetbase_engine.optimize_events import emit_ready

            emit_ready(
                run_id,
                engine=merged.get("engine") or "vroom",  # fleetbase-first:ok — passthrough to Fleetbase
                assignment_count=len(merged.get("assignments") or []),
                unassigned_count=len(merged.get("unassigned") or []),
            )
            if pc_driver_id:
                apply_flag = merged.get("apply_on_ready")
                if apply_flag is None:
                    apply_flag = True
                if apply_flag:
                    try:
                        from porterchain_api.fleetbase_engine.optimize_events import emit_applied
                        from porterchain_driver.sequence_store import apply_run_to_driver

                        waypoints = apply_run_to_driver(str(pc_driver_id), merged)
                        if waypoints:
                            emit_applied(
                                run_id,
                                pc_driver_id=str(pc_driver_id),
                                waypoint_count=len(waypoints),
                            )
                    except Exception as exc:  # noqa: BLE001 — sequence apply must not fail the run
                        logger.warning("driver sequence apply failed run_id=%s: %s", run_id, exc)
        else:
            from porterchain_api.fleetbase_engine.optimize_events import emit_rejected

            emit_rejected(
                run_id,
                error=merged.get("error") or "optimize_failed",
                message=str(merged.get("message") or "")[:200],
            )
        return merged

    def run(
        self,
        db: Session,
        *,
        order_ids: list[str] | None = None,
        mode: str = "allocate",
        engine: str | None = "vroom",  # fleetbase-first:ok — Fleetbase orchestrator engine id
        vehicle_ids: list[str] | None = None,
        driver_ids: list[str] | None = None,
        prior_assignments: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Call Fleetbase orchestrator. Worker / execute_queued_run only — not HTTP handlers."""
        fb_ids, fb_to_pc, missing = self._resolve_fleetbase_ids(db, order_ids)
        if not fb_ids:
            return {
                "ok": False,
                "error": "no_synced_orders",
                "message": (
                    "No orders with a live Fleetbase id in the optimize pool. "
                    "Placeholder ids like fb-123 are skipped."
                ),
                "missing_sync": missing,
                "assignments": [],
                "metrics": {},
            }

        fleet_vehicle_ids, fleet_driver_ids = self._synced_fleet(db)
        scoped_vehicles = (
            [v for v in vehicle_ids if is_consumable_public_id(v)]
            if vehicle_ids is not None
            else fleet_vehicle_ids
        )
        scoped_drivers = (
            [d for d in driver_ids if is_consumable_public_id(d)]
            if driver_ids is not None
            else fleet_driver_ids
        )
        if not scoped_vehicles:
            return {
                "ok": False,
                "error": "no_synced_vehicles",
                "message": (
                    "No vehicles synced to Fleetbase. Attach a cargo van to an "
                    "approved driver and wait for Fleetbase sync."
                ),
                "missing_sync": missing,
                "assignments": [],
                "metrics": {},
            }

        # prior_assignments use Fleetbase order public_ids (adapter contract).
        priors = [
            {
                "order_id": row.get("order_id"),
                "vehicle_id": row.get("vehicle_id"),
                "driver_id": row.get("driver_id"),
            }
            for row in (prior_assignments or [])
            if isinstance(row, dict) and row.get("order_id")
        ]

        settings = get_settings()
        adapter = get_fleetbase_integration(settings)
        result = adapter.run_orchestrator(
            fb_ids,
            mode=mode,
            engine=engine,
            vehicle_ids=scoped_vehicles,
            driver_ids=scoped_drivers or None,
            prior_assignments=priors or None,
        )
        # Attach PC order ids for the UI.
        for row in result.get("assignments") or []:
            fb = row.get("order_id")
            if fb and fb in fb_to_pc:
                row["porterchain_order_id"] = fb_to_pc[fb]

        unassigned_details: list[dict[str, Any]] = []
        for row in result.get("unassigned_details") or []:
            if not isinstance(row, dict):
                continue
            fb = row.get("order_id")
            detail = dict(row)
            if fb and fb in fb_to_pc:
                detail["porterchain_order_id"] = fb_to_pc[fb]
            unassigned_details.append(detail)

        before = {
            "before_order_count": len(fb_ids),
            "before_distance_m": None,
            "before_duration_s": None,
            "note": "Before metrics are plan-relative; Fleetbase returns after totals on the proposed plan.",
        }
        metrics = {**before, **(result.get("metrics") or {})}
        metrics = self._enrich_fuel_scorecard(
            db, metrics, vehicle_ids=scoped_vehicles
        )
        return {
            **result,
            "mode": mode,
            "engine": engine,
            "missing_sync": missing,
            "fleetbase_order_ids": fb_ids,
            "vehicle_ids": scoped_vehicles,
            "driver_ids": scoped_drivers,
            "unassigned_details": unassigned_details,
            "metrics": metrics,
            "ran_at": datetime.now(UTC).isoformat(),
        }

    def _enrich_fuel_scorecard(
        self,
        db: Session,
        metrics: dict[str, Any],
        *,
        vehicle_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """Attach pricing_fuel × km scorecard (Valhalla right-turn lives in matrix costing)."""
        from porterchain_pricing.fuel_scorecard import enrich_optimize_metrics_fuel
        from porterchain_pricing.types import FuelConfig

        fuel = FuelConfig()
        try:
            from porterchain_api.admin_models import SystemConfig

            row = (
                db.query(SystemConfig)
                .filter(SystemConfig.key == "pricing_fuel")
                .first()
            )
            if row and isinstance(row.value, dict):
                fuel = FuelConfig(
                    **{
                        k: v
                        for k, v in row.value.items()
                        if k in FuelConfig.__dataclass_fields__
                    }
                )
        except Exception as exc:  # noqa: BLE001
            logger.debug("pricing_fuel load for scorecard failed: %s", exc)

        vehicle_class: str | None = None
        if vehicle_ids:
            try:
                rows = (
                    db.query(Vehicle.vehicle_class)
                    .filter(Vehicle.fleetbase_vehicle_id.in_(list(vehicle_ids)))
                    .all()
                )
                classes = [str(r[0]) for r in rows if r and r[0]]
                # Prefer truck costing class when any scoped vehicle is a box truck.
                from porterchain_services.maps.costing import (
                    valhalla_costing_for_vehicle_class,
                )

                truckish = [
                    c for c in classes if valhalla_costing_for_vehicle_class(c) == "truck"
                ]
                vehicle_class = truckish[0] if truckish else (classes[0] if classes else None)
            except Exception as exc:  # noqa: BLE001
                logger.debug("vehicle_class for fuel scorecard failed: %s", exc)

        enriched = enrich_optimize_metrics_fuel(
            metrics, fuel=fuel, vehicle_class=vehicle_class
        )
        if vehicle_class:
            from porterchain_services.maps.costing import (
                valhalla_costing_for_vehicle_class,
            )

            enriched["valhalla_costing"] = valhalla_costing_for_vehicle_class(
                vehicle_class
            )
        return enriched

    def commit(
        self,
        db: Session,
        *,
        assignments: list[dict[str, Any]],
        scheduled_date: str | None = None,
        run_id: str | None = None,
        expected_sequence_version: int | None = None,
        pc_driver_id: str | None = None,
    ) -> dict[str, Any]:
        if not assignments:
            raise ValueError("assignments_required")
        rid = (run_id or "").strip() or None
        if rid:
            prior = _read_commit_cache(rid)
            if prior:
                return {**prior, "idempotent": True}
            stored = read_optimize_run(rid) or {}
            metrics = stored.get("metrics") if isinstance(stored.get("metrics"), dict) else {}
            rejects = int(metrics.get("capacity_reject_count") or 0)
            unassigned = stored.get("unassigned") or stored.get("unassigned_details") or []
            if rejects > 0 and unassigned:
                raise ValueError("capacity_rejects_block_commit")
        del db

        if pc_driver_id and expected_sequence_version is not None:
            from porterchain_driver.sequence_store import (
                SequenceConflictError,
                read_sequence,
            )

            live = read_sequence(str(pc_driver_id))
            current = int((live or {}).get("version") or 0)
            if int(expected_sequence_version) != current:
                raise SequenceConflictError(
                    current_version=current,
                    expected_version=int(expected_sequence_version),
                )

        settings = get_settings()
        adapter = get_fleetbase_integration(settings)
        # Strip PC-only fields before sending to Fleetbase.
        cleaned: list[dict[str, Any]] = []
        for a in assignments:
            cleaned.append(
                {
                    "order_id": a.get("order_id"),
                    "vehicle_id": a.get("vehicle_id"),
                    "driver_id": a.get("driver_id"),
                    "distance": a.get("distance_m") or a.get("distance") or 0,
                    "duration": a.get("duration_s") or a.get("duration") or 0,
                    "sequence": a.get("sequence"),
                }
            )
        day = scheduled_date or datetime.now(UTC).date().isoformat()
        result = adapter.commit_orchestrator(cleaned, scheduled_date=day)
        payload = {
            **result,
            "scheduled_date": day,
            "committed_at": datetime.now(UTC).isoformat(),
            "run_id": rid,
            "idempotent": False,
        }
        if rid:
            _write_commit_cache(rid, payload)
            from porterchain_api.fleetbase_engine.optimize_run_store import clear_fleet_optimize_open

            clear_fleet_optimize_open()
        if pc_driver_id:
            try:
                from porterchain_driver.sequence_store import apply_run_to_driver

                apply_run_to_driver(
                    str(pc_driver_id),
                    {
                        "status": "ready",
                        "run_id": rid,
                        "assignments": assignments,
                        "engine": "fleetbase_commit",
                    },
                    expected_version=expected_sequence_version,
                )
            except Exception as exc:  # noqa: BLE001 — commit already landed in Fleetbase
                logger.warning("post-commit sequence apply failed: %s", exc)
        return payload

    def engines(self) -> list[dict[str, Any]]:
        settings = get_settings()
        adapter = get_fleetbase_integration(settings)
        return adapter.list_orchestrator_engines()
