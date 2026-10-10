"""Support dashboard metrics and reporting."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.admin_models import AdminUser, SupportTicket
from porterchain_api.domain.support import ticket_number
from porterchain_api.support_engine.support_helpers import (
    OPEN_STATUSES,
    normalize_status,
    ticket_data,
)


class SupportDashboardMixin:
    def dashboard(self, db: Session) -> dict[str, Any]:
        tickets = db.query(SupportTicket).all()
        open_tickets = [t for t in tickets if normalize_status(t.status) in OPEN_STATUSES]
        urgent = [t for t in open_tickets if t.priority in ("urgent", "critical")]
        breached = [t for t in tickets if self._sla_status(db, t) == "breached"]
        waiting_customer = [t for t in open_tickets if normalize_status(t.status) == "waiting_customer"]
        waiting_merchant = [t for t in open_tickets if normalize_status(t.status) == "waiting_merchant"]
        waiting_driver = [t for t in open_tickets if normalize_status(t.status) == "waiting_driver"]
        waiting_internal = [t for t in open_tickets if normalize_status(t.status) == "waiting_internal"]
        claims_linked = sum(1 for t in tickets if t.category == "claim" or t.order_id)
        orders_impacted = len({t.order_id for t in tickets if t.order_id})

        first_response_times: list[float] = []
        resolution_times: list[float] = []
        csat_scores: list[float] = []
        for t in tickets:
            data = ticket_data(t)
            if data.get("first_response_at") and t.created_at:
                created = t.created_at.replace(tzinfo=UTC) if t.created_at.tzinfo is None else t.created_at
                first = datetime.fromisoformat(str(data["first_response_at"]).replace("Z", "+00:00"))
                first_response_times.append((first - created).total_seconds() / 3600)
            if data.get("resolved_at") and t.created_at:
                created = t.created_at.replace(tzinfo=UTC) if t.created_at.tzinfo is None else t.created_at
                resolved = datetime.fromisoformat(str(data["resolved_at"]).replace("Z", "+00:00"))
                resolution_times.append((resolved - created).total_seconds() / 3600)
            if data.get("csat_score") is not None:
                csat_scores.append(float(data["csat_score"]))

        agents = (
            db.query(AdminUser)
            .filter(AdminUser.role.in_(("support", "support_lead", "admin", "super_admin")))
            .all()
        )
        workload = []
        for agent in agents:
            assigned = [t for t in open_tickets if t.assigned_to == agent.id]
            workload.append(
                {
                    "agent_id": agent.id,
                    "agent_name": agent.name or agent.email,
                    "open_tickets": len(assigned),
                    "urgent_tickets": sum(1 for t in assigned if t.priority in ("urgent", "critical")),
                }
            )
        workload.sort(key=lambda x: -x["open_tickets"])

        recent = sorted(tickets, key=lambda t: t.updated_at, reverse=True)[:8]
        return {
            "open_tickets": len(open_tickets),
            "urgent_tickets": len(urgent),
            "sla_breaches": len(breached),
            "pending_customer": len(waiting_customer),
            "pending_merchant": len(waiting_merchant),
            "pending_driver": len(waiting_driver),
            "pending_internal": len(waiting_internal),
            "claims_linked": claims_linked,
            "orders_impacted": orders_impacted,
            "avg_first_response_hours": round(sum(first_response_times) / len(first_response_times), 1)
            if first_response_times
            else 0,
            "avg_resolution_hours": round(sum(resolution_times) / len(resolution_times), 1)
            if resolution_times
            else 0,
            "customer_satisfaction": round(sum(csat_scores) / len(csat_scores), 1) if csat_scores else 0,
            "recent_activity": [
                {
                    "ticket_id": t.id,
                    "ticket_number": ticket_number(t.id),
                    "subject": t.subject,
                    "status": normalize_status(t.status),
                    "updated_at": t.updated_at,
                }
                for t in recent
            ],
            "team_workload": workload[:10],
        }

    def reports(self, db: Session) -> dict[str, Any]:
        tickets = db.query(SupportTicket).all()
        by_type: dict[str, int] = {}
        by_merchant: dict[str, int] = {}
        by_driver: dict[str, int] = {}
        by_agent: dict[str, int] = {}
        monthly: dict[str, int] = {}
        sla_ok = 0
        sla_breach = 0
        for t in tickets:
            by_type[t.category or "other"] = by_type.get(t.category or "other", 0) + 1
            ctx = self._order_context(db, t.order_id)
            if ctx.get("merchant_name"):
                by_merchant[ctx["merchant_name"]] = by_merchant.get(ctx["merchant_name"], 0) + 1
            if ctx.get("driver_name"):
                by_driver[ctx["driver_name"]] = by_driver.get(ctx["driver_name"], 0) + 1
            agent = self._agent_name(db, t.assigned_to) or "Unassigned"
            by_agent[agent] = by_agent.get(agent, 0) + 1
            month = t.created_at.strftime("%Y-%m") if t.created_at else "unknown"
            monthly[month] = monthly.get(month, 0) + 1
            sla = self._sla_status(db, t)
            if sla == "breached":
                sla_breach += 1
            elif sla in ("ok", "met"):
                sla_ok += 1
        dash = self.dashboard(db)
        return {
            "by_type": by_type,
            "by_merchant": dict(sorted(by_merchant.items(), key=lambda x: x[1], reverse=True)[:15]),
            "by_driver": dict(sorted(by_driver.items(), key=lambda x: x[1], reverse=True)[:15]),
            "by_agent": dict(sorted(by_agent.items(), key=lambda x: x[1], reverse=True)[:15]),
            "monthly_trends": dict(sorted(monthly.items())),
            "avg_first_response_hours": dash["avg_first_response_hours"],
            "avg_resolution_hours": dash["avg_resolution_hours"],
            "sla_compliance_percent": round(100 * sla_ok / max(1, sla_ok + sla_breach), 1),
            "customer_satisfaction": dash["customer_satisfaction"],
            "top_issues": [{"cause": k, "count": v} for k, v in sorted(by_type.items(), key=lambda x: x[1], reverse=True)[:10]],
        }
