"""Smart features — duplicates, insights, auto-assignment."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from porterchain_api.admin_models import AdminUser, Claim
from porterchain_api.domain.claims import claim_number
from porterchain_api.support_engine.support_helpers import SupportActor


class ClaimsSmartMixin:
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

    def auto_assign_investigator(self, db: Session, ctx: SupportActor, claim_id: str) -> Claim:
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
