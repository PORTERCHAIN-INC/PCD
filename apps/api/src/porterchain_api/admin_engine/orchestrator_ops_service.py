"""Control Tower Optimize — PorterChain one-van day plan.

Maps queue orders to the OR-Tools sequencer (Valhalla matrix). Preview is
stored in Redis; accept writes ``sequence_store``.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

import porterchain_api.user_models as _user_models  # noqa: F401 — Driver.porterchain_user_id FK
from porterchain_api.admin_models import Driver, Vehicle
from porterchain_api.booking_models import Order
from porterchain_api.dispatch_engine.optimize_run_store import (
    STATUS_ERROR,
    STATUS_PENDING,
    STATUS_READY,
    read_optimize_run,
)
from porterchain_api.domain.admin_states import DriverStatus

logger = logging.getLogger(__name__)

COMMIT_CACHE_KEY = "porterchain:optimize_commit:{run_id}"
COMMIT_CACHE_TTL_SECONDS = 24 * 60 * 60

# Unassigned / retryable pool eligible for Optimize.
OPTIMIZE_STATES = frozenset(
    {"BOOKED", "DISPATCH_READY", "DRIVER_REJECTED", "FAILED", "DRIVER_ASSIGNED", "DRIVER_ACCEPTED"}
)
PREVIEW_ORDER_CAP = 20
# One van — same cap as the sequencer.
DAY_STOP_CAP = 25


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


class OrchestratorOpsService:
    def pool(self, db: Session, *, limit: int = 100, offset: int = 0) -> dict[str, Any]:
        from porterchain_api.admin_engine.optimize_pool import build_optimize_pool

        vehicle_ids, driver_ids = self._porterchain_fleet(db)
        return build_optimize_pool(
            db,
            limit=limit,
            offset=offset,
            vehicle_ids=vehicle_ids,
            driver_ids=driver_ids,
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

    def _porterchain_fleet(self, db: Session) -> tuple[list[str], list[str]]:
        """Active vans and approved drivers — PorterChain ids only."""
        vehicles = (
            db.query(Vehicle)
            .filter(Vehicle.is_active.is_(True))
            .all()
        )
        vehicle_ids = [v.id for v in vehicles if v.id]
        drivers = (
            db.query(Driver)
            .filter(Driver.status == DriverStatus.APPROVED.value)
            .all()
        )
        driver_ids = [d.id for d in drivers if d.id]
        return vehicle_ids, driver_ids

    def _load_orders(self, db: Session, order_ids: list[str] | None) -> list[Order]:
        if order_ids:
            rows = db.query(Order).filter(Order.id.in_(order_ids)).all()
            by_id = {o.id: o for o in rows}
            return [by_id[i] for i in order_ids if i in by_id]
        pool = self.pool(db, limit=PREVIEW_ORDER_CAP)
        ids = [row["id"] for row in pool["orders"] if row.get("id")]
        if not ids:
            return []
        rows = db.query(Order).filter(Order.id.in_(ids)).all()
        by_id = {o.id: o for o in rows}
        return [by_id[i] for i in ids if i in by_id]

    def _resolve_pc_driver(
        self,
        db: Session,
        *,
        pc_driver_id: str | None,
        driver_ids: list[str] | None,
        orders: list[Order],
    ) -> str | None:
        if pc_driver_id:
            return str(pc_driver_id)
        if driver_ids:
            return str(driver_ids[0])
        assigned = {o.assigned_driver_id for o in orders if o.assigned_driver_id}
        if len(assigned) == 1:
            return str(next(iter(assigned)))
        _, fleet_drivers = self._porterchain_fleet(db)
        for did in fleet_drivers:
            d = db.get(Driver, did)
            if d and (bool(d.is_online) or d.availability == "online"):
                return str(d.id)
        return fleet_drivers[0] if fleet_drivers else None

    def _vehicle_for_driver(self, db: Session, driver_id: str) -> Vehicle | None:
        return (
            db.query(Vehicle)
            .filter(Vehicle.driver_id == driver_id, Vehicle.is_active.is_(True))
            .first()
        )

    def enqueue_run(
        self,
        db: Session,
        *,
        order_ids: list[str] | None = None,
        mode: str = "allocate",
        engine: str | None = "porterchain",
        vehicle_ids: list[str] | None = None,
        driver_ids: list[str] | None = None,
        shape: str = "fleet",
        merchant_id: str | None = None,
        prior_assignments: list[dict[str, Any]] | None = None,
        pc_driver_id: str | None = None,
        apply_on_ready: bool = True,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Queue a one-van PorterChain day-plan preview. Worker runs OR-Tools."""
        from porterchain_api.dispatch_engine.day_plan import (
            payload_from_orders,
            queue_one_van,
        )
        from porterchain_api.platform.last_known import read_last_known

        del mode, prior_assignments  # accepted for API compat; day plan uses locked prefix
        shaped = self._shape_order_ids(
            db, shape=shape, order_ids=order_ids, merchant_id=merchant_id, offset=offset
        )
        orders = self._load_orders(db, shaped)
        if not orders:
            return {
                "ok": False,
                "status": STATUS_ERROR,
                "error": "no_eligible_orders",
                "message": "No orders with coordinates in the optimize pool.",
                "missing_sync": [],
                "assignments": [],
                "unassigned": [],
                "metrics": {},
            }

        driver_id = self._resolve_pc_driver(
            db, pc_driver_id=pc_driver_id, driver_ids=driver_ids, orders=orders
        )
        if not driver_id:
            return {
                "ok": False,
                "status": STATUS_ERROR,
                "error": "no_driver",
                "message": "Approve a driver before running Optimize.",
                "missing_sync": [],
                "assignments": [],
                "unassigned": [],
                "metrics": {},
            }

        vehicle = None
        if vehicle_ids:
            getter = getattr(db, "get", None)
            if callable(getter):
                try:
                    vehicle = getter(Vehicle, vehicle_ids[0])
                except Exception:  # noqa: BLE001 — test doubles / missing row
                    vehicle = None
        if vehicle is None:
            vehicle = self._vehicle_for_driver(db, driver_id)
        vehicle_class = str(vehicle.vehicle_class) if vehicle and vehicle.vehicle_class else None

        # Cap: sequencer refuses >25 stops (~12.5 pickup/drop pairs).
        if len(orders) * 2 > DAY_STOP_CAP:
            return {
                "ok": False,
                "status": STATUS_ERROR,
                "error": "day_too_large",
                "message": f"At most {DAY_STOP_CAP // 2} jobs on one van. Narrow the selection.",
                "missing_sync": [],
                "assignments": [],
                "unassigned": [],
                "metrics": {},
            }

        known = read_last_known(driver_id)
        origin = (
            {"lat": known.lat, "lng": known.lng}
            if known is not None
            else None
        )
        payload = payload_from_orders(
            orders,
            vehicle_class=vehicle_class,
            driver_id=driver_id,
            apply_on_ready=bool(apply_on_ready),
            origin=origin,
        )
        if vehicle is not None:
            payload["capacity"] = {
                "kg": vehicle.capacity_kg,
                "volume_m3": None,
                "pallets": None,
                "parcels": None,
            }
        payload["shape"] = shape
        payload["merchant_id"] = merchant_id
        payload["order_ids"] = [o.id for o in orders]
        payload["vehicle_ids"] = [vehicle.id] if vehicle else list(vehicle_ids or [])
        payload["driver_ids"] = [driver_id]
        payload["engine"] = "porterchain"
        if engine and engine not in {"porterchain", "vroom", "greedy", "capacity"}:
            payload["engine"] = "porterchain"

        try:
            pending = queue_one_van(payload)
            if not pc_driver_id and not driver_ids:
                from porterchain_api.dispatch_engine.optimize_run_store import (
                    mark_fleet_optimize_open,
                )

                mark_fleet_optimize_open()
            from porterchain_api.dispatch_engine.optimize_events import emit_enqueued

            emit_enqueued(
                pending["run_id"],
                engine="porterchain",
                shape=shape,
                order_count=len(orders),
                pc_driver_id=driver_id,
            )
            return pending
        except Exception as exc:
            logger.warning("optimize enqueue failed: %s", exc)
            from porterchain_api.dispatch_engine.optimize_events import emit_rejected

            emit_rejected("none", error="optimize_enqueue_failed")
            return {
                "ok": False,
                "status": STATUS_ERROR,
                "error": "optimize_enqueue_failed",
                "message": "Could not queue the preview. Try again.",
                "assignments": [],
                "unassigned": [],
                "metrics": {},
            }

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        return read_optimize_run(run_id)

    def execute_queued_run(self, db: Session, run_id: str) -> dict[str, Any]:
        """Worker fallback when the run record is not already engine=porterchain."""
        from porterchain_api.dispatch_engine.day_plan import finish_porterchain_run

        rec = read_optimize_run(run_id)
        if not rec:
            return {"ok": False, "status": STATUS_ERROR, "error": "run_not_found", "assignments": []}
        if rec.get("status") != STATUS_PENDING:
            return rec
        merged = finish_porterchain_run(db, run_id, {**rec, "engine": "porterchain"})
        status = STATUS_READY if merged.get("status") == "ready" or merged.get("ok") else STATUS_ERROR
        if status == STATUS_READY:
            merged["ok"] = True
            merged["status"] = STATUS_READY
        pc_driver_id = merged.get("pc_driver_id") or rec.get("pc_driver_id")
        if not pc_driver_id:
            from porterchain_api.dispatch_engine.optimize_run_store import (
                clear_fleet_optimize_open,
            )

            clear_fleet_optimize_open()
        if status == STATUS_READY:
            from porterchain_api.dispatch_engine.optimize_events import emit_ready

            emit_ready(
                run_id,
                engine="porterchain",
                assignment_count=len(merged.get("assignments") or []),
                unassigned_count=len(merged.get("unassigned") or []),
            )
            apply_flag = merged.get("apply_on_ready")
            if apply_flag is None:
                apply_flag = True
            if pc_driver_id and apply_flag:
                try:
                    from porterchain_driver.sequence_store import apply_run_to_driver

                    from porterchain_api.dispatch_engine.optimize_events import (
                        emit_applied,
                    )

                    waypoints = apply_run_to_driver(str(pc_driver_id), merged)
                    if waypoints:
                        emit_applied(
                            run_id,
                            pc_driver_id=str(pc_driver_id),
                            waypoint_count=len(waypoints),
                        )
                except Exception as exc:  # noqa: BLE001
                    logger.warning("driver sequence apply failed run_id=%s: %s", run_id, exc)
        else:
            from porterchain_api.dispatch_engine.optimize_events import emit_rejected

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
        engine: str | None = "porterchain",
        vehicle_ids: list[str] | None = None,
        driver_ids: list[str] | None = None,
        prior_assignments: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Enqueue and return the pending run (worker finishes the search)."""
        del prior_assignments
        return self.enqueue_run(
            db,
            order_ids=order_ids,
            mode=mode,
            engine=engine or "porterchain",
            vehicle_ids=vehicle_ids,
            driver_ids=driver_ids,
        )

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
            if not pc_driver_id:
                pc_driver_id = stored.get("pc_driver_id")
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

        day = scheduled_date or datetime.now(UTC).date().isoformat()
        payload = {
            "ok": True,
            "engine": "porterchain",
            "scheduled_date": day,
            "committed_at": datetime.now(UTC).isoformat(),
            "run_id": rid,
            "idempotent": False,
            "assignments": assignments,
        }
        if rid:
            _write_commit_cache(rid, payload)
            from porterchain_api.dispatch_engine.optimize_run_store import (
                clear_fleet_optimize_open,
            )

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
                        "engine": "porterchain",
                    },
                    expected_version=expected_sequence_version,
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("post-commit sequence apply failed: %s", exc)
        return payload

    def engines(self) -> list[dict[str, Any]]:
        return [{"id": "porterchain", "name": "PorterChain", "label": "One van day plan"}]
