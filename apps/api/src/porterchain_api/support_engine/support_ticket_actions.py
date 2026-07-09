"""Support ticket mutations — status, assignment, notes, and bulk actions."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.audit import log_admin_audit
from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.admin_models import AdminUser, SupportTicket
from porterchain_api.booking_engine._core import emit_event
from porterchain_api.support_engine.support_helpers import (
    OPEN_STATUSES,
    TICKET_STATUSES,
    append_timeline,
    normalize_status,
    set_ticket_data,
    ticket_data,
)


class SupportTicketActionsMixin:
    def update_status(self, db: Session, ctx: AdminContext, ticket_id: str, status: str) -> SupportTicket:
        ticket = self.get_ticket(db, ticket_id)
        if not ticket:
            raise LookupError("ticket_not_found")
        if status not in TICKET_STATUSES:
            raise ValueError("invalid_status")
        old = ticket.status
        ticket.status = status
        data = ticket_data(ticket)
        if status in ("resolved", "closed") and not data.get("resolved_at"):
            set_ticket_data(ticket, resolved_at=datetime.now(UTC).isoformat())
        append_timeline(
            ticket,
            label=f"Status changed to {status.replace('_', ' ')}",
            actor_type="admin",
            actor_id=ctx.user.id,
            payload={"from": old, "to": status},
        )
        log_admin_audit(
            db,
            ctx,
            action="support.ticket.status",
            resource_type="support_ticket",
            resource_id=ticket.id,
            payload={"from": old, "to": status},
        )
        if status in ("resolved", "closed"):
            emit_event(
                db,
                event_type="support.ticket_resolved",
                aggregate_type="support_ticket",
                aggregate_id=ticket.id,
                actor_type="admin",
                actor_id=ctx.user.id,
            )
        db.commit()
        db.refresh(ticket)
        return ticket

    def assign_agent(self, db: Session, ctx: AdminContext, ticket_id: str, agent_id: str) -> SupportTicket:
        ticket = self.get_ticket(db, ticket_id)
        if not ticket:
            raise LookupError("ticket_not_found")
        ticket.assigned_to = agent_id
        if normalize_status(ticket.status) in ("new", "open"):
            ticket.status = "assigned"
        append_timeline(
            ticket,
            label="Agent assigned",
            actor_type="admin",
            actor_id=ctx.user.id,
            payload={"agent_id": agent_id},
        )
        log_admin_audit(
            db,
            ctx,
            action="support.ticket.assign",
            resource_type="support_ticket",
            resource_id=ticket.id,
            payload={"agent_id": agent_id},
        )
        db.commit()
        db.refresh(ticket)
        return ticket

    def auto_assign(self, db: Session, ctx: AdminContext, ticket_id: str) -> SupportTicket:
        agents = (
            db.query(AdminUser)
            .filter(AdminUser.is_active.is_(True), AdminUser.role.in_(("support", "support_lead")))
            .all()
        )
        if not agents:
            raise LookupError("no_agents")
        open_counts = {
            a.id: db.query(func.count(SupportTicket.id))
            .filter(
                SupportTicket.assigned_to == a.id,
                SupportTicket.status.in_(tuple(OPEN_STATUSES)),
            )
            .scalar()
            or 0
            for a in agents
        }
        agent_id = min(open_counts, key=open_counts.get)
        return self.assign_agent(db, ctx, ticket_id, agent_id)

    def add_note(
        self,
        db: Session,
        ctx: AdminContext,
        ticket_id: str,
        *,
        body: str,
        internal: bool = True,
        channel: str = "note",
    ) -> SupportTicket:
        ticket = self.get_ticket(db, ticket_id)
        if not ticket:
            raise LookupError("ticket_not_found")
        data = ticket_data(ticket)
        entry = {
            "id": str(uuid.uuid4()),
            "body": body,
            "channel": channel,
            "internal": internal,
            "author_id": ctx.user.id,
            "at": datetime.now(UTC).isoformat(),
        }
        if internal:
            notes = list(data.get("notes") or [])
            notes.append(entry)
            set_ticket_data(ticket, notes=notes)
            append_timeline(ticket, label="Internal note added", actor_type="admin", actor_id=ctx.user.id)
        else:
            comms = list(data.get("communications") or [])
            comms.append(entry)
            set_ticket_data(ticket, communications=comms)
            if not data.get("first_response_at"):
                set_ticket_data(ticket, first_response_at=datetime.now(UTC).isoformat())
            append_timeline(
                ticket,
                label=f"Reply sent via {channel}",
                actor_type="admin",
                actor_id=ctx.user.id,
            )
        log_admin_audit(
            db,
            ctx,
            action="support.ticket.note",
            resource_type="support_ticket",
            resource_id=ticket.id,
            payload={"internal": internal, "channel": channel},
        )
        db.commit()
        db.refresh(ticket)
        return ticket

    def pause_sla(self, db: Session, ctx: AdminContext, ticket_id: str) -> SupportTicket:
        ticket = self.get_ticket(db, ticket_id)
        if not ticket:
            raise LookupError("ticket_not_found")
        set_ticket_data(ticket, sla_paused=True)
        append_timeline(ticket, label="SLA paused", actor_type="admin", actor_id=ctx.user.id)
        db.commit()
        db.refresh(ticket)
        return ticket

    def resume_sla(self, db: Session, ctx: AdminContext, ticket_id: str) -> SupportTicket:
        ticket = self.get_ticket(db, ticket_id)
        if not ticket:
            raise LookupError("ticket_not_found")
        set_ticket_data(ticket, sla_paused=False)
        append_timeline(ticket, label="SLA resumed", actor_type="admin", actor_id=ctx.user.id)
        db.commit()
        db.refresh(ticket)
        return ticket

    def bulk_action(
        self,
        db: Session,
        ctx: AdminContext,
        ticket_ids: list[str],
        action: str,
        *,
        agent_id: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, str]]:
        results: list[dict[str, str]] = []
        for tid in ticket_ids:
            try:
                if action == "assign" and agent_id:
                    self.assign_agent(db, ctx, tid, agent_id)
                    results.append({"ticket_id": tid, "status": "assigned"})
                elif action == "auto_assign":
                    self.auto_assign(db, ctx, tid)
                    results.append({"ticket_id": tid, "status": "auto_assigned"})
                elif action == "status" and status:
                    self.update_status(db, ctx, tid, status)
                    results.append({"ticket_id": tid, "status": status})
                elif action == "close":
                    self.update_status(db, ctx, tid, "closed")
                    results.append({"ticket_id": tid, "status": "closed"})
                elif action == "escalate":
                    self.update_status(db, ctx, tid, "escalated")
                    results.append({"ticket_id": tid, "status": "escalated"})
                else:
                    results.append({"ticket_id": tid, "status": "unsupported"})
            except Exception as exc:
                results.append({"ticket_id": tid, "status": f"error:{exc}"})
        return results

    def update_ticket(self, db: Session, ticket_id: str, **fields) -> SupportTicket:
        ticket = self.get_ticket(db, ticket_id)
        if not ticket:
            raise LookupError("ticket_not_found")
        for k, v in fields.items():
            if v is not None and hasattr(ticket, k):
                setattr(ticket, k, v)
        db.commit()
        db.refresh(ticket)
        return ticket
