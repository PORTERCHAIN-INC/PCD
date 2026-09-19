"""Lead Assist — heuristic + optional NVIDIA NIM proposals (never auto-send)."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.crm_models import CrmConversation, CrmConversationMessage, CrmLead
from porterchain_api.domain.crm_states import LeadDecisionStatus


_LEAD_ASSIST_SYSTEM = """You assist PorterChain sales staff closing merchant capacity deals.
Rules:
1. Return ONLY JSON: {"summary":string,"draft_reply":string,"suggested_decision_status":string,"next_questions":[string],"risks":[string]}
2. suggested_decision_status must be one of: researching, questions_open, objection, ready_to_convert, deferred
3. draft_reply is a short professional message the human may send — no invented prices, SLAs, or contracts.
4. next_questions: 2–4 discovery questions. risks: 0–3 short flags.
5. No markdown."""


def _heuristic(lead: CrmLead, messages: list[str]) -> dict[str, Any]:
    thread = "\n".join(messages[-8:]) if messages else (lead.internal_notes or "")
    decision = lead.decision_status or LeadDecisionStatus.NEW.value
    score = int(lead.lead_score or 0)
    if score >= 60 and decision in (LeadDecisionStatus.NEW.value, LeadDecisionStatus.RESEARCHING.value):
        suggested = LeadDecisionStatus.READY_TO_CONVERT.value
    elif "price" in thread.lower() or "competitor" in thread.lower():
        suggested = LeadDecisionStatus.OBJECTION.value
    elif thread.strip():
        suggested = LeadDecisionStatus.QUESTIONS_OPEN.value
    else:
        suggested = LeadDecisionStatus.RESEARCHING.value

    name = lead.primary_contact_name or "there"
    draft = (
        f"Hi {name}, thanks for reaching out to PorterChain. "
        f"We help merchants secure reliable delivery capacity in the GTA. "
        f"Could you share approx. monthly deliveries and your current provider?"
    )
    questions = [
        "How many deliveries per month do you need capacity for?",
        "Which cities / FSAs should we cover first?",
        "What vehicle class do you typically need?",
        "Who else evaluates logistics vendors at your company?",
    ]
    risks: list[str] = []
    if not lead.email:
        risks.append("Missing email — hard to nurture")
    if not lead.phone:
        risks.append("Missing phone — slow first response")
    if lead.merge_candidate_of:
        risks.append("Possible duplicate — review merge queue")

    return {
        "summary": f"{lead.company_name} via {lead.channel or lead.source} — score {score}, status {lead.status}",
        "draft_reply": draft,
        "suggested_decision_status": suggested,
        "next_questions": questions,
        "risks": risks,
        "source": "heuristic",
        "proposals": [
            {
                "id": "draft_reply",
                "type": "draft_reply",
                "title": "Suggested reply",
                "body": draft,
            },
            {
                "id": "decision_status",
                "type": "decision_status",
                "title": "Suggested decision",
                "body": suggested,
            },
        ],
    }


def build_lead_assist(
    db: Session,
    lead: CrmLead,
    *,
    flags: dict[str, bool] | None = None,
    actor_id: str | None = None,
) -> dict[str, Any]:
    convos = (
        db.query(CrmConversation)
        .filter(CrmConversation.lead_id == lead.id)
        .order_by(CrmConversation.updated_at.desc())
        .limit(3)
        .all()
    )
    messages: list[str] = []
    for c in convos:
        rows = (
            db.query(CrmConversationMessage)
            .filter(CrmConversationMessage.conversation_id == c.id)
            .order_by(CrmConversationMessage.occurred_at.asc())
            .limit(20)
            .all()
        )
        for m in rows:
            messages.append(f"{m.direction}: {m.body}")

    base = _heuristic(lead, messages)

    from porterchain_api.intelligence_engine.enrichers import _can_call_nim, _call_nim, _parse_json_object, _phase2_ready

    if not _phase2_ready(flags or {}) or not _can_call_nim(db):
        return base

    result = _call_nim(
        db,
        feature="lead_assist",
        system=_LEAD_ASSIST_SYSTEM,
        user=json.dumps(
            {
                "company_name": lead.company_name,
                "contact": lead.primary_contact_name,
                "channel": lead.channel,
                "source": lead.source,
                "intent_type": lead.intent_type,
                "decision_status": lead.decision_status,
                "lead_score": lead.lead_score,
                "notes": lead.internal_notes,
                "thread": messages[-12:],
                "estimated_deliveries_per_month": lead.estimated_deliveries_per_month,
            }
        ),
        max_tokens=500,
        actor_type="staff",
        actor_id=actor_id,
    )
    if not result:
        return base
    try:
        data = _parse_json_object(result["content"])
    except (json.JSONDecodeError, TypeError, ValueError):
        return base

    draft = str(data.get("draft_reply") or "").strip()
    summary = str(data.get("summary") or "").strip()
    suggested = str(data.get("suggested_decision_status") or "").strip()
    allowed = {s.value for s in LeadDecisionStatus}
    if suggested not in allowed:
        suggested = base["suggested_decision_status"]
    questions = [str(q).strip() for q in (data.get("next_questions") or []) if str(q).strip()][:4]
    risks = [str(r).strip() for r in (data.get("risks") or []) if str(r).strip()][:3]

    if summary:
        base["summary"] = summary[:500]
    if draft:
        base["draft_reply"] = draft[:2000]
        base["proposals"][0]["body"] = base["draft_reply"]
    base["suggested_decision_status"] = suggested
    base["proposals"][1]["body"] = suggested
    if questions:
        base["next_questions"] = questions
    if risks:
        base["risks"] = risks
    base["source"] = "nvidia_nim"
    base["model"] = result.get("model")
    return base


__all__ = ["build_lead_assist"]
