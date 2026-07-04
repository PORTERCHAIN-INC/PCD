"""Driver jobs — list, detail, and history scoped to assigned driver.

Reuses AdminOrdersService for timeline reads only; never duplicates order transitions.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from porterchain_driver.job_legs import allowed_actions, current_leg, delivery_completed, pickup_completed
from porterchain_driver.next_stop import NextStopResolver
from porterchain_driver.route_optimizer import DriverRouteOptimizer, compute_urgency
from porterchain_driver.stops import StopsService

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

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


class JobsService:
    def __init__(self) -> None:
        self._stops = StopsService()
        self._optimizer = DriverRouteOptimizer()
        self._next_stop = NextStopResolver()

    def list_jobs(self, db: Session, driver: Any) -> dict[str, Any]:
        plan = self._stops._active_plan(db, driver.id)  # noqa: SLF001
        priority_ranks = self._optimizer.priority_ranks_from_plan(plan)
        orders = self._today_orders(db, driver.id)
        next_stop = self._next_stop.resolve(db, driver)
        next_order_id = next_stop.get("order_id") if next_stop else None

        summaries = [
            self._job_summary(
                db,
                driver,
                order,
                priority_ranks=priority_ranks,
                next_order_id=next_order_id,
            )
            for order in orders
        ]
        current = next(
            (j for j in summaries if j["bucket"] == "current"),
            next((j for j in summaries if j["bucket"] != "completed"), None),
        )
        upcoming = self._sort_by_priority([j for j in summaries if j["bucket"] == "upcoming"])
        completed = [j for j in summaries if j["bucket"] == "completed"]
        route = self._stops.assigned_route(db, driver)
        metrics = dict(plan.simulation or {}) if plan and plan.simulation else None
        active_jobs = [j for j in summaries if j["bucket"] != "completed"]
        completed_jobs = [j for j in summaries if j["bucket"] == "completed"]
        return {
            "route_id": route.route_id if route else None,
            "route_status": route.status if route else None,
            "plan_id": plan.id if plan else None,
            "route_metrics": metrics,
            "optimize_available": self._optimizer.can_optimize(
                [o for o in orders if str(o.state) not in _COMPLETED_STATES]
            ),
            "next_stop": next_stop,
            "current": current,
            "upcoming": upcoming,
            "completed": completed,
            "jobs": self._sort_by_priority(active_jobs) + completed_jobs,
        }

    def optimize_route(self, db: Session, driver: Any) -> dict[str, Any]:
        result = self._optimizer.optimize(db, driver)
        jobs = self.list_jobs(db, driver)
        return {**result, "jobs": jobs}

    def order_history(self, db: Session, driver: Any, *, limit: int = 50) -> list[dict[str, Any]]:
        from porterchain_api.models import Order

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
        return [self._job_summary(db, driver, order, force_bucket="completed") for order in rows]

    def job_detail(self, db: Session, driver: Any, order_id: str) -> dict[str, Any]:
        order = self._require_order(db, driver.id, order_id)
        from porterchain_api.admin_engine.orders_service import AdminOrdersService
        from porterchain_api.driver_models import DriverIncident, DriverStopMeta
        from porterchain_api.merchant_models import Merchant
        from porterchain_api.models import Customer, Quote

        admin_orders = AdminOrdersService()
        quote = db.query(Quote).filter(Quote.id == order.quote_id).first() if order.quote_id else None
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

        packages: list[dict[str, Any]] = []
        if quote:
            packages.append(
                {
                    "package_type": quote.package_type,
                    "vehicle_class": quote.vehicle_class,
                    "weight_kg": quote.weight_kg,
                    "dimensions": quote.dimensions,
                    "declared_value_cents": quote.declared_value_cents,
                }
            )

        dropoff = order.dropoff or {}
        pickup = order.pickup or {}

        route = self._stops.assigned_route(db, driver)
        next_stop = self._next_stop.resolve(db, driver)
        state = str(order.state)
        leg_meta = self._leg_metadata(state, stop_meta)

        return {
            **self._job_summary(
                db,
                driver,
                order,
                next_order_id=next_stop.get("order_id") if next_stop else None,
            ),
            "route_id": route.route_id if route else None,
            "special_instructions": order.special_instructions,
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
            "timeline": timeline,
            "photos": photos,
            "signatures": signatures,
            "documents": documents,
            "proof_of_delivery": {
                "completed": str(order.state) in ("POD_COMPLETED", "CLOSED", "INVOICED"),
                "proofs": proofs,
                "otp_verified": bool(stop_meta.get("delivery_otp_hash")),
            },
            "otp_required": True,
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
            "amount_cents": order.amount_cents,
            "currency": order.currency,
            "scheduled_at": order.scheduled_at.isoformat() if order.scheduled_at else None,
            "updated_at": order.updated_at.isoformat() if order.updated_at else None,
        }

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

    def _require_order(self, db: Session, driver_id: str, order_id: str):
        from porterchain_api.models import Order

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
    ) -> dict[str, Any]:
        state = str(order.state)
        bucket = force_bucket or self._bucket_for_order(state, order.id, next_order_id)
        pickup = order.pickup or {}
        dropoff = order.dropoff or {}
        urgency = compute_urgency(order)
        ranks = priority_ranks or {}
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
