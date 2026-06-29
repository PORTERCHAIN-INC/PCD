"""Claims and incidents per ORDER_LIFECYCLE.md exception states."""

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.admin_models import Claim
from porterchain_api.booking_engine._core import emit_event
from porterchain_api.admin_engine import events as E


class AdminClaimsService:
    def list_claims(self, db: Session, *, status: str | None = None, limit: int = 50) -> list[Claim]:
        q = db.query(Claim)
        if status:
            q = q.filter(Claim.status == status)
        return q.order_by(Claim.created_at.desc()).limit(limit).all()

    def get_claim(self, db: Session, claim_id: str) -> Claim | None:
        return db.query(Claim).filter(Claim.id == claim_id).first()

    def open_claim(
        self,
        db: Session,
        ctx: AdminContext,
        *,
        order_id: str,
        claim_type: str,
        description: str | None = None,
    ) -> Claim:
        claim = Claim(order_id=order_id, claim_type=claim_type, description=description, assigned_to=ctx.user.id)
        db.add(claim)
        db.flush()
        emit_event(
            db,
            event_type=E.CLAIM_OPENED,
            aggregate_type="claim",
            aggregate_id=claim.id,
            actor_type="admin",
            actor_id=ctx.user.id,
            payload={"order_id": order_id, "claim_type": claim_type},
        )
        db.commit()
        db.refresh(claim)
        return claim

    def update_status(self, db: Session, ctx: AdminContext, claim_id: str, status: str) -> Claim:
        claim = self.get_claim(db, claim_id)
        if not claim:
            raise LookupError("claim_not_found")
        claim.status = status
        if status in ("resolved", "closed"):
            claim.resolved_at = datetime.now(UTC)
            emit_event(
                db,
                event_type=E.CLAIM_RESOLVED,
                aggregate_type="claim",
                aggregate_id=claim_id,
                actor_type="admin",
                actor_id=ctx.user.id,
            )
        db.commit()
        db.refresh(claim)
        return claim
