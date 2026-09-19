"""List, search, dashboard, and reports for claims."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from porterchain_api.admin_models import Claim
from porterchain_api.booking_models import Order
from porterchain_api.support_engine.claims_constants import ClaimFilters


class ClaimsQueryMixin:
    def list_claims(self, db: Session, *, status: str | None = None, limit: int = 50) -> list[Claim]:
        """Legacy list — prefer list_enriched."""
        q = db.query(Claim)
        if status:
            q = q.filter(Claim.status == status)
        return q.order_by(Claim.created_at.desc()).limit(limit).all()

    def open_count_for_merchant(self, db: Session, merchant_id: str) -> int:
        return (
            db.query(func.count(Claim.id))
            .join(Order, Claim.order_id == Order.id)
            .filter(Order.merchant_id == merchant_id, Claim.status.in_(("open", "investigating")))
            .scalar()
            or 0
        )

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
        if filters.customer_id:
            # Claim has no customer FK — scope via order.customer_id (C-6).
            order_ids = [
                oid
                for (oid,) in db.query(Order.id)
                .filter(Order.customer_id == filters.customer_id)
                .limit(5000)
                .all()
            ]
            if not order_ids:
                return []
            q = q.filter(Claim.order_id.in_(order_ids))
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
            if filters.customer_id and row["customer_id"] != filters.customer_id:
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

    def export_csv(self, db: Session, filters: ClaimFilters) -> str:
        import csv
        import io

        rows = self.list_enriched(db, filters)
        buffer = io.StringIO()
        fields = [
            "claim_number",
            "claim_type",
            "status",
            "priority",
            "amount_cents",
            "merchant_name",
            "tracking_number",
            "assigned_investigator",
            "has_insurance",
            "created_at",
        ]
        writer = csv.DictWriter(buffer, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
        return buffer.getvalue()
