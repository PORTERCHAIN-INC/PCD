"""Driver jobs — list, detail, and history scoped to assigned driver.

Reuses AdminOrdersService for timeline reads only; never duplicates order transitions.
"""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any
import logging

from porterchain_driver.job_legs import allowed_actions, current_leg, delivery_completed, pickup_completed
from porterchain_driver.next_stop import NextStopResolver
from porterchain_driver.route_optimizer import DriverRouteOptimizer, compute_urgency
from porterchain_driver.stops import StopsService

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def _any_coords(orders: list[Any]) -> bool:
    for order in orders:
        for addr in (getattr(order, "pickup", None), getattr(order, "dropoff", None)):
            if not isinstance(addr, dict):
                continue
            lat = addr.get("lat") or addr.get("latitude")
            lng = addr.get("lng") or addr.get("lon") or addr.get("longitude")
            if lat is not None and lng is not None:
                return True
    return False

_COMPLETED_STATES = frozenset(
    {
        "DELIVERED",
        "POD_COMPLETED",
        "INVOICED",
        "CLOSED",
        "CANCELLED",
        "FAILED",
        "RETURN_TO_SENDER",
        "DAMAGED",
        "LOST",
        "REFUNDED",
    }
)


def _shopify_order_label(order: Any) -> str | None:
    if str(getattr(order, "order_source", "") or "").upper() != "SHOPIFY":
        return None
    meta = order.compliance_metadata if isinstance(getattr(order, "compliance_metadata", None), dict) else {}
    raw = meta.get("shopify") if isinstance(meta.get("shopify"), dict) else {}
    name = raw.get("order_name") or raw.get("name") or getattr(order, "internal_reference", None)
    text = str(name).strip() if name else ""
    return f"Shopify {text}" if text else "Shopify"


class JobsService:
    def __init__(self) -> None:
        self._stops = StopsService()
        self._optimizer = DriverRouteOptimizer()
        self._next_stop = NextStopResolver()

    def list_jobs(self, db: Session, driver: Any) -> dict[str, Any]:
        from porterchain_driver.sequence_store import read_sequence

        plan = read_sequence(driver.id)
        priority_ranks = self._optimizer.priority_ranks_from_plan(
            SimpleNamespace(stops=(plan or {}).get("waypoints") or []) if plan else None
        )
        orders = self._today_orders(db, driver.id)
        try:
            next_stop = self._next_stop.resolve(db, driver)
        except Exception:
            logger.exception("next_stop resolve failed for driver %s", getattr(driver, "id", None))
            next_stop = None
        next_order_id = next_stop.get("order_id") if next_stop else None

        from porterchain_api.merchant_engine.scan_gate_service import ScanGateService

        scan_by_order = ScanGateService().progress_by_order_ids(db, [o.id for o in orders])
        summaries = [
            self._job_summary(
                db,
                driver,
                order,
                priority_ranks=priority_ranks,
                next_order_id=next_order_id,
                scan=scan_by_order.get(order.id),
            )
            for order in orders
        ]
        current = next(
            (j for j in summaries if j["bucket"] == "current"),
            next((j for j in summaries if j["bucket"] != "completed"), None),
        )
        upcoming = self._sort_by_priority([j for j in summaries if j["bucket"] == "upcoming"])
        completed = [j for j in summaries if j["bucket"] == "completed"]
        try:
            route = self._stops.assigned_route(db, driver)
        except Exception:
            logger.exception("assigned_route failed for driver %s", getattr(driver, "id", None))
            route = None
        active_jobs = [j for j in summaries if j["bucket"] != "completed"]
        completed_jobs = [j for j in summaries if j["bucket"] == "completed"]
        prev_metrics = (plan or {}).get("metrics") if isinstance(plan, dict) else None
        route_metrics = None
        if isinstance(prev_metrics, dict) and prev_metrics:
            route_metrics = {
                "distance_km": prev_metrics.get("after_distance_km"),
                "duration_minutes": prev_metrics.get("after_duration_min"),
                "estimated_fuel_cents": prev_metrics.get("estimated_fuel_cents"),
                "estimated_fuel_liters": prev_metrics.get("estimated_fuel_liters"),
                "source": "last_optimize",
            }
        return {
            "route_id": route.route_id if route else None,
            "route_status": route.status if route else None,
            "plan_id": (plan or {}).get("run_id"),
            "route_metrics": route_metrics,
            "optimize_available": self._optimizer.can_optimize(
                [o for o in orders if str(o.state) not in _COMPLETED_STATES]
            ),
            "next_stop": next_stop,
            "current": current,
            "upcoming": upcoming,
            "completed": completed,
            "jobs": self._sort_by_priority(active_jobs) + completed_jobs,
        }

    def optimize_route(
        self,
        db: Session,
        driver: Any,
        *,
        insert_order_id: str | None = None,
        preview: bool = False,
    ) -> dict[str, Any]:
        """Queue this driver's van. The worker searches. Accept only draws the stored order."""
        from porterchain_api.dispatch_engine.day_plan import payload_from_orders, queue_one_van

        orders = [o for o in self._today_orders(db, driver.id) if str(o.state) not in _COMPLETED_STATES]
        if not orders or not _any_coords(orders):
            raise ValueError("no_synced_jobs")

        vehicle_class = None
        try:
            from porterchain_api.admin_models import Vehicle

            vehicles = (
                db.query(Vehicle)
                .filter(Vehicle.driver_id == driver.id, Vehicle.is_active.is_(True))
                .all()
            )
            for vehicle in vehicles:
                kind = getattr(vehicle, "vehicle_class", None)
                if kind:
                    vehicle_class = str(kind)
                    break
        except Exception:  # noqa: BLE001
            vehicle_class = None

        rec = queue_one_van(
            payload_from_orders(
                orders,
                vehicle_class=vehicle_class,
                driver_id=str(driver.id),
                insert_order_id=insert_order_id,
                apply_on_ready=not preview,
            )
        )
        jobs = self.list_jobs(db, driver)
        out = self.plan_from_run(rec, jobs, driver_id=driver.id)
        out["preview"] = bool(preview)
        out["apply_on_ready"] = not preview
        return out

    def optimize_run_status(
        self,
        db: Session,
        driver: Any,
        run_id: str,
        *,
        expected_version: int | None = None,
        apply: bool = False,
    ) -> dict[str, Any]:
        from porterchain_api.admin_engine.orchestrator_ops_service import OrchestratorOpsService
        from porterchain_driver.sequence_store import apply_run_to_driver, read_sequence

        rec = OrchestratorOpsService().get_run(run_id)
        if not rec:
            raise LookupError("optimize_run_not_found")
        # IDOR: driver-scoped runs must not leak across drivers (404, not 403).
        owner = rec.get("pc_driver_id")
        if owner and str(owner) != str(driver.id):
            raise LookupError("optimize_run_not_found")
        # Capture baseline before apply overwrites the sequence metrics snapshot.
        prev = read_sequence(driver.id)
        before_km = None
        if isinstance(prev, dict):
            prev_m = prev.get("metrics") if isinstance(prev.get("metrics"), dict) else {}
            if prev_m.get("after_distance_km") is not None:
                try:
                    before_km = float(prev_m["after_distance_km"])
                except (TypeError, ValueError):
                    before_km = None
        applied = False
        if apply and (rec.get("status") or "") == "ready":
            if rec.get("engine") == "porterchain":
                from porterchain_api.dispatch_engine.day_plan import accept_line

                accept_line(
                    [tuple(point) for point in (rec.get("line_points") or [])],
                    vehicle_class=rec.get("vehicle_class"),
                )
            apply_run_to_driver(driver.id, rec, expected_version=expected_version)
            applied = True
            try:
                from porterchain_api.dispatch_engine.optimize_events import emit_applied

                emit_applied(
                    run_id,
                    pc_driver_id=str(driver.id),
                    via="driver_accept",
                )
            except Exception:  # noqa: BLE001
                pass
        jobs = self.list_jobs(db, driver)
        if before_km is not None and applied:
            jobs = {
                **jobs,
                "route_metrics": {
                    **(jobs.get("route_metrics") or {}),
                    "distance_km": before_km,
                },
            }
        out = self.plan_from_run(rec, jobs, driver_id=driver.id)
        out["preview"] = not applied and not bool(rec.get("apply_on_ready", True))
        out["applied"] = applied
        return out

    def accept_optimize_run(
        self,
        db: Session,
        driver: Any,
        run_id: str,
        *,
        expected_version: int | None = None,
    ) -> dict[str, Any]:
        """Apply a ready preview to the driver's sequence (Preview→Accept)."""
        return self.optimize_run_status(
            db, driver, run_id, expected_version=expected_version, apply=True
        )

    def undo_optimize(self, db: Session, driver: Any) -> dict[str, Any]:
        """Restore previous sequence snapshot after a bad Accept."""
        from porterchain_driver.sequence_store import rollback_sequence

        restored = rollback_sequence(driver.id)
        jobs = self.list_jobs(db, driver)
        if not restored:
            return {
                "ok": False,
                "status": "error",
                "error": "nothing_to_undo",
                "message": "No previous stop order to restore.",
                "jobs": jobs,
            }
        return {
            "ok": True,
            "status": "ready",
            "run_id": restored.get("run_id"),
            "sequence_version": restored.get("version"),
            "message": "Previous stop order restored.",
            "jobs": jobs,
            "optimized_stops": list(restored.get("waypoints") or []),
            "metrics": dict(restored.get("metrics") or {}),
            "warnings": [],
            "order_ids": [],
            "plan_id": restored.get("run_id") or "rollback",
        }

    @staticmethod
    def plan_from_run(
        rec: dict[str, Any],
        jobs: dict[str, Any],
        *,
        driver_id: str | None = None,
    ) -> dict[str, Any]:
        from porterchain_driver.sequence_store import read_sequence, waypoints_from_assignments
        from porterchain_pricing.fuel_scorecard import enrich_optimize_metrics_fuel

        assignments = rec.get("assignments") or []
        waypoints = waypoints_from_assignments(list(assignments))
        stops: list[dict[str, Any]] = []
        if waypoints:
            for wp in waypoints:
                stops.append(
                    {
                        "sequence": wp["sequence"],
                        "order_id": wp["order_id"],
                        "tracking_number": wp["order_id"],
                        "type": wp["stop_type"],
                        "stop_type": wp["stop_type"],
                        "vehicle_id": wp.get("vehicle_id"),
                        "driver_id": wp.get("driver_id"),
                    }
                )
        else:
            for i, row in enumerate(assignments, 1):
                if not isinstance(row, dict):
                    continue
                stops.append(
                    {
                        "sequence": row.get("sequence") or i,
                        "order_id": row.get("porterchain_order_id") or row.get("order_id"),
                        "tracking_number": row.get("order_id"),
                        "type": "stop",
                        "vehicle_id": row.get("vehicle_id"),
                        "driver_id": row.get("driver_id"),
                    }
                )
        run_id = rec.get("run_id") or ""
        metrics = dict(rec.get("metrics") or {})
        metrics.setdefault("engine", rec.get("engine") or "porterchain")
        # Baseline from prior applied plan so driver UI can show fuel/km delta.
        route_metrics = jobs.get("route_metrics") if isinstance(jobs, dict) else None
        if isinstance(route_metrics, dict) and route_metrics.get("distance_km") is not None:
            try:
                metrics.setdefault(
                    "before_distance_km", float(route_metrics["distance_km"])
                )
            except (TypeError, ValueError):
                pass
        if metrics.get("after_distance_km") is not None or metrics.get("after_distance_m"):
            metrics = enrich_optimize_metrics_fuel(metrics)
        sequence_version = None
        if driver_id:
            applied = read_sequence(driver_id)
            if isinstance(applied, dict) and applied.get("version") is not None:
                try:
                    sequence_version = int(applied["version"])
                except (TypeError, ValueError):
                    sequence_version = None
        return {
            "plan_id": run_id or "none",
            "run_id": run_id or None,
            "status": rec.get("status") or "pending",
            "optimized_stops": stops,
            "metrics": metrics,
            "warnings": list(rec.get("warnings") or []),
            "order_ids": rec.get("order_ids") or [],
            "message": rec.get("message") or rec.get("error"),
            "jobs": jobs,
            "sequence_version": sequence_version,
        }

    def order_history(self, db: Session, driver: Any, *, limit: int = 50) -> list[dict[str, Any]]:
        from porterchain_api.booking_models import Order

        rows = (
            db.query(Order)
            .filter(
                Order.assigned_driver_id == driver.id,
                Order.state.in_(list(_COMPLETED_STATES)),
            )
            .order_by(Order.updated_at.desc())
            .limit(limit)
            .all()
        )
        from porterchain_api.merchant_engine.scan_gate_service import ScanGateService

        scan_by_order = ScanGateService().progress_by_order_ids(db, [o.id for o in rows])
        return [
            self._job_summary(
                db,
                driver,
                order,
                force_bucket="completed",
                scan=scan_by_order.get(order.id),
            )
            for order in rows
        ]

    def job_detail(self, db: Session, driver: Any, order_id: str) -> dict[str, Any]:
        order = self._require_order(db, driver.id, order_id)
        from porterchain_api.admin_engine.orders_service import AdminOrdersService
        from porterchain_api.booking_engine.compliance_metadata import otp_required_at_delivery
        from porterchain_api.driver_models import DriverIncident, DriverStopMeta
        from porterchain_api.merchant_models import Merchant
        from porterchain_api.booking_models import Customer, OrderException

        admin_orders = AdminOrdersService()
        customer = (
            db.query(Customer).filter(Customer.id == order.customer_id).first()
            if order.customer_id
            else None
        )
        merchant = (
            db.query(Merchant).filter(Merchant.id == order.merchant_id).first()
            if order.merchant_id
            else None
        )
        meta_row = db.query(DriverStopMeta).filter(DriverStopMeta.order_id == order_id).first()
        stop_meta = dict(meta_row.meta or {}) if meta_row else {}
        proofs = list(stop_meta.get("proofs", []))
        photos = [p for p in proofs if p.get("type") == "photo"]
        signatures = [p for p in proofs if p.get("type") == "signature"]
        documents = [p for p in proofs if p.get("type") not in ("photo", "signature", "barcode")]

        incidents = (
            db.query(DriverIncident)
            .filter(DriverIncident.driver_id == driver.id, DriverIncident.order_id == order_id)
            .order_by(DriverIncident.created_at.desc())
            .all()
        )

        pickup_stop = self._stops._order_to_stop(order, "pickup")  # noqa: SLF001
        delivery_stop = self._stops._order_to_stop(order, "dropoff")  # noqa: SLF001

        from porterchain_driver.stop_exceptions import MAX_DELIVERY_ATTEMPTS, prior_attempt_rows

        attempt_rows = prior_attempt_rows(
            db.query(OrderException).filter(OrderException.order_id == order_id).all()
        )
        delivery_attempts = len(attempt_rows)

        timeline = []
        for ev in admin_orders.order_timeline(db, order_id):
            timeline.append(
                {
                    "event_type": ev.event_type,
                    "label": ev.event_type.replace(".", " ").replace("_", " ").title(),
                    "from_state": ev.from_state,
                    "to_state": ev.to_state,
                    "occurred_at": ev.occurred_at.isoformat() if ev.occurred_at else None,
                    "actor_type": ev.actor_type,
                }
            )

        packages, scan_pickup, scan_delivery, packages_error = self._load_packages(db, order)

        dropoff = order.dropoff or {}
        pickup = order.pickup or {}

        next_stop = self._next_stop.resolve(db, driver)
        state = str(order.state)
        leg_meta = self._leg_metadata(state, stop_meta)

        return {
            **self._job_summary(
                db,
                driver,
                order,
                next_order_id=next_stop.get("order_id") if next_stop else None,
                scan={"scan_pickup": scan_pickup, "scan_delivery": scan_delivery},
            ),
            "special_instructions": order.special_instructions,
            "declared_value_cents": (
                (order.compliance_metadata or {}).get("parcels", {}).get("declared_value_cents")
                if isinstance(order.compliance_metadata, dict)
                and isinstance((order.compliance_metadata or {}).get("parcels"), dict)
                else None
            ),
            "booking_mode": (order.compliance_metadata or {}).get("booking_mode")
            if isinstance(order.compliance_metadata, dict)
            else None,
            "vehicle_class": self._order_vehicle_class(db, order),
            "pickup_detail": pickup,
            "delivery_detail": dropoff,
            "pickup_stop": self._stop_dict(pickup_stop),
            "delivery_stop": self._stop_dict(delivery_stop),
            **leg_meta,
            "next_stop": next_stop,
            "is_current_job": bool(next_stop and next_stop.get("order_id") == order_id),
            "pickup_completed_at": stop_meta.get("pickup_completed_at"),
            "delivery_completed_at": stop_meta.get("delivery_completed_at"),
            "merchant": (
                {
                    "id": merchant.id,
                    "company_name": merchant.company_name,
                    "email": merchant.email,
                    "phone": merchant.phone,
                }
                if merchant
                else None
            ),
            "customer": {
                "id": customer.id if customer else None,
                "email": customer.email if customer else dropoff.get("email") or pickup.get("email"),
                "phone": customer.phone if customer else dropoff.get("phone") or pickup.get("phone"),
                "name": dropoff.get("name") or dropoff.get("contact_name") or pickup.get("name"),
            },
            "packages": packages,
            "packages_error": packages_error,
            "scan_pickup": {
                "scanned": scan_pickup.get("scanned", 0),
                "required": scan_pickup.get("required", 0),
                "complete": bool(scan_pickup.get("complete")),
                "missing_suffixes": scan_pickup.get("missing_suffixes") or [],
            },
            "scan_delivery": {
                "scanned": scan_delivery.get("scanned", 0),
                "required": scan_delivery.get("required", 0),
                "complete": bool(scan_delivery.get("complete")),
                "missing_suffixes": scan_delivery.get("missing_suffixes") or [],
            },
            "timeline": timeline,
            "photos": photos,
            "signatures": signatures,
            "documents": documents,
            "proof_of_delivery": {
                "completed": str(order.state) in ("POD_COMPLETED", "CLOSED", "INVOICED"),
                "proofs": proofs,
                "otp_verified": bool(stop_meta.get("delivery_otp_hash")),
            },
            "otp_required": otp_required_at_delivery(order.compliance_metadata),
            **_pod_gate(db, driver, order),
            "incidents": [
                {
                    "id": i.id,
                    "incident_type": i.incident_type,
                    "description": i.description,
                    "status": i.status,
                    "created_at": i.created_at.isoformat(),
                }
                for i in incidents
            ],
            "delivery_attempts": delivery_attempts,
            "max_delivery_attempts": MAX_DELIVERY_ATTEMPTS,
            "amount_cents": order.amount_cents,
            "cod_amount_cents": getattr(order, "cod_amount_cents", None),
            "cod_status": getattr(order, "cod_status", None),
            "currency": order.currency,
            "scheduled_at": order.scheduled_at.isoformat() if order.scheduled_at else None,
            "updated_at": order.updated_at.isoformat() if order.updated_at else None,
        }

    @staticmethod
    def _order_vehicle_class(db: Session, order: Any) -> str | None:
        from porterchain_api.domain.customer_goods import booked_capacity_class

        quote_id = getattr(order, "quote_id", None)
        quote_vc = None
        if quote_id:
            from porterchain_api.booking_models import Quote

            quote = db.query(Quote).filter(Quote.id == quote_id).first()
            quote_vc = getattr(quote, "vehicle_class", None) if quote else None
        meta = getattr(order, "compliance_metadata", None)
        return booked_capacity_class(
            quote_vehicle_class=quote_vc,
            compliance_metadata=meta if isinstance(meta, dict) else None,
        )

    @staticmethod
    def _leg_metadata(state: str, stop_meta: dict[str, Any]) -> dict[str, Any]:
        return {
            "current_leg": current_leg(state),
            "allowed_actions": allowed_actions(state),
            "pickup_completed": pickup_completed(state) or bool(stop_meta.get("pickup_completed_at")),
            "delivery_completed": delivery_completed(state) or bool(stop_meta.get("delivery_completed_at")),
        }

    def _today_orders(self, db: Session, driver_id: str) -> list:
        return self._stops._today_orders(db, driver_id)  # noqa: SLF001

    @staticmethod
    def route_id_for_order(order: Any) -> str | None:
        dt = getattr(order, "scheduled_at", None) or getattr(order, "updated_at", None)
        if dt is None:
            return None
        date = dt.date() if hasattr(dt, "date") else None
        if date is None:
            return None
        return f"route-{date.isoformat()}"

    @staticmethod
    def _scan_view(progress: dict[str, Any] | None) -> dict[str, Any]:
        src = progress or {}
        return {
            "scanned": int(src.get("scanned") or 0),
            "required": int(src.get("required") or 0),
            "complete": bool(src.get("complete")),
            "missing_suffixes": list(src.get("missing_suffixes") or []),
        }

    def _load_packages(
        self, db: Session, order: Any
    ) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any], str | None]:
        empty = self._scan_view(None)
        try:
            from porterchain_api.merchant_engine.scan_gate_service import ScanGateService

            gate = ScanGateService()
            packages = gate.package_rows(db, order)
            pickup = self._scan_view(gate.scan_progress(db, order, phase="pickup"))
            delivery = self._scan_view(gate.scan_progress(db, order, phase="delivery"))
            return packages, pickup, delivery, None
        except Exception:  # noqa: BLE001 — job stays up; never invent a fake box
            logger.exception("scan_gate failed for order %s", getattr(order, "id", None))
            return [], dict(empty), dict(empty), "packages_unavailable"

    def _require_order(self, db: Session, driver_id: str, order_id: str):
        from porterchain_api.booking_models import Order

        order = (
            db.query(Order)
            .filter(Order.id == order_id, Order.assigned_driver_id == driver_id)
            .first()
        )
        if not order:
            raise LookupError("job_not_found")
        return order

    def _job_summary(
        self,
        db: Session,
        driver: Any,
        order: Any,
        *,
        force_bucket: str | None = None,
        priority_ranks: dict[str, int] | None = None,
        next_order_id: str | None = None,
        scan: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        state = str(order.state)
        bucket = force_bucket or self._bucket_for_order(state, order.id, next_order_id)
        pickup = order.pickup or {}
        dropoff = order.dropoff or {}
        urgency = compute_urgency(order)
        ranks = priority_ranks or {}
        scan_block = scan or {}
        return {
            "order_id": order.id,
            "order_number": order.order_number,
            "tracking_number": order.tracking_number,
            "state": state,
            "status": state.lower(),
            "bucket": bucket,
            "pickup_address": pickup.get("formatted") or pickup.get("line1") or "—",
            "delivery_address": dropoff.get("formatted") or dropoff.get("line1") or "—",
            "pickup_stop_id": f"{order.id}-pickup",
            "delivery_stop_id": f"{order.id}-dropoff",
            "scheduled_at": order.scheduled_at.isoformat() if order.scheduled_at else None,
            "special_instructions": order.special_instructions,
            "urgency": urgency,
            "high_priority": urgency in ("critical", "high"),
            "priority_rank": ranks.get(order.id),
            "current_leg": current_leg(state),
            "pickup_completed": pickup_completed(state),
            "delivery_completed": delivery_completed(state),
            "is_current_job": bool(next_order_id and next_order_id == order.id),
            "route_id": self.route_id_for_order(order),
            "scan_pickup": self._scan_view(scan_block.get("scan_pickup")),
            "scan_delivery": self._scan_view(scan_block.get("scan_delivery")),
            "shopify_order_label": _shopify_order_label(order),
        }

    @staticmethod
    def _sort_by_priority(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        urgency_weight = {"critical": 0, "high": 1, "medium": 2, "normal": 3}

        def sort_key(job: dict[str, Any]) -> tuple:
            rank = job.get("priority_rank")
            return (
                rank is None,
                rank if rank is not None else 9999,
                urgency_weight.get(job.get("urgency") or "normal", 3),
            )

        return sorted(jobs, key=sort_key)

    @staticmethod
    def _bucket_for_order(state: str, order_id: str, next_order_id: str | None) -> str:
        if state in _COMPLETED_STATES:
            return "completed"
        if next_order_id:
            return "current" if next_order_id == order_id else "upcoming"
        return "upcoming"

    @staticmethod
    def _stop_dict(stop: Any) -> dict[str, Any]:
        return {
            "stop_id": stop.stop_id,
            "stop_type": stop.stop_type,
            "status": stop.status,
            "address": stop.address,
            "scheduled_at": stop.scheduled_at.isoformat() if stop.scheduled_at else None,
            "otp_required": stop.otp_required,
            "pod_required": stop.pod_required,
        }


def _pod_gate(db: Session, driver: Any, order: Any) -> dict[str, Any]:
    """What the driver must capture before completing the dropoff (readiness audit #5)."""
    from porterchain_driver.pod_policy import duty_enforced, is_on_duty, missing_for, requirements_for

    try:
        req = requirements_for(db, order)
        missing = missing_for(db, order, requirements=req) if req["enforced"] else []
    except Exception:  # noqa: BLE001 — never break the job screen over the gate preview
        req, missing = {"enforced": False}, []
    return {
        "pod_requirements": req,
        "pod_missing": missing,
        "on_duty": is_on_duty(db, driver) if duty_enforced() else True,
    }
