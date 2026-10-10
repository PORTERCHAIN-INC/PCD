"""Visitor intelligence — fuse visitor sessions, quotes, and CRM guide signals."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.booking_engine.visitor_tracking_service import VisitorTrackingService
from porterchain_api.crm_models import CrmLead
from porterchain_api.domain.visitor_intent import behavioral_score_boost as domain_behavioral_boost
from porterchain_api.booking_models import Quote, VisitorSession


class VisitorIntelligenceService:
    def __init__(self) -> None:
        self._visitors = VisitorTrackingService()

    def insight_for_session(self, db: Session, session_id: str) -> dict[str, Any] | None:
        visitor = self._visitors.get_session(db, session_id)
        if not visitor:
            return None
        return self._build_insight(db, visitor)

    def insight_for_lead(self, db: Session, lead: CrmLead) -> dict[str, Any] | None:
        fields = lead.custom_fields if isinstance(lead.custom_fields, dict) else {}
        session_id = lead.visitor_session_id or fields.get("visitor_id") or fields.get("session_id")
        if isinstance(session_id, str) and session_id.strip():
            insight = self.insight_for_session(db, session_id.strip())
            if insight:
                return insight
        return {
            "session_id": session_id,
            "intent_score": None,
            "guide": {
                "intent": fields.get("intent"),
                "stage_hint": self._infer_guide_stage(fields),
                "transcript_turns": len(fields.get("transcript") or [])
                if isinstance(fields.get("transcript"), list)
                else 0,
                "has_appointment": bool(fields.get("appointment")),
            },
            "attribution": {
                "source_page": fields.get("source_page"),
                "utm_source": fields.get("utm_source"),
                "utm_medium": fields.get("utm_medium"),
                "utm_campaign": fields.get("utm_campaign"),
            },
            "quotes": [],
            "signals": {},
        }

    def _build_insight(self, db: Session, visitor: VisitorSession) -> dict[str, Any]:
        signals = visitor.signals if isinstance(visitor.signals, dict) else {}
        quotes = (
            db.query(Quote)
            .filter(
                (Quote.anonymous_session_id == visitor.id)
                | (Quote.visitor_session_id == visitor.id)
            )
            .order_by(Quote.created_at.desc())
            .limit(8)
            .all()
        )
        return {
            "session_id": visitor.id,
            "intent_score": int(visitor.intent_score or 0),
            "touch_count": int(visitor.touch_count or 0),
            "quote_generated": bool(visitor.quote_generated),
            "last_quote_id": visitor.last_quote_id,
            "customer_id": visitor.customer_id,
            "device": visitor.device,
            "attribution": {
                "utm_source": visitor.utm_source,
                "utm_medium": visitor.utm_medium,
                "utm_campaign": visitor.utm_campaign,
                "referrer": visitor.referrer,
                "landing_page": signals.get("landing_page"),
                "from_page": signals.get("from_page"),
                "source_page": signals.get("source_page"),
                "locale": signals.get("locale"),
            },
            "signals": signals,
            "quotes": [
                {
                    "quote_id": q.id,
                    "state": q.state,
                    "amount_cents": q.amount_cents,
                    "vehicle_class": q.vehicle_class,
                    "created_at": q.created_at.isoformat() if q.created_at else None,
                }
                for q in quotes
            ],
        }

    @staticmethod
    def _infer_guide_stage(fields: dict[str, Any]) -> str | None:
        if fields.get("appointment"):
            return "book"
        if isinstance(fields.get("transcript"), list) and fields["transcript"]:
            return "capture" if fields.get("intent") else "qualify"
        if fields.get("intent"):
            return "qualify"
        return None

    @staticmethod
    def behavioral_score_boost(lead: CrmLead, visitor: VisitorSession | None = None) -> int:
        return domain_behavioral_boost(lead, visitor)
