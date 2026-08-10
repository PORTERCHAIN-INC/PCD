"""Driver 360 — admin driver command center aggregation.

Per masterrule.md: driver approval, verification, wallet, payouts, support,
documents and compliance are Porterchain-owned. Operational dispatch/GPS/routes
belong to Fleetbase and are reached only via the Porterchain API/adapter — this
service reads the Porterchain order mirror and never calls Fleetbase directly.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, time, timedelta
from typing import Any

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from porterchain_api.admin_models import Claim, Driver, DriverPayout, Vehicle
from porterchain_api.crm_models import CrmActivity, CrmSalesTask
from porterchain_api.models import Order, OrderException

COMPLETED_STATES = ("DELIVERED", "POD_COMPLETED", "INVOICED", "CLOSED")
ACTIVE_STATES = (
    "DRIVER_ASSIGNED", "DRIVER_ACCEPTED", "DRIVER_EN_ROUTE", "AT_PICKUP",
    "PICKED_UP", "IN_TRANSIT", "AT_DESTINATION",
)
NEGATIVE_STATES = ("DRIVER_REJECTED", "CANCELLED", "FAILED", "RETURN_TO_SENDER", "LOST", "DAMAGED")


def _now() -> datetime:
    return datetime.now(UTC)


def _naive_now() -> datetime:
    """UTC naive now for timestamp comparisons against DB datetimes."""
    return datetime.now(UTC).replace(tzinfo=None)


def _as_naive(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(UTC).replace(tzinfo=None)
    return dt


def _on_or_after(dt: datetime | None, cutoff: datetime) -> bool:
    naive = _as_naive(dt)
    return naive is not None and naive >= cutoff


class Driver360Service:
    # ------------------------------------------------------------------ #
    # Metrics
    # ------------------------------------------------------------------ #
    def _metrics(self, db: Session, driver: Driver) -> dict[str, Any]:
        base = db.query(Order).filter(Order.assigned_driver_id == driver.id)
        all_orders = base.all()
        now = _naive_now()
        sod = datetime.combine(now.date(), time.min)
        week = now - timedelta(days=7)
        month = now - timedelta(days=30)

        def revenue(orders: list[Order]) -> int:
            return sum(o.amount_cents for o in orders if o.state in COMPLETED_STATES)

        today_orders = [o for o in all_orders if _on_or_after(o.created_at, sod)]
        completed_today = [o for o in today_orders if o.state in COMPLETED_STATES]
        in_progress = [o for o in all_orders if o.state in ACTIVE_STATES]
        week_orders = [o for o in all_orders if _on_or_after(o.created_at, week)]
        month_orders = [o for o in all_orders if _on_or_after(o.created_at, month)]

        total = len(all_orders)
        completed = len([o for o in all_orders if o.state in COMPLETED_STATES])
        rejected = len([o for o in all_orders if o.state == "DRIVER_REJECTED"])
        cancelled = len([o for o in all_orders if o.state in ("CANCELLED", "FAILED")])

        perf = driver.performance or {}
        acceptance = perf.get("acceptance_rate")
        completion = perf.get("completion_rate")
        on_time = perf.get("on_time_percent")
        if acceptance is None:
            acceptance = round((1 - rejected / total) * 100, 1) if total else 100.0
        if completion is None:
            completion = round((completed / total) * 100, 1) if total else 0.0
        cancellation_rate = round((cancelled / total) * 100, 1) if total else 0.0

        # D-36: earnings SSOT = DriverFinanceService (wallet txns), not raw DriverPayout sum.
        from porterchain_api.billing_engine.driver_finance_service import DriverFinanceService

        fin = DriverFinanceService().driver_earnings_snapshot(db, driver)
        weekly_earnings = int(fin.get("week_cents") or 0)
        pending_payout = sum(
            int(p.get("amount_cents") or 0)
            for p in (fin.get("payout_history") or [])
            if str(p.get("status") or "").lower() == "pending"
        )
        if not pending_payout:
            pending_payout = sum(
                p.amount_cents
                for p in db.query(DriverPayout)
                .filter(DriverPayout.driver_id == driver.id, DriverPayout.status == "pending")
                .all()
            )

        incidents = (
            db.query(func.count(OrderException.id))
            .join(Order, Order.id == OrderException.order_id)
            .filter(Order.assigned_driver_id == driver.id)
            .scalar()
            or 0
        )
        last_order = base.order_by(Order.created_at.desc()).first()
        return {
            "orders_today": len(today_orders),
            "in_progress": len(in_progress),
            "completed_today": len(completed_today),
            "revenue_today_cents": revenue(today_orders),
            "revenue_week_cents": revenue(week_orders),
            "revenue_month_cents": revenue(month_orders),
            "lifetime_orders": total,
            "lifetime_completed": completed,
            "acceptance_rate": acceptance,
            "completion_rate": completion,
            "cancellation_rate": cancellation_rate,
            "on_time_percent": on_time if on_time is not None else (completion if total else 0.0),
            "weekly_earnings_cents": weekly_earnings,
            "wallet_balance_cents": int(fin.get("wallet_balance_cents") or driver.wallet_balance_cents or 0),
            "pending_payout_cents": pending_payout,
            "incidents": incidents,
            "last_active_at": (last_order.created_at if last_order else driver.updated_at),
        }

    def _verification_score(self, driver: Driver) -> int:
        score = 0
        if driver.license_verified:
            score += 1
        if driver.insurance_verified:
            score += 1
        if driver.vehicle_verified:
            score += 1
        if driver.background_check_status in ("passed", "cleared", "approved"):
            score += 1
        return score

    def _health(self, driver: Driver, metrics: dict) -> int:
        score = 50
        if driver.status == "APPROVED":
            score += 10
        elif driver.status in ("SUSPENDED", "REJECTED"):
            score -= 30
        elif driver.status == "PENDING":
            score -= 10
        if driver.rating is not None:
            score += int((driver.rating - 4.0) * 20)  # 5.0 → +20, 4.0 → 0, lower negative
        score += self._verification_score(driver) * 4
        if metrics["completion_rate"] >= 95:
            score += 8
        if metrics["cancellation_rate"] > 10:
            score -= 10
        score -= min(20, metrics["incidents"] * 5)
        if metrics["orders_today"] > 0:
            score += 5
        return max(0, min(100, score))

    def _ai(self, driver: Driver, metrics: dict, vehicles: list[Vehicle]) -> dict:
        fraud = "low"
        if metrics["cancellation_rate"] > 25 or (metrics["lifetime_orders"] > 5 and metrics["acceptance_rate"] < 40):
            fraud = "high"
        elif metrics["cancellation_rate"] > 12:
            fraud = "medium"

        burnout = "low"
        if metrics["orders_today"] >= 15:
            burnout = "high"
        elif metrics["orders_today"] >= 10:
            burnout = "medium"

        late_risk = "low"
        if metrics["on_time_percent"] < 80:
            late_risk = "high"
        elif metrics["on_time_percent"] < 92:
            late_risk = "medium"

        maintenance = "low"
        soon = _now().date() + timedelta(days=30)
        for v in vehicles:
            if v.compliance_expires_at and v.compliance_expires_at.date() <= soon:
                maintenance = "high"
                break

        payout_anomaly = "high" if metrics["pending_payout_cents"] > 200000 else "low"

        suggestions: list[str] = []
        if self._verification_score(driver) < 4:
            suggestions.append("Complete verification (license / insurance / vehicle / background).")
        if late_risk != "low":
            suggestions.append("On-time rate is slipping — recommend route-planning training.")
        if burnout != "low":
            suggestions.append("High daily order load — monitor for burnout and rest compliance.")
        if maintenance == "high":
            suggestions.append("Vehicle compliance expiring within 30 days — schedule inspection.")
        if metrics["incidents"] > 0:
            suggestions.append("Open incidents on record — review and recommend safety training.")
        if not suggestions:
            suggestions.append("Driver performing well — consider for peak-hour bonus campaigns.")

        training = []
        if metrics["incidents"] > 0 or (driver.rating or 5) < 4.5:
            training.append("Safety & customer-service refresher")
        if late_risk != "low":
            training.append("Route optimization")
        if not training:
            training.append("Up to date")

        return {
            "fraud_risk": fraud,
            "burnout_risk": burnout,
            "late_delivery_risk": late_risk,
            "maintenance_risk": maintenance,
            "payout_anomaly": payout_anomaly,
            "recommended_training": training,
            "suggested_actions": suggestions,
        }

    def _primary_vehicle(self, db: Session, driver_id: str) -> Vehicle | None:
        return (
            db.query(Vehicle)
            .filter(Vehicle.driver_id == driver_id, Vehicle.is_active == True)  # noqa: E712
            .order_by(Vehicle.created_at.asc())
            .first()
        )

    def _row(self, db: Session, driver: Driver, *, light: bool = False) -> dict[str, Any]:
        metrics = self._metrics(db, driver)
        health = self._health(driver, metrics)
        vehicle = self._primary_vehicle(db, driver.id)
        docs = driver.documents or {}
        row = {
            "id": driver.id,
            "full_name": driver.full_name,
            "email": driver.email,
            "phone": driver.phone,
            "photo_url": docs.get("photo_url"),
            "status": driver.status,
            # Online/availability intentionally omitted — Fleetbase owns live driver state.
            "vehicle": vehicle.make_model if vehicle else None,
            "vehicle_type": vehicle.vehicle_class if vehicle else None,
            "license_class": docs.get("license_class"),
            "service_area": docs.get("service_area"),
            "province": (docs.get("address") or {}).get("province") if isinstance(docs.get("address"), dict) else docs.get("province"),
            "city": (docs.get("address") or {}).get("city") if isinstance(docs.get("address"), dict) else docs.get("city"),
            "rating": driver.rating,
            "acceptance_rate": metrics["acceptance_rate"],
            "completion_rate": metrics["completion_rate"],
            "orders_today": metrics["orders_today"],
            "weekly_earnings_cents": metrics["weekly_earnings_cents"],
            "outstanding_payout_cents": metrics["pending_payout_cents"],
            "wallet_balance_cents": driver.wallet_balance_cents,
            "health_score": health,
            "license_verified": driver.license_verified,
            "insurance_verified": driver.insurance_verified,
            "vehicle_verified": driver.vehicle_verified,
            "medical_transport_certified": bool(driver.medical_transport_certified),
            "background_check_status": driver.background_check_status,
            "fleetbase_driver_id": driver.fleetbase_driver_id,
            "last_active_at": metrics["last_active_at"],
            "created_at": driver.created_at,
            "tags": docs.get("tags") or [],
        }
        if not light:
            row["metrics"] = metrics
        return row

    # ------------------------------------------------------------------ #
    # List / facets / stats
    # ------------------------------------------------------------------ #
    def list_drivers(
        self,
        db: Session,
        *,
        status: str | None = None,
        background_check: str | None = None,
        search: str | None = None,
        limit: int = 1000,
    ) -> list[dict]:
        q = db.query(Driver)
        if status:
            q = q.filter(Driver.status == status)
        if background_check:
            q = q.filter(Driver.background_check_status == background_check)
        if search:
            like = f"%{search}%"
            q = q.filter(or_(Driver.full_name.ilike(like), Driver.email.ilike(like), Driver.phone.ilike(like)))
        drivers = q.order_by(Driver.created_at.desc()).limit(limit).all()
        return [self._row(db, d, light=True) for d in drivers]

    def facets(self, db: Session) -> dict:
        status_rows = db.query(Driver.status, func.count(Driver.id)).group_by(Driver.status).all()
        bg_rows = (
            db.query(Driver.background_check_status, func.count(Driver.id))
            .group_by(Driver.background_check_status)
            .all()
        )
        vehicle_rows = db.query(Vehicle.vehicle_class, func.count(Vehicle.id)).group_by(Vehicle.vehicle_class).all()
        return {
            "statuses": [{"value": s, "count": n} for s, n in status_rows if s],
            "background_check": [{"value": s, "count": n} for s, n in bg_rows if s],
            "vehicle_types": [{"value": s, "count": n} for s, n in vehicle_rows if s],
        }

    def stats(self, db: Session) -> dict:
        total = db.query(func.count(Driver.id)).scalar() or 0
        approved = db.query(func.count(Driver.id)).filter(Driver.status == "APPROVED").scalar() or 0
        pending = db.query(func.count(Driver.id)).filter(Driver.status == "PENDING").scalar() or 0
        suspended = db.query(func.count(Driver.id)).filter(Driver.status == "SUSPENDED").scalar() or 0
        pending_payout = (
            db.query(func.coalesce(func.sum(DriverPayout.amount_cents), 0))
            .filter(DriverPayout.status == "pending")
            .scalar()
            or 0
        )
        return {
            "total": total,
            "approved": approved,
            "pending": pending,
            "suspended": suspended,
            # "online" count removed — live driver state is Fleetbase-owned.
            "pending_payout_cents": int(pending_payout),
        }

    # ------------------------------------------------------------------ #
    # Detail + sub-resources
    # ------------------------------------------------------------------ #
    def detail(self, db: Session, driver_id: str) -> dict | None:
        driver = db.get(Driver, driver_id)
        if not driver:
            return None
        metrics = self._metrics(db, driver)
        health = self._health(driver, metrics)
        vehicles = db.query(Vehicle).filter(Vehicle.driver_id == driver_id).all()
        ai = self._ai(driver, metrics, vehicles)
        row = self._row(db, driver, light=False)
        row.update(
            {
                "health": health,
                "ai": ai,
                "documents": driver.documents or {},
                "performance": driver.performance or {},
                "fleetbase_driver_id": driver.fleetbase_driver_id,
                "counts": {
                    "vehicles": len(vehicles),
                    "open_tasks": db.query(CrmSalesTask).filter(
                        CrmSalesTask.entity_id == driver_id,
                        CrmSalesTask.status.in_(["open", "in_progress"]),
                    ).count(),
                    "incidents": metrics["incidents"],
                    "payouts": db.query(DriverPayout).filter(DriverPayout.driver_id == driver_id).count(),
                },
            }
        )
        return row

    def orders(self, db: Session, driver_id: str, *, state: str | None = None, limit: int = 200) -> list[dict]:
        q = db.query(Order).filter(Order.assigned_driver_id == driver_id)
        if state:
            q = q.filter(Order.state == state)
        rows = q.order_by(Order.created_at.desc()).limit(limit).all()
        return [
            {
                "id": o.id,
                "order_number": o.order_number,
                "tracking_number": o.tracking_number,
                "state": o.state,
                "amount_cents": o.amount_cents,
                "scheduled_at": o.scheduled_at.isoformat() if o.scheduled_at else None,
                "created_at": o.created_at.isoformat() if o.created_at else None,
                "dropoff": o.dropoff,
            }
            for o in rows
        ]

    def vehicles(self, db: Session, driver_id: str) -> list[dict]:
        rows = db.query(Vehicle).filter(Vehicle.driver_id == driver_id).order_by(Vehicle.created_at.asc()).all()
        return [
            {
                "id": v.id,
                "vehicle_class": v.vehicle_class,
                "plate_number": v.plate_number,
                "make_model": v.make_model,
                "capacity_kg": v.capacity_kg,
                "compliance_expires_at": v.compliance_expires_at.isoformat() if v.compliance_expires_at else None,
                "is_active": v.is_active,
            }
            for v in rows
        ]

    def payouts(self, db: Session, driver_id: str) -> dict:
        rows = (
            db.query(DriverPayout)
            .filter(DriverPayout.driver_id == driver_id)
            .order_by(DriverPayout.created_at.desc())
            .all()
        )
        driver = db.get(Driver, driver_id)
        return {
            "wallet_balance_cents": driver.wallet_balance_cents if driver else 0,
            "pending_cents": sum(p.amount_cents for p in rows if p.status == "pending"),
            "paid_cents": sum(p.amount_cents for p in rows if p.status == "paid"),
            "payouts": [
                {
                    "id": p.id,
                    "amount_cents": p.amount_cents,
                    "currency": p.currency,
                    "status": p.status,
                    "reference": p.reference,
                    "created_at": p.created_at.isoformat(),
                }
                for p in rows
            ],
        }

    def documents(self, db: Session, driver_id: str) -> dict:
        driver = db.get(Driver, driver_id)
        if not driver:
            raise LookupError("driver_not_found")
        docs = driver.documents or {}
        vehicles = db.query(Vehicle).filter(Vehicle.driver_id == driver_id).all()
        return {
            "verification": {
                "license_verified": driver.license_verified,
                "insurance_verified": driver.insurance_verified,
                "vehicle_verified": driver.vehicle_verified,
                "background_check_status": driver.background_check_status,
            },
            "files": docs.get("files") or [],
            "expiries": [
                {"label": f"{v.make_model or v.vehicle_class} compliance", "expires_at": v.compliance_expires_at.isoformat()}
                for v in vehicles
                if v.compliance_expires_at
            ],
            "raw": docs,
        }

    def incidents(self, db: Session, driver_id: str) -> dict:
        from porterchain_api.admin_models import SupportTicket
        from porterchain_api.support_engine.claims_constants import claim_meta

        exc = (
            db.query(OrderException)
            .join(Order, Order.id == OrderException.order_id)
            .filter(Order.assigned_driver_id == driver_id)
            .order_by(OrderException.created_at.desc())
            .all()
        )
        # D-31: current assignee OR snapshot driver_id in claim evidence._meta
        by_assignee = {
            c.id: c
            for c in (
                db.query(Claim)
                .join(Order, Order.id == Claim.order_id)
                .filter(Order.assigned_driver_id == driver_id)
                .order_by(Claim.created_at.desc())
                .limit(100)
                .all()
            )
        }
        for c in (
            db.query(Claim).order_by(Claim.created_at.desc()).limit(300).all()
        ):
            if claim_meta(c).get("driver_id") == driver_id:
                by_assignee[c.id] = c
        claims = sorted(
            by_assignee.values(),
            key=lambda c: c.created_at or datetime.min,
            reverse=True,
        )

        tickets = (
            db.query(SupportTicket)
            .filter(SupportTicket.driver_id == driver_id)
            .order_by(SupportTicket.created_at.desc())
            .limit(100)
            .all()
        )
        return {
            "incidents": [
                {
                    "id": e.id,
                    "type": e.type,
                    "status": e.status,
                    "order_id": e.order_id,
                    "created_at": e.created_at.isoformat() if e.created_at else None,
                }
                for e in exc
            ],
            "claims": [
                {
                    "id": c.id,
                    "claim_type": c.claim_type,
                    "status": c.status,
                    "order_id": c.order_id,
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                }
                for c in claims
            ],
            "support_tickets": [
                {
                    "id": t.id,
                    "subject": t.subject,
                    "status": t.status,
                    "order_id": t.order_id,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                }
                for t in tickets
            ],
        }

    def analytics(self, db: Session, driver_id: str) -> dict:
        orders = db.query(Order).filter(Order.assigned_driver_id == driver_id).all()
        by_month: dict[str, dict[str, int]] = defaultdict(lambda: {"orders": 0, "completed": 0, "revenue_cents": 0})
        for o in orders:
            key = o.created_at.strftime("%Y-%m") if o.created_at else "unknown"
            by_month[key]["orders"] += 1
            if o.state in COMPLETED_STATES:
                by_month[key]["completed"] += 1
                by_month[key]["revenue_cents"] += o.amount_cents
        months = sorted(by_month.keys())[-12:]
        return {
            "by_month": [{"month": m, **by_month[m]} for m in months],
            "lifetime_orders": len(orders),
        }

    def timeline(self, db: Session, driver_id: str) -> list[dict]:
        events: list[dict] = []
        acts = (
            db.query(CrmActivity)
            .filter(CrmActivity.entity_type == "driver", CrmActivity.entity_id == driver_id)
            .order_by(CrmActivity.occurred_at.desc())
            .limit(40)
            .all()
        )
        for a in acts:
            events.append({"kind": "activity", "type": a.activity_type, "title": a.subject or a.body or a.activity_type, "at": a.occurred_at.isoformat()})
        orders = (
            db.query(Order).filter(Order.assigned_driver_id == driver_id).order_by(Order.created_at.desc()).limit(30).all()
        )
        for o in orders:
            events.append({"kind": "order", "type": o.state, "title": f"Order {o.order_number} — {o.state}", "at": o.created_at.isoformat() if o.created_at else None})
        payouts = (
            db.query(DriverPayout).filter(DriverPayout.driver_id == driver_id).order_by(DriverPayout.created_at.desc()).limit(20).all()
        )
        for p in payouts:
            events.append({"kind": "payout", "type": p.status, "title": f"Payout {p.reference or ''} — {p.status}", "at": p.created_at.isoformat()})
        events.sort(key=lambda e: e["at"] or "", reverse=True)
        return events[:80]
