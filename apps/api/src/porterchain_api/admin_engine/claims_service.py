"""Enterprise claims management — Application Service (masterrule §3).

Claims are Porterchain business objects; logistics execution context comes from
the order mirror and Fleetbase sync — never direct Fleetbase HTTP from here.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.admin_models import AdminUser, Claim, Driver
from porterchain_api.booking_engine._core import emit_event, publish_recorded_event, _event_fields
from porterchain_api.admin_engine import events as E
from porterchain_api.merchant_models import Merchant
from porterchain_api.models import Customer, DomainEvent, Order
from porterchain_shared.events.catalog import DomainEventType

CLAIM_TYPES = frozenset({
    "lost_parcel",
    "damaged_parcel",
    "missing_items",
    "wrong_delivery",
    "late_delivery",
    "pickup_failed",
    "delivery_failed",
    "customer_complaint",
    "merchant_complaint",
    "driver_complaint",
    "vehicle_damage",
    "insurance_claim",
    "payment_dispute",
    "chargeback",
    "fraud_investigation",
    "internal_investigation",
    "compliance_issue",
    "other",
    # legacy Fleetbase webhook types
    "damage",
    "loss",
    "general",
})

CLAIM_STATUSES = frozenset({
    "new",
    "assigned",
    "under_investigation",
    "waiting_customer",
    "waiting_merchant",
    "waiting_driver",
    "waiting_insurance",
    "approved",
    "rejected",
    "compensated",
    "closed",
    "archived",
    # legacy
    "open",
    "investigating",
    "resolved",
})

LEGACY_STATUS_MAP = {
    "open": "new",
    "investigating": "under_investigation",
    "resolved": "compensated",
}


def claim_number(claim_id: str) -> str:
    return f"PCC-{claim_id[:8].upper()}"


def _normalize_status(status: str) -> str:
    return LEGACY_STATUS_MAP.get(status, status)


def _meta(claim: Claim) -> dict[str, Any]:
    return dict((claim.evidence or {}).get("_meta") or {})


def _set_meta(claim: Claim, **updates: Any) -> None:
    ev = dict(claim.evidence or {})
    meta = dict(ev.get("_meta") or {})
    meta.update(updates)
    ev["_meta"] = meta
    claim.evidence = ev


@dataclass
class ClaimFilters:
    status: str | None = None
    claim_type: str | None = None
    priority: str | None = None
    investigator_id: str | None = None
    merchant_id: str | None = None
    driver_id: str | None = None
    insurance: bool | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    amount_min_cents: int | None = None
    amount_max_cents: int | None = None
    risk_min: int | None = None
    search: str | None = None
    limit: int = 500


class AdminClaimsService:
    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _order_context(self, db: Session, order_id: str) -> dict[str, Any]:
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            return {}
        merchant = (
            db.query(Merchant).filter(Merchant.id == order.merchant_id).first()
            if order.merchant_id
            else None
        )
        customer = (
            db.query(Customer).filter(Customer.id == order.customer_id).first()
            if order.customer_id
            else None
        )
        driver = (
            db.query(Driver).filter(Driver.id == order.assigned_driver_id).first()
            if order.assigned_driver_id
            else None
        )
        investigator = None
        return {
            "order": order,
            "tracking_number": order.tracking_number,
            "order_number": order.order_number,
            "amount_cents": order.amount_cents,
            "merchant_id": order.merchant_id,
            "merchant_name": merchant.company_name if merchant else None,
            "customer_id": order.customer_id,
            "customer_email": customer.email if customer else None,
            "customer_phone": customer.phone if customer else None,
            "driver_id": order.assigned_driver_id,
            "driver_name": driver.full_name if driver else None,
        }

    def _claim_amount(self, claim: Claim, ctx: dict[str, Any]) -> int:
        comp = (claim.resolution or {}).get("compensation") or {}
        if comp.get("claim_amount_cents"):
            return int(comp["claim_amount_cents"])
        return int(ctx.get("amount_cents") or 0)

    def _risk_score(self, claim: Claim, ctx: dict[str, Any]) -> int:
        meta = _meta(claim)
        if meta.get("risk_score") is not None:
            return int(meta["risk_score"])
        score = 20
        ctype = claim.claim_type or ""
        if ctype in ("fraud_investigation", "chargeback", "payment_dispute"):
            score += 40
        if ctype in ("lost_parcel", "damaged_parcel"):
            score += 25
        amount = self._claim_amount(claim, ctx)
        if amount >= 50000:
            score += 20
        elif amount >= 20000:
            score += 10
        status = _normalize_status(claim.status)
        if status.startswith("waiting_"):
            score += 15
        return min(100, score)

    def _append_timeline(
        self,
        db: Session,
        claim: Claim,
        *,
        label: str,
        actor_type: str = "system",
        actor_id: str | None = None,
        payload: dict | None = None,
    ) -> None:
        ev = dict(claim.evidence or {})
        timeline = list(ev.get("timeline") or [])
        timeline.append(
            {
                "id": str(uuid.uuid4()),
                "label": label,
                "actor_type": actor_type,
                "actor_id": actor_id,
                "occurred_at": datetime.now(UTC).isoformat(),
                "payload": payload or {},
            }
        )
        ev["timeline"] = timeline
        claim.evidence = ev
        emit_event(
            db,
            event_type=f"claim.{label.lower().replace(' ', '_')}",
            aggregate_type="claim",
            aggregate_id=claim.id,
            actor_type=actor_type,
            actor_id=actor_id,
            payload={"label": label, **(payload or {})},
        )

    def _row(self, db: Session, claim: Claim) -> dict[str, Any]:
        ctx = self._order_context(db, claim.order_id)
        meta = _meta(claim)
        investigator_id = claim.assigned_to
        investigator_name = None
        if investigator_id:
            inv = db.query(AdminUser).filter(AdminUser.id == investigator_id).first()
            investigator_name = inv.name or inv.email if inv else None
        insurance = (claim.resolution or {}).get("insurance") or {}
        return {
            "id": claim.id,
            "claim_number": claim_number(claim.id),
            "claim_type": claim.claim_type,
            "priority": meta.get("priority", "normal"),
            "status": claim.status,
            "display_status": _normalize_status(claim.status),
            "merchant_id": ctx.get("merchant_id"),
            "merchant_name": ctx.get("merchant_name"),
            "customer_id": ctx.get("customer_id"),
            "customer_email": ctx.get("customer_email"),
            "driver_id": ctx.get("driver_id"),
            "driver_name": ctx.get("driver_name"),
            "order_id": claim.order_id,
            "tracking_number": ctx.get("tracking_number"),
            "order_number": ctx.get("order_number"),
            "amount_cents": self._claim_amount(claim, ctx),
            "has_insurance": bool(insurance.get("provider")),
            "assigned_investigator_id": investigator_id,
            "assigned_investigator": investigator_name,
            "risk_score": self._risk_score(claim, ctx),
            "description": claim.description,
            "created_at": claim.created_at,
            "updated_at": claim.resolved_at or claim.created_at,
            "resolved_at": claim.resolved_at,
        }

    # ------------------------------------------------------------------ #
    # List / search / dashboard / reports
    # ------------------------------------------------------------------ #
    def list_claims(self, db: Session, *, status: str | None = None, limit: int = 50) -> list[Claim]:
        """Legacy list — prefer list_enriched."""
        q = db.query(Claim)
        if status:
            q = q.filter(Claim.status == status)
        return q.order_by(Claim.created_at.desc()).limit(limit).all()

    def list_enriched(self, db: Session, filters: ClaimFilters) -> list[dict[str, Any]]:
        q = db.query(Claim).order_by(Claim.created_at.desc())
        if filters.status:
            q = q.filter(Claim.status == filters.status)
        if filters.claim_type:
            q = q.filter(Claim.claim_type == filters.claim_type)
        if filters.date_from:
            q = q.filter(Claim.created_at >= filters.date_from)
        if filters.date_to:
            q = q.filter(Claim.created_at <= filters.date_to)
        if filters.search:
            like = f"%{filters.search}%"
            order_ids = [
                o.id
                for o in db.query(Order)
                .filter(
                    or_(
                        Order.tracking_number.ilike(like),
                        Order.order_number.ilike(like),
                    )
                )
                .limit(200)
                .all()
            ]
            clauses = [
                Claim.id.ilike(like),
                Claim.order_id.ilike(like),
                Claim.claim_type.ilike(like),
            ]
            if order_ids:
                clauses.append(Claim.order_id.in_(order_ids))
            q = q.filter(or_(*clauses))
        rows = q.limit(filters.limit).all()
        out: list[dict[str, Any]] = []
        for claim in rows:
            row = self._row(db, claim)
            if filters.priority and row["priority"] != filters.priority:
                continue
            if filters.investigator_id and row["assigned_investigator_id"] != filters.investigator_id:
                continue
            if filters.merchant_id and row["merchant_id"] != filters.merchant_id:
                continue
            if filters.driver_id and row["driver_id"] != filters.driver_id:
                continue
            if filters.insurance is True and not row["has_insurance"]:
                continue
            if filters.insurance is False and row["has_insurance"]:
                continue
            if filters.amount_min_cents is not None and row["amount_cents"] < filters.amount_min_cents:
                continue
            if filters.amount_max_cents is not None and row["amount_cents"] > filters.amount_max_cents:
                continue
            if filters.risk_min is not None and row["risk_score"] < filters.risk_min:
                continue
            out.append(row)
        return out

    def dashboard(self, db: Session) -> dict[str, Any]:
        now = datetime.now(UTC).replace(tzinfo=None)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        def count_status(*statuses: str) -> int:
            return db.query(func.count(Claim.id)).filter(Claim.status.in_(statuses)).scalar() or 0

        open_statuses = ("new", "open", "assigned", "under_investigation", "investigating")
        resolved_statuses = ("compensated", "closed", "resolved")
        rejected_statuses = ("rejected",)

        all_claims = db.query(Claim).all()
        compensation_total = 0
        resolution_hours: list[float] = []
        for c in all_claims:
            comp = (c.resolution or {}).get("compensation") or {}
            compensation_total += int(comp.get("approved_amount_cents") or 0)
            if c.resolved_at and c.created_at:
                hrs = (c.resolved_at.replace(tzinfo=None) - c.created_at.replace(tzinfo=None)).total_seconds() / 3600
                resolution_hours.append(hrs)
        avg_resolution_hours = round(sum(resolution_hours) / len(resolution_hours), 1) if resolution_hours else 0.0

        monthly = db.query(func.count(Claim.id)).filter(Claim.created_at >= month_start).scalar() or 0

        risk_scores = [self._risk_score(c, self._order_context(db, c.order_id)) for c in all_claims[:200]]
        avg_risk = round(sum(risk_scores) / len(risk_scores), 1) if risk_scores else 0.0

        return {
            "open_claims": count_status(*open_statuses),
            "under_investigation": count_status("under_investigation", "investigating"),
            "waiting_merchant": count_status("waiting_merchant"),
            "waiting_customer": count_status("waiting_customer"),
            "waiting_driver": count_status("waiting_driver"),
            "insurance_claims": sum(
                1 for c in all_claims if ((c.resolution or {}).get("insurance") or {}).get("provider")
            ),
            "chargebacks": db.query(func.count(Claim.id)).filter(Claim.claim_type.in_(("chargeback", "payment_dispute"))).scalar() or 0,
            "resolved_claims": count_status(*resolved_statuses),
            "rejected_claims": count_status(*rejected_statuses),
            "avg_resolution_hours": avg_resolution_hours,
            "total_compensation_cents": compensation_total,
            "monthly_claims": monthly,
            "avg_risk_score": avg_risk,
        }

    def reports(self, db: Session) -> dict[str, Any]:
        claims = db.query(Claim).all()
        by_type: dict[str, int] = {}
        by_merchant: dict[str, int] = {}
        by_driver: dict[str, int] = {}
        compensation = 0
        insurance_recovery = 0
        causes: dict[str, int] = {}

        for c in claims:
            by_type[c.claim_type] = by_type.get(c.claim_type, 0) + 1
            ctx = self._order_context(db, c.order_id)
            if ctx.get("merchant_name"):
                by_merchant[ctx["merchant_name"]] = by_merchant.get(ctx["merchant_name"], 0) + 1
            if ctx.get("driver_name"):
                by_driver[ctx["driver_name"]] = by_driver.get(ctx["driver_name"], 0) + 1
            comp = (c.resolution or {}).get("compensation") or {}
            compensation += int(comp.get("approved_amount_cents") or 0)
            ins = (c.resolution or {}).get("insurance") or {}
            insurance_recovery += int(ins.get("settlement_cents") or 0)
            inv = (c.evidence or {}).get("investigation") or {}
            rc = inv.get("root_cause") or c.claim_type
            causes[str(rc)] = causes.get(str(rc), 0) + 1

        top_causes = sorted(causes.items(), key=lambda x: x[1], reverse=True)[:10]
        return {
            "by_type": by_type,
            "by_merchant": dict(sorted(by_merchant.items(), key=lambda x: x[1], reverse=True)[:15]),
            "by_driver": dict(sorted(by_driver.items(), key=lambda x: x[1], reverse=True)[:15]),
            "compensation_cost_cents": compensation,
            "insurance_recovery_cents": insurance_recovery,
            "top_causes": [{"cause": k, "count": v} for k, v in top_causes],
        }

    def claim_row(self, db: Session, claim: Claim) -> dict[str, Any]:
        return self._row(db, claim)

    def get_claim(self, db: Session, claim_id: str) -> Claim | None:
        return db.query(Claim).filter(Claim.id == claim_id).first()

    def get_detail(self, db: Session, claim_id: str) -> dict[str, Any] | None:
        claim = self.get_claim(db, claim_id)
        if not claim:
            return None
        row = self._row(db, claim)
        ctx = self._order_context(db, claim.order_id)
        order = ctx.get("order")
        domain_events = (
            db.query(DomainEvent)
            .filter(DomainEvent.aggregate_type == "claim", DomainEvent.aggregate_id == claim.id)
            .order_by(DomainEvent.occurred_at.asc())
            .all()
        )
        ev = claim.evidence or {}
        duplicates = self.find_duplicates(db, claim)
        smart = self.smart_insights(db, claim)

        return {
            **row,
            "description": claim.description,
            "evidence_files": ev.get("files") or [],
            "communications": ev.get("communications") or [],
            "investigation": ev.get("investigation") or {},
            "internal_notes": ev.get("notes") or [],
            "timeline": ev.get("timeline") or [],
            "compensation": (claim.resolution or {}).get("compensation") or {},
            "insurance": (claim.resolution or {}).get("insurance") or {},
            "order": {
                "order_id": order.id if order else claim.order_id,
                "tracking_number": ctx.get("tracking_number"),
                "order_number": ctx.get("order_number"),
                "state": order.state if order else None,
                "amount_cents": ctx.get("amount_cents"),
                "pickup": order.pickup if order else None,
                "dropoff": order.dropoff if order else None,
            }
            if order
            else {"order_id": claim.order_id},
            "domain_events": [
                {
                    "event_type": e.event_type,
                    "occurred_at": e.occurred_at.isoformat() if e.occurred_at else None,
                    "actor_type": e.actor_type,
                    "payload": e.payload,
                }
                for e in domain_events
            ],
            "duplicates": duplicates,
            "smart": smart,
        }

    # ------------------------------------------------------------------ #
    # Mutations
    # ------------------------------------------------------------------ #
    def open_claim(
        self,
        db: Session,
        ctx: AdminContext,
        *,
        order_id: str,
        claim_type: str,
        description: str | None = None,
        priority: str = "normal",
    ) -> Claim:
        normalized_type = claim_type if claim_type in CLAIM_TYPES else "other"
        claim = Claim(
            order_id=order_id,
            claim_type=normalized_type,
            description=description,
            assigned_to=ctx.user.id,
            status="new",
        )
        db.add(claim)
        db.flush()
        _set_meta(claim, priority=priority)
        order = db.query(Order).filter(Order.id == order_id).first()
        customer = (
            db.query(Customer).filter(Customer.id == order.customer_id).first()
            if order and order.customer_id
            else None
        )
        self._append_timeline(
            db, claim, label="Claim Created", actor_type="admin", actor_id=ctx.user.id,
            payload={"claim_type": normalized_type, "order_id": order_id},
        )
        claim_event = _event_fields(
            event_type=E.CLAIM_OPENED,
            aggregate_type="claim",
            aggregate_id=claim.id,
            actor_type="admin",
            actor_id=ctx.user.id,
            payload={
                "order_id": order_id,
                "claim_type": normalized_type,
                "claim_number": claim_number(claim.id),
                "order_number": order.order_number if order else "",
                "email": customer.email if customer else None,
            },
        )
        emit_event(db, publish=False, **claim_event)
        if normalized_type in ("payment_dispute", "chargeback"):
            emit_event(
                db,
                publish=False,
                event_type=DomainEventType.REFUND_REQUESTED,
                aggregate_type="claim",
                aggregate_id=claim.id,
                actor_type="admin",
                actor_id=ctx.user.id,
                correlation_id=order_id,
                payload={
                    "claim_id": claim.id,
                    "order_id": order_id,
                    "claim_type": normalized_type,
                },
            )
        db.commit()
        publish_recorded_event(**claim_event)
        db.refresh(claim)
        return claim

    def update_status(self, db: Session, ctx: AdminContext, claim_id: str, status: str) -> Claim:
        claim = self.get_claim(db, claim_id)
        if not claim:
            raise LookupError("claim_not_found")
        if status not in CLAIM_STATUSES:
            raise ValueError("invalid_status")
        previous = claim.status
        claim.status = status
        if status in ("compensated", "closed", "archived", "resolved", "rejected"):
            claim.resolved_at = datetime.now(UTC)
            emit_event(
                db,
                event_type=E.CLAIM_RESOLVED,
                aggregate_type="claim",
                aggregate_id=claim_id,
                actor_type="admin",
                actor_id=ctx.user.id,
                payload={"from_status": previous, "to_status": status},
            )
        self._append_timeline(
            db, claim, label="Decision Made", actor_type="admin", actor_id=ctx.user.id,
            payload={"from_status": previous, "to_status": status},
        )
        db.commit()
        db.refresh(claim)
        return claim

    def assign_investigator(
        self, db: Session, ctx: AdminContext, claim_id: str, investigator_id: str
    ) -> Claim:
        claim = self.get_claim(db, claim_id)
        if not claim:
            raise LookupError("claim_not_found")
        claim.assigned_to = investigator_id
        if claim.status in ("new", "open"):
            claim.status = "assigned"
        self._append_timeline(
            db, claim, label="Investigator Assigned", actor_type="admin", actor_id=ctx.user.id,
            payload={"investigator_id": investigator_id},
        )
        db.commit()
        db.refresh(claim)
        return claim

    def add_evidence(
        self,
        db: Session,
        ctx: AdminContext,
        claim_id: str,
        *,
        file_type: str,
        name: str,
        url: str | None = None,
        meta: dict | None = None,
    ) -> Claim:
        claim = self.get_claim(db, claim_id)
        if not claim:
            raise LookupError("claim_not_found")
        ev = dict(claim.evidence or {})
        files = list(ev.get("files") or [])
        version = len([f for f in files if f.get("name") == name]) + 1
        files.append(
            {
                "id": str(uuid.uuid4()),
                "type": file_type,
                "name": name,
                "url": url,
                "version": version,
                "uploaded_at": datetime.now(UTC).isoformat(),
                "uploaded_by": ctx.user.id,
                "meta": meta or {},
            }
        )
        ev["files"] = files
        claim.evidence = ev
        self._append_timeline(
            db, claim, label="Evidence Uploaded", actor_type="admin", actor_id=ctx.user.id,
            payload={"file_type": file_type, "name": name},
        )
        db.commit()
        db.refresh(claim)
        return claim

    def add_note(
        self,
        db: Session,
        ctx: AdminContext,
        claim_id: str,
        *,
        body: str,
        internal: bool = True,
        channel: str = "internal",
    ) -> Claim:
        claim = self.get_claim(db, claim_id)
        if not claim:
            raise LookupError("claim_not_found")
        ev = dict(claim.evidence or {})
        notes = list(ev.get("notes") or [])
        notes.append(
            {
                "id": str(uuid.uuid4()),
                "body": body,
                "internal": internal,
                "channel": channel,
                "author_id": ctx.user.id,
                "created_at": datetime.now(UTC).isoformat(),
            }
        )
        ev["notes"] = notes
        if not internal:
            comms = list(ev.get("communications") or [])
            comms.append(
                {
                    "channel": channel,
                    "body": body,
                    "direction": "outbound",
                    "at": datetime.now(UTC).isoformat(),
                }
            )
            ev["communications"] = comms
        claim.evidence = ev
        self._append_timeline(
            db, claim, label="Note Added", actor_type="admin", actor_id=ctx.user.id,
            payload={"internal": internal},
        )
        db.commit()
        db.refresh(claim)
        return claim

    def update_investigation(
        self, db: Session, ctx: AdminContext, claim_id: str, investigation: dict[str, Any]
    ) -> Claim:
        claim = self.get_claim(db, claim_id)
        if not claim:
            raise LookupError("claim_not_found")
        ev = dict(claim.evidence or {})
        current = dict(ev.get("investigation") or {})
        current.update(investigation)
        ev["investigation"] = current
        claim.evidence = ev
        if claim.status in ("new", "open", "assigned"):
            claim.status = "under_investigation"
        self._append_timeline(
            db, claim, label="Investigation Updated", actor_type="admin", actor_id=ctx.user.id,
        )
        db.commit()
        db.refresh(claim)
        return claim

    def set_compensation(
        self, db: Session, ctx: AdminContext, claim_id: str, compensation: dict[str, Any]
    ) -> Claim:
        claim = self.get_claim(db, claim_id)
        if not claim:
            raise LookupError("claim_not_found")
        res = dict(claim.resolution or {})
        res["compensation"] = compensation
        claim.resolution = res
        if compensation.get("approved_amount_cents"):
            claim.status = "compensated"
            claim.resolved_at = datetime.now(UTC)
            emit_event(
                db,
                event_type=DomainEventType.REFUND_ISSUED,
                aggregate_type="claim",
                aggregate_id=claim_id,
                actor_type="admin",
                actor_id=ctx.user.id,
                correlation_id=claim.order_id,
                payload={
                    "claim_id": claim_id,
                    "order_id": claim.order_id,
                    "amount_cents": compensation.get("approved_amount_cents"),
                },
            )
        self._append_timeline(
            db, claim, label="Compensation Paid", actor_type="admin", actor_id=ctx.user.id,
            payload=compensation,
        )
        db.commit()
        db.refresh(claim)
        return claim

    def set_insurance(
        self, db: Session, ctx: AdminContext, claim_id: str, insurance: dict[str, Any]
    ) -> Claim:
        claim = self.get_claim(db, claim_id)
        if not claim:
            raise LookupError("claim_not_found")
        res = dict(claim.resolution or {})
        res["insurance"] = insurance
        claim.resolution = res
        if claim.status not in ("compensated", "closed", "archived"):
            claim.status = "waiting_insurance"
        self._append_timeline(
            db, claim, label="Insurance Updated", actor_type="admin", actor_id=ctx.user.id,
            payload=insurance,
        )
        db.commit()
        db.refresh(claim)
        return claim

    def bulk_action(
        self,
        db: Session,
        ctx: AdminContext,
        *,
        claim_ids: list[str],
        action: str,
        investigator_id: str | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        results = []
        for cid in claim_ids:
            try:
                if action == "assign" and investigator_id:
                    self.assign_investigator(db, ctx, cid, investigator_id)
                elif action == "status" and status:
                    self.update_status(db, ctx, cid, status)
                else:
                    raise ValueError("invalid_bulk_action")
                results.append({"claim_id": cid, "status": "ok"})
            except Exception as exc:
                results.append({"claim_id": cid, "status": "error", "detail": str(exc)})
        return {"action": action, "results": results}

    # ------------------------------------------------------------------ #
    # Smart features
    # ------------------------------------------------------------------ #
    def find_duplicates(self, db: Session, claim: Claim) -> list[dict[str, Any]]:
        others = (
            db.query(Claim)
            .filter(Claim.order_id == claim.order_id, Claim.id != claim.id)
            .all()
        )
        return [
            {"id": o.id, "claim_number": claim_number(o.id), "claim_type": o.claim_type, "status": o.status}
            for o in others
        ]

    def smart_insights(self, db: Session, claim: Claim) -> dict[str, Any]:
        ctx = self._order_context(db, claim.order_id)
        risk = self._risk_score(claim, ctx)
        duplicates = self.find_duplicates(db, claim)
        fraud_flags = []
        if claim.claim_type in ("fraud_investigation", "chargeback"):
            fraud_flags.append("High-risk claim type")
        if len(duplicates) >= 2:
            fraud_flags.append("Multiple claims on same order")
        if risk >= 70:
            fraud_flags.append("Elevated risk score")

        suggestion = "Continue investigation and collect evidence"
        if claim.claim_type == "late_delivery":
            suggestion = "Review SLA timeline and GPS history; consider partial credit"
        elif claim.claim_type == "damaged_parcel":
            suggestion = "Request photos and POD; review driver handling notes"
        elif claim.claim_type in ("chargeback", "payment_dispute"):
            suggestion = "Gather payment records and delivery proof for Stripe dispute"

        summary = f"{claim.claim_type.replace('_', ' ').title()} claim for order {ctx.get('tracking_number', claim.order_id[:8])}. Status: {claim.status}."

        return {
            "risk_score": risk,
            "fraud_flags": fraud_flags,
            "duplicate_count": len(duplicates),
            "suggested_resolution": suggestion,
            "ai_summary": summary,
            "similar_claims": duplicates[:5],
        }

    def auto_assign_investigator(self, db: Session, ctx: AdminContext, claim_id: str) -> Claim:
        """Assign to least-loaded active investigator (automation stub)."""
        investigators = db.query(AdminUser).filter(AdminUser.is_active.is_(True)).limit(20).all()
        if not investigators:
            raise ValueError("no_investigators")
        loads = []
        for inv in investigators:
            count = db.query(func.count(Claim.id)).filter(
                Claim.assigned_to == inv.id,
                Claim.status.in_(("new", "open", "assigned", "under_investigation", "investigating")),
            ).scalar() or 0
            loads.append((count, inv.id))
        loads.sort(key=lambda x: x[0])
        return self.assign_investigator(db, ctx, claim_id, loads[0][1])
