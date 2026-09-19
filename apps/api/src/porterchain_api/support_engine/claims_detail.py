"""Claim detail and retrieval."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.admin_models import Claim
from porterchain_api.booking_models import DomainEvent


class ClaimsDetailMixin:
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
