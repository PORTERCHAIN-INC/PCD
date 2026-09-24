"""Live activity feed, sync health, and AI ops risk scoring."""

from __future__ import annotations

from sqlalchemy.orm import Session

from porterchain_api.booking_models import DomainEvent, Order
from porterchain_api.order_engine.buckets import HIGH_PRIORITY_CENTS, IN_FLIGHT, WAITING

from porterchain_api.admin_engine.control_tower._helpers import now_utc


class EventsMixin:
    def live_activity(self, db: Session, *, limit: int = 60) -> list[dict]:
        rows = db.query(DomainEvent).order_by(DomainEvent.occurred_at.desc()).limit(limit).all()
        return [
            {
                "id": e.id,
                "event_type": e.event_type,
                "aggregate_type": e.aggregate_type,
                "aggregate_id": e.aggregate_id,
                "actor_type": e.actor_type,
                "occurred_at": e.occurred_at.isoformat() if e.occurred_at else None,
            }
            for e in rows
        ]

    def sync_health(self, db: Session, *, audit_limit: int = 40) -> dict:
        """Fleetbase sync queue health for the ops control tower.

        Reads the Porterchain retry queue + sync audit mirror; never calls
        Fleetbase directly (masterrule §3 — adapter boundary).
        """
        from porterchain_api.fleetbase_engine import ErrorQueue
        from porterchain_api.fleetbase_models import FleetbaseSyncAudit

        recent = (
            db.query(FleetbaseSyncAudit)
            .order_by(FleetbaseSyncAudit.created_at.desc())
            .limit(audit_limit)
            .all()
        )
        return {
            "queue": ErrorQueue.stats(db),
            "dead_letters": [
                {
                    "id": j.id,
                    "kind": j.kind,
                    "direction": j.direction,
                    "order_id": j.order_id,
                    "attempts": j.attempts,
                    "last_error": j.last_error,
                }
                for j in ErrorQueue.list_dead(db)
            ],
            "recent_audit": [
                {
                    "direction": a.direction,
                    "kind": a.kind,
                    "status": a.status,
                    "order_id": a.order_id,
                    "message": a.message,
                    "at": a.created_at.isoformat() if a.created_at else None,
                }
                for a in recent
            ],
        }

    def ai_ops(self, db: Session) -> dict:
        now = now_utc()
        merchants = self._merchant_names(db)
        drivers = self._driver_names(db)
        from datetime import timedelta

        from sqlalchemy import or_

        from porterchain_api.booking_engine.order_sla import AT_RISK_MINUTES

        hours = self._instant_sla_hours(db)
        risk_end = now + timedelta(minutes=AT_RISK_MINUTES)
        rows = (
            db.query(Order)
            .filter(
                Order.is_sandbox.is_(False),
                Order.state.in_(WAITING + IN_FLIGHT),
                or_(Order.sla_deadline_at.is_(None), Order.sla_deadline_at <= risk_end),
            )
            .all()
        )
        risk_orders: list[dict] = []
        for o in rows:
            sla = self._sla_status(o, now, instant_sla_hours=hours)
            score = 0
            reasons = []
            if sla == "breached":
                score += 60
                reasons.append("SLA breached")
            elif sla == "at_risk":
                score += 35
                reasons.append("Approaching SLA")
            if o.amount_cents >= HIGH_PRIORITY_CENTS:
                score += 20
                reasons.append("High-value order")
            if o.state in WAITING:
                score += 15
                reasons.append("Awaiting dispatch")
            if not o.assigned_driver_id and o.state not in WAITING:
                score += 10
                reasons.append("No driver assigned")
            if score >= 35:
                card = self._order_card(o, merchants, drivers, now, instant_sla_hours=hours)
                card["risk_score"] = min(100, score)
                card["reasons"] = reasons
                risk_orders.append(card)
        risk_orders.sort(key=lambda c: c["risk_score"], reverse=True)
        suggested = self.assignable_drivers(db)
        from porterchain_api.config import get_settings
        from porterchain_api.intelligence_engine.nim_client import nim_status

        llm = nim_status()
        flags = get_settings().phase2_flags
        return {
            "risk_orders": risk_orders[:25],
            "suggested_drivers": suggested[:5],
            "recommendation": (
                f"{len(risk_orders)} orders need attention. Prioritise SLA-breached and high-value first."
                if risk_orders
                else "All in-flight orders are on track."
            ),
            "llm": llm,
            "phase2": {
                "intelligence": bool(flags.get("intelligence")),
                "ai_dispatch": bool(flags.get("ai_dispatch")),
            },
        }
