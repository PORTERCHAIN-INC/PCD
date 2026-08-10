"""Control Tower Optimize — wrap Fleetbase orchestrator for PC order ids.

Maps Porterchain queue orders → fleetbase_order_id, runs allocate/optimize,
and commits assignment plans (creates Fleetbase manifests). Never rebuilds
VROOM/greedy engines locally.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.config import get_settings
from porterchain_api.models import Order
from porterchain_api.services.fleetbase_integration import get_fleetbase_integration

logger = logging.getLogger(__name__)

# Unassigned / retryable pool eligible for Optimize.
OPTIMIZE_STATES = frozenset(
    {"BOOKED", "DISPATCH_READY", "DRIVER_REJECTED", "FAILED", "DRIVER_ASSIGNED", "DRIVER_ACCEPTED"}
)


class OrchestratorOpsService:
    def pool(self, db: Session, *, limit: int = 100) -> dict[str, Any]:
        rows = (
            db.query(Order)
            .filter(
                Order.state.in_(OPTIMIZE_STATES),
                Order.fleetbase_order_id.isnot(None),
            )
            .order_by(Order.scheduled_at.asc())
            .limit(limit)
            .all()
        )
        return {
            "order_count": len(rows),
            "synced_count": len(rows),
            "orders": [
                {
                    "id": o.id,
                    "tracking_number": o.tracking_number,
                    "state": o.state,
                    "fleetbase_order_id": o.fleetbase_order_id,
                    "scheduled_at": o.scheduled_at.isoformat() if o.scheduled_at else None,
                    "merchant_id": o.merchant_id,
                }
                for o in rows
            ],
        }

    def _resolve_fleetbase_ids(
        self, db: Session, order_ids: list[str] | None
    ) -> tuple[list[str], dict[str, str], list[str]]:
        """Return (fleetbase_ids, fb→pc map, missing_pc_ids)."""
        if order_ids:
            orders = db.query(Order).filter(Order.id.in_(order_ids)).all()
        else:
            pool = self.pool(db)
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
            if not o.fleetbase_order_id:
                missing.append(o.id)
                continue
            fb_ids.append(o.fleetbase_order_id)
            fb_to_pc[o.fleetbase_order_id] = o.id
        return fb_ids, fb_to_pc, missing

    def run(
        self,
        db: Session,
        *,
        order_ids: list[str] | None = None,
        mode: str = "allocate",
        engine: str | None = "greedy",
    ) -> dict[str, Any]:
        settings = get_settings()
        adapter = get_fleetbase_integration(settings)
        fb_ids, fb_to_pc, missing = self._resolve_fleetbase_ids(db, order_ids)
        if not fb_ids:
            return {
                "ok": False,
                "error": "no_synced_orders",
                "message": "No orders with fleetbase_order_id in the optimize pool.",
                "missing_sync": missing,
                "assignments": [],
                "metrics": {},
            }

        result = adapter.run_orchestrator(fb_ids, mode=mode, engine=engine)
        # Attach PC order ids for the UI.
        for row in result.get("assignments") or []:
            fb = row.get("order_id")
            if fb and fb in fb_to_pc:
                row["porterchain_order_id"] = fb_to_pc[fb]

        before = {
            "before_order_count": len(fb_ids),
            "before_distance_m": None,
            "before_duration_s": None,
            "note": "Before metrics are plan-relative; Fleetbase returns after totals on the proposed plan.",
        }
        metrics = {**before, **(result.get("metrics") or {})}
        return {
            **result,
            "mode": mode,
            "engine": engine,
            "missing_sync": missing,
            "fleetbase_order_ids": fb_ids,
            "metrics": metrics,
            "ran_at": datetime.now(UTC).isoformat(),
        }

    def commit(
        self,
        db: Session,
        *,
        assignments: list[dict[str, Any]],
        scheduled_date: str | None = None,
    ) -> dict[str, Any]:
        del db
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
        return {**result, "scheduled_date": day, "committed_at": datetime.now(UTC).isoformat()}

    def engines(self) -> list[dict[str, Any]]:
        settings = get_settings()
        adapter = get_fleetbase_integration(settings)
        return adapter.list_orchestrator_engines()
