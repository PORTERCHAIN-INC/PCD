"""Dispatcher copilot — concrete next-best-action recommendations (P2-1).

Decision support only: accept triggers the existing assign path; dismiss/modify
are audited via DomainEvent. Never auto-assigns without human accept.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.dispatch_suggestions_service import (
    DispatchSuggestionsService,
)
from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.booking_engine._core import emit_event
from porterchain_api.booking_models import Order
from porterchain_api.order_engine.buckets import DISPATCH_POOL, WAITING

logger = logging.getLogger(__name__)

ACTION_CAP = 8
DISMISS_TTL_SECONDS = 1800  # 30 minutes
DISMISS_KEY = "porterchain:ops:copilot:dismissed:{actor}"


def _action_id(order_id: str, driver_id: str, kind: str) -> str:
    raw = f"{kind}:{order_id}:{driver_id}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _dismissed_ids(actor_id: str) -> set[str]:
    try:
        from porterchain_shared.redis_client import get_redis_client

        raw = get_redis_client().get(DISMISS_KEY.format(actor=actor_id or "anon"))
        if not raw:
            return set()
        data = json.loads(raw)
        return set(data) if isinstance(data, list) else set()
    except Exception:  # noqa: BLE001
        return set()


def _remember_dismiss(actor_id: str, action_id: str) -> None:
    try:
        from porterchain_shared.redis_client import get_redis_client

        key = DISMISS_KEY.format(actor=actor_id or "anon")
        client = get_redis_client()
        current = _dismissed_ids(actor_id)
        current.add(action_id)
        client.setex(key, DISMISS_TTL_SECONDS, json.dumps(sorted(current)))
    except Exception as exc:  # noqa: BLE001
        logger.debug("copilot dismiss cache failed: %s", exc)


class DispatcherCopilotService:
    def __init__(self, suggestions: DispatchSuggestionsService | None = None) -> None:
        self._suggestions = suggestions or DispatchSuggestionsService()

    def recommendations(self, db: Session, ctx: AdminContext) -> dict[str, Any]:
        actor = getattr(ctx.user, "id", None) or "anon"
        dismissed = _dismissed_ids(actor)
        waiting = (
            db.query(Order)
            .filter(
                Order.is_sandbox.is_(False),
                Order.assigned_driver_id.is_(None),
                Order.state.in_(tuple(set(DISPATCH_POOL + WAITING))),
            )
            .order_by(Order.scheduled_at.asc())
            .limit(ACTION_CAP)
            .all()
        )

        actions: list[dict[str, Any]] = []
        pending_ranking = 0
        for order in waiting:
            try:
                ranked = self._suggestions.suggest(db, order.id)
            except LookupError:
                continue
            if ranked.get("source") == "pending":
                pending_ranking += 1
                continue
            drivers = ranked.get("drivers") or []
            if not drivers:
                continue
            best = drivers[0]
            second = drivers[1] if len(drivers) > 1 else None
            best_eta = best.get("eta_minutes")
            next_eta = second.get("eta_minutes") if second else None
            savings = None
            if best_eta is not None and next_eta is not None:
                savings = round(float(next_eta) - float(best_eta), 1)

            aid = _action_id(order.id, best["id"], "assign")
            if aid in dismissed:
                continue

            rationale_bits = list(best.get("reasons") or [])
            if savings is not None and savings > 0:
                rationale_bits.insert(
                    0, f"Saves ~{savings:.0f} min vs next-best ({second.get('name')})"
                )
            actions.append(
                {
                    "id": aid,
                    "kind": "assign",
                    "priority": 100 - (best.get("score") or 50),
                    "title": f"Assign {order.tracking_number} → {best.get('name')}",
                    "summary": (
                        f"Assign order {order.tracking_number} to {best.get('name')}"
                        + (f": saves {savings:.0f} min vs next best" if savings and savings > 0 else "")
                    ),
                    "order_id": order.id,
                    "tracking_number": order.tracking_number,
                    "driver_id": best["id"],
                    "driver_name": best.get("name"),
                    "eta_minutes": best_eta,
                    "eta_source": best.get("eta_source"),
                    "next_best_driver": second.get("name") if second else None,
                    "next_best_eta_minutes": next_eta,
                    "savings_minutes": savings,
                    "score": best.get("score"),
                    "reasons": rationale_bits,
                    "rationale_narrative": None,
                    "alternates": [
                        {
                            "driver_id": d["id"],
                            "driver_name": d.get("name"),
                            "eta_minutes": d.get("eta_minutes"),
                            "eta_source": d.get("eta_source"),
                            "score": d.get("score"),
                        }
                        for d in drivers[1:4]
                    ],
                }
            )

        actions.sort(key=lambda a: (-(a.get("priority") or 0), a.get("score") or 99))
        if actions:
            try:
                from porterchain_api.config import get_settings
                from porterchain_api.intelligence_engine.enrichers import (
                    explain_dispatch_rationale,
                )

                top = actions[0]
                narrative = explain_dispatch_rationale(
                    list(top.get("reasons") or []),
                    flags=get_settings().phase2_flags,
                    db=db,
                    actor_type="admin",
                    actor_id=getattr(ctx.user, "id", None),
                )
                if narrative:
                    top["rationale_narrative"] = narrative
            except Exception as exc:  # noqa: BLE001
                logger.debug("dispatch rationale enrich skipped: %s", exc)
        ranking = pending_ranking > 0 and not actions
        return {
            "generated_at": datetime.now(UTC).isoformat(),
            "action_count": len(actions),
            "actions": actions[:ACTION_CAP],
            "pending_ranking": pending_ranking,
            "note": (
                "Ranking drivers…"
                if ranking
                else "Recommendations only — accept runs the existing assign path; never auto-assigns."
            ),
        }

    def accept(
        self,
        db: Session,
        ctx: AdminContext,
        *,
        action_id: str,
        order_id: str,
        driver_id: str,
        modified: bool = False,
    ) -> dict[str, Any]:
        from porterchain_api.admin_engine.operations_service import AdminOperationsService

        if not driver_id:
            raise ValueError("driver_id_required")

        actor = getattr(ctx.user, "id", None)

        ops = AdminOperationsService()
        try:
            # Keep assign + copilot audit in one transaction.
            order = ops._assign_driver_no_commit(db, ctx, order_id, driver_id)
        except LookupError as exc:
            raise LookupError(str(exc)) from exc
        except ValueError as exc:
            raise ValueError(str(exc)) from exc

        # Assignment side effects fan out once via order.driver_assigned.

        emit_event(
            db,
            event_type="ops.copilot.modified" if modified else "ops.copilot.accepted",
            aggregate_type="order",
            aggregate_id=order_id,
            actor_type="admin",
            actor_id=actor,
            payload={
                "action_id": action_id,
                "driver_id": driver_id,
                "modified": modified,
                "correlation": str(uuid4()),
            },
        )
        db.commit()
        db.refresh(order)
        # Phase 1d/1b: mid-day insert reopt with prior_assignments (best-effort).
        AdminOperationsService._enqueue_driver_book_optimize(
            db, driver_id, insert_order_id=order.id
        )
        return {
            "ok": True,
            "order_id": order.id,
            "state": order.state,
            "action_id": action_id,
            "modified": modified,
        }

    def dismiss(
        self,
        db: Session,
        ctx: AdminContext,
        *,
        action_id: str,
        order_id: str,
        reason: str | None = None,
    ) -> dict[str, Any]:
        actor = getattr(ctx.user, "id", None) or "anon"
        _remember_dismiss(actor, action_id)
        emit_event(
            db,
            event_type="ops.copilot.dismissed",
            aggregate_type="order",
            aggregate_id=order_id,
            actor_type="admin",
            actor_id=actor,
            payload={"action_id": action_id, "reason": reason},
        )
        db.commit()
        return {"ok": True, "action_id": action_id, "dismissed": True}

    def audit_trail(self, db: Session, *, limit: int = 40) -> list[dict[str, Any]]:
        from porterchain_api.booking_models import DomainEvent

        rows = (
            db.query(DomainEvent)
            .filter(DomainEvent.event_type.like("ops.copilot.%"))
            .order_by(DomainEvent.occurred_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": e.id,
                "event_type": e.event_type,
                "order_id": e.aggregate_id,
                "actor_id": e.actor_id,
                "payload": e.payload,
                "occurred_at": e.occurred_at.isoformat() if e.occurred_at else None,
            }
            for e in rows
        ]
