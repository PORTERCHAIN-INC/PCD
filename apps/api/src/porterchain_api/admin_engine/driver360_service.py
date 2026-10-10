"""Driver 360 — admin driver command center aggregation.

Per masterrule.md: driver approval, verification, wallet, payouts, support,
documents and compliance are Porterchain-owned. Operational dispatch/GPS/routes
come from shifts and last-known GPS; this service reads PorterChain orders.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.driver360_board import (
    ai_payload,
    analytics_payload,
    detail_payload,
    driver_row,
    health_score,
    incidents_payload,
    metrics_payload,
    timeline_payload,
    verification_score,
)
from porterchain_api.admin_models import Driver, DriverPayout, Vehicle
from porterchain_api.booking_models import Order


class Driver360Service:
    # ------------------------------------------------------------------ #
    # Metrics
    # ------------------------------------------------------------------ #
    def _metrics(self, db: Session, driver: Driver) -> dict[str, Any]:
        # D-36: earnings SSOT = DriverFinanceService (wallet txns), not raw DriverPayout sum.
        from porterchain_api.billing_engine.driver_finance_service import (
            DriverFinanceService,
        )

        return metrics_payload(db, driver, finance=DriverFinanceService().driver_earnings_snapshot(db, driver))

    def _verification_score(self, driver: Driver) -> int:
        return verification_score(driver)

    def _health(self, driver: Driver, metrics: dict) -> int:
        return health_score(driver, metrics)

    def _ai(self, driver: Driver, metrics: dict, vehicles: list[Vehicle], db: Session | None = None) -> dict:
        return ai_payload(driver, metrics, vehicles, db=db)

    def _primary_vehicle(self, db: Session, driver_id: str) -> Vehicle | None:
        return (
            db.query(Vehicle)
            .filter(Vehicle.driver_id == driver_id, Vehicle.is_active == True)
            .order_by(Vehicle.created_at.asc())
            .first()
        )

    def _row(self, db: Session, driver: Driver, *, light: bool = False) -> dict[str, Any]:
        return driver_row(self, db, driver, light=light)

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
            # Live driver state is on Dispatch → Fleet.
            "pending_payout_cents": int(pending_payout),
        }

    # ------------------------------------------------------------------ #
    # Detail + sub-resources
    # ------------------------------------------------------------------ #
    def detail(self, db: Session, driver_id: str) -> dict | None:
        driver = db.get(Driver, driver_id)
        if not driver:
            return None
        return detail_payload(self, db, driver)

    def orders(
        self,
        db: Session,
        driver_id: str,
        *,
        state: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        from porterchain_api.platform.pagination import (
            MAX_EMBEDDED_LIST_LIMIT,
            as_page,
            clamp_page,
        )

        limit, offset = clamp_page(limit, offset, max_limit=MAX_EMBEDDED_LIST_LIMIT)
        q = db.query(Order).filter(Order.assigned_driver_id == driver_id)
        if state:
            q = q.filter(Order.state == state)
        q = q.order_by(Order.created_at.desc(), Order.id.desc())
        total = q.count()
        rows = q.offset(offset).limit(limit).all()
        active_classes = [
            v.vehicle_class
            for v in db.query(Vehicle)
            .filter(Vehicle.driver_id == driver_id, Vehicle.is_active.is_(True))
            .all()
            if v.vehicle_class
        ]
        items = [
            {
                "id": o.id,
                "order_number": o.order_number,
                "tracking_number": o.tracking_number,
                "state": o.state,
                "amount_cents": o.amount_cents,
                "scheduled_at": o.scheduled_at.isoformat() if o.scheduled_at else None,
                "created_at": o.created_at.isoformat() if o.created_at else None,
                "dropoff": o.dropoff,
                "pickup": o.pickup,
                "vehicle_classes": active_classes,
            }
            for o in rows
        ]
        return as_page(items, total, limit, offset)

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
        from porterchain_api.driver_engine.wallet_ledger import wallet_balance_cents

        return {
            "wallet_balance_cents": (
                wallet_balance_cents(db, driver_id, cached_cents=driver.wallet_balance_cents) if driver else 0
            ),
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
        from porterchain_api.admin_engine.driver360_board import (
            verification_quality_bonus,
        )
        from porterchain_api.admin_engine.driver_documents import admin_review_files
        from porterchain_api.driver_engine.verification_sources import (
            verification_sources_payload,
        )

        driver = db.get(Driver, driver_id)
        if not driver:
            raise LookupError("driver_not_found")
        docs = driver.documents or {}
        vehicles = db.query(Vehicle).filter(Vehicle.driver_id == driver_id).all()
        sources = verification_sources_payload(driver)
        return {
            "verification": {
                "license_verified": driver.license_verified,
                "insurance_verified": driver.insurance_verified,
                "vehicle_verified": driver.vehicle_verified,
                "background_check_status": driver.background_check_status,
                "abstract_verified": bool(sources.get("abstract", {}).get("verified")),
                "score": self._verification_score(driver),
                "quality_bonus": verification_quality_bonus(driver),
            },
            "sources": sources,
            "files": admin_review_files(docs),
            "expiries": [
                {
                    "label": f"{v.make_model or v.vehicle_class} compliance",
                    "expires_at": v.compliance_expires_at.isoformat(),
                }
                for v in vehicles
                if v.compliance_expires_at
            ],
        }

    def incidents(self, db: Session, driver_id: str) -> dict:
        from porterchain_api.support_engine.claims_constants import claim_meta

        return incidents_payload(db, driver_id, claim_meta=claim_meta)

    def analytics(self, db: Session, driver_id: str) -> dict:
        return analytics_payload(db, driver_id)

    def timeline(self, db: Session, driver_id: str) -> list[dict]:
        return timeline_payload(db, driver_id)
