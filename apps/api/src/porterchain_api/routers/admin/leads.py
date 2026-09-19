"""Admin CRM leads — list, detail, status updates, appointment calendar."""

from datetime import datetime
from typing import Annotated
import uuid

from fastapi import HTTPException, Query
from sqlalchemy.orm import Session

from porterchain_api.collaboration_engine import CrmSalesService
from porterchain_api.collaboration_engine.lead_channel_adapters import event_from_referral
from porterchain_api.collaboration_engine.lead_ingest_service import (
    CanonicalLeadEvent,
    LeadIngestService,
)
from porterchain_api.config import Settings, get_settings
from porterchain_api.crm_models import CrmConversation, CrmConversationMessage, CrmLeadIdentity
from porterchain_api.domain.crm_states import channel_for_source
from porterchain_api.merchant_engine.lookups import get_merchant
from porterchain_api.routers.admin._deps import (
    AdminContext,
    Depends,
    _perm,
    get_admin_context,
    get_db,
    require_module,
    router,
)
from porterchain_api.schemas_crm import LeadConvertRequest, LeadCreate, LeadOut, LeadUpdate, TaskOut
from pydantic import BaseModel, Field

_crm = CrmSalesService()
_ingest = LeadIngestService()


@router.get("/leads", response_model=list[LeadOut])
def list_leads(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    status: str | None = None,
    priority: str | None = None,
    source: str | None = None,
    channel: str | None = None,
    intent_type: str | None = None,
    decision_status: str | None = None,
    assigned_to: str | None = None,
    unassigned: bool | None = None,
    merge_candidates: bool | None = None,
    sla_breached: bool | None = None,
    search: str | None = None,
    limit: int = 200,
) -> list[LeadOut]:
    require_module(ctx, "crm_read")
    rows = _crm.list_leads(
        db,
        status=status,
        priority=priority,
        source=source,
        channel=channel,
        intent_type=intent_type,
        decision_status=decision_status,
        assigned_to=assigned_to,
        unassigned=unassigned,
        merge_candidates=merge_candidates,
        sla_breached=sla_breached,
        search=search,
        limit=min(limit, 500),
    )
    return [LeadOut.model_validate(row) for row in rows]


@router.get("/leads/metrics")
def leads_metrics(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    days: int = Query(30, ge=1, le=365),
) -> dict:
    """Channel funnel, SLA, CAPI coverage, assist usage (Leaf 4)."""
    require_module(ctx, "crm_read")
    from porterchain_api.collaboration_engine.lead_metrics import lead_channel_metrics

    return lead_channel_metrics(db, days=days)


@router.get("/leads/pipeline")
def leads_pipeline_board(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    search: str | None = None,
    card_type: str | None = None,
) -> list[dict]:
    """Merchant-acquisition pipeline board (leads + deals) with origin channel."""
    require_module(ctx, "crm_read")
    return _crm.pipeline_board(db, search=search, card_type=card_type)


@router.post("/leads", response_model=LeadOut, status_code=201)
def create_lead_manual(
    body: LeadCreate,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> LeadOut:
    """Staff manual capture (call / SMS / referral / walk-in)."""
    require_module(ctx, "crm")
    data = body.model_dump()
    email = (data.get("email") or "").strip()
    phone = (data.get("phone") or "").strip()
    if not email and not phone:
        raise HTTPException(status_code=400, detail="email_or_phone_required")
    source = data.get("source") or "manual"
    channel = data.get("channel") or channel_for_source(source)
    consent = dict(data.get("consent") or {})
    if consent and not consent.get("captured_at"):
        from datetime import UTC, datetime

        consent["captured_at"] = datetime.now(UTC).isoformat()
    result = _ingest.ingest(
        db,
        CanonicalLeadEvent(
            channel=channel,
            source=source,
            provider="admin_manual",
            external_event_id=f"manual:{ctx.user.id}:{uuid.uuid4()}",
            company_name=data["company_name"],
            primary_contact_name=data.get("primary_contact_name"),
            email=data.get("email"),
            phone=data.get("phone"),
            intent_type=data.get("intent_type") or "merchant",
            decision_status=data.get("decision_status") or "new",
            priority=data.get("priority") or "medium",
            status=data.get("status") or "new",
            message=data.get("internal_notes"),
            tags=list(data.get("tags") or []),
            custom_fields=dict(data.get("custom_fields") or {}),
            consent=consent,
            referred_by_merchant_id=data.get("referred_by_merchant_id"),
            actor=ctx,
            seed_conversation=bool(data.get("internal_notes")),
        ),
    )
    return LeadOut.model_validate(result.lead)


class ReferralLeadCreate(BaseModel):
    company_name: str
    primary_contact_name: str | None = None
    email: str | None = None
    phone: str | None = None
    referred_by_merchant_id: str
    internal_notes: str | None = None


@router.post("/leads/referral", response_model=LeadOut, status_code=201)
def create_referral_lead(
    body: ReferralLeadCreate,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> LeadOut:
    """Merchant-referred prospect — network moat ingest."""
    require_module(ctx, "crm")
    if not get_merchant(db, body.referred_by_merchant_id):
        raise HTTPException(status_code=404, detail="referring_merchant_not_found")
    if not (body.email or body.phone):
        raise HTTPException(status_code=422, detail="email_or_phone_required")
    result = _ingest.ingest(
        db,
        event_from_referral(
            company_name=body.company_name,
            email=body.email,
            phone=body.phone,
            contact_name=body.primary_contact_name,
            referred_by_merchant_id=body.referred_by_merchant_id,
            notes=body.internal_notes,
        ),
    )
    return LeadOut.model_validate(result.lead)


@router.get("/leads/referral-credits")
def list_lead_referral_credits(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    merchant_id: str | None = None,
    status: str | None = None,
    limit: int = 200,
) -> list[dict]:
    require_module(ctx, "crm_read")
    from porterchain_api.collaboration_engine.lead_ops import list_referral_credits

    return list_referral_credits(
        db, merchant_id=merchant_id, status=status, limit=min(limit, 500)
    )


@router.get("/leads/{lead_id}/assist")
def lead_assist(
    lead_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    """NVIDIA NIM / heuristic sales assist — never auto-sends."""
    require_module(ctx, "crm_read")
    lead = _crm.get_lead(db, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="lead_not_found")
    from porterchain_api.intelligence_engine.lead_assist import build_lead_assist

    return build_lead_assist(
        db,
        lead,
        flags={"phase2_intelligence": bool(settings.phase2_intelligence)},
        actor_id=ctx.user.id,
    )


class LeadAssistDecideRequest(BaseModel):
    proposal_id: str
    decision: str = Field(description="accept | reject")
    draft_reply: str | None = None
    decision_status: str | None = None


@router.post("/leads/{lead_id}/assist/decide")
def lead_assist_decide(
    lead_id: str,
    body: LeadAssistDecideRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> dict:
    require_module(ctx, "crm")
    lead = _crm.get_lead(db, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="lead_not_found")
    if body.decision not in ("accept", "reject"):
        raise HTTPException(status_code=422, detail="invalid_decision")
    applied: dict = {"proposal_id": body.proposal_id, "decision": body.decision}
    if body.decision == "accept":
        patch: dict = {}
        if body.decision_status:
            patch["decision_status"] = body.decision_status
        if body.draft_reply:
            notes = (lead.internal_notes or "").strip()
            reply = body.draft_reply.strip()
            patch["internal_notes"] = f"{notes}\n[Assist draft] {reply}".strip() if notes else f"[Assist draft] {reply}"
            # Seed outbound message on open conversation if present.
            convo = (
                db.query(CrmConversation)
                .filter(CrmConversation.lead_id == lead_id, CrmConversation.status == "open")
                .order_by(CrmConversation.updated_at.desc())
                .first()
            )
            if convo and reply:
                db.add(
                    CrmConversationMessage(
                        conversation_id=convo.id,
                        direction="outbound",
                        body=reply,
                        actor_type="staff",
                        actor_id=ctx.user.id,
                        metadata_json={"from_assist": True, "proposal_id": body.proposal_id},
                    )
                )
        if patch:
            lead = _crm.update_lead(db, lead_id, patch)
        applied["lead_id"] = lead.id
        applied["decision_status"] = lead.decision_status
    _crm.log_activity(
        db,
        entity_type="lead",
        entity_id=lead_id,
        activity_type="note",
        subject=f"Assist {body.decision}: {body.proposal_id}",
        body=body.draft_reply if body.decision == "accept" else None,
        actor_id=ctx.user.id,
        metadata={
            "from_assist": True,
            "assist_decision": body.decision,
            "proposal_id": body.proposal_id,
        },
    )
    return {"ok": True, **applied}


@router.get("/leads/calendar", response_model=list[TaskOut])
def list_lead_calendar_tasks(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    due_after: datetime | None = None,
    due_before: datetime | None = None,
    limit: int = Query(200, le=500),
) -> list[TaskOut]:
    """Week/range view of call + meeting tasks linked to CRM leads."""
    require_module(ctx, "crm_read")
    rows = _crm.list_tasks(
        db,
        entity_type="lead",
        task_types=["call", "meeting"],
        due_after=due_after,
        due_before=due_before,
        limit=limit,
    )
    return [TaskOut.model_validate(t) for t in rows]


@router.get("/leads/{lead_id}", response_model=LeadOut)
def get_lead(
    lead_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> LeadOut:
    require_module(ctx, "crm_read")
    lead = _crm.get_lead(db, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="lead_not_found")
    return LeadOut.model_validate(lead)


class MergeResolveRequest(BaseModel):
    action: str = Field(description="accept | reject")


@router.post("/leads/{lead_id}/merge", response_model=LeadOut)
def resolve_lead_merge(
    lead_id: str,
    body: MergeResolveRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> LeadOut:
    """Accept (fold into merge_candidate_of) or reject soft-duplicate queue item."""
    require_module(ctx, "crm")
    from porterchain_api.collaboration_engine.lead_ops import resolve_merge_candidate

    try:
        lead = resolve_merge_candidate(
            db,
            lead_id=lead_id,
            action=body.action,
            actor_id=ctx.user.id if ctx.user else None,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return LeadOut.model_validate(lead)


@router.get("/leads/{lead_id}/identities")
def list_lead_identities(
    lead_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> list[dict]:
    require_module(ctx, "crm_read")
    if not _crm.get_lead(db, lead_id):
        raise HTTPException(status_code=404, detail="lead_not_found")
    rows = db.query(CrmLeadIdentity).filter(CrmLeadIdentity.lead_id == lead_id).all()
    return [
        {
            "id": r.id,
            "kind": r.kind,
            "value_normalized": r.value_normalized,
            "raw_value": r.raw_value,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.get("/leads/{lead_id}/conversations")
def list_lead_conversations(
    lead_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> list[dict]:
    require_module(ctx, "crm_read")
    if not _crm.get_lead(db, lead_id):
        raise HTTPException(status_code=404, detail="lead_not_found")
    convos = (
        db.query(CrmConversation)
        .filter(CrmConversation.lead_id == lead_id)
        .order_by(CrmConversation.updated_at.desc())
        .all()
    )
    out: list[dict] = []
    for c in convos:
        msgs = (
            db.query(CrmConversationMessage)
            .filter(CrmConversationMessage.conversation_id == c.id)
            .order_by(CrmConversationMessage.occurred_at.asc())
            .limit(200)
            .all()
        )
        out.append(
            {
                "id": c.id,
                "channel": c.channel,
                "status": c.status,
                "external_thread_id": c.external_thread_id,
                "messages": [
                    {
                        "id": m.id,
                        "direction": m.direction,
                        "body": m.body,
                        "actor_type": m.actor_type,
                        "occurred_at": m.occurred_at.isoformat() if m.occurred_at else None,
                    }
                    for m in msgs
                ],
            }
        )
    return out


@router.post("/leads/{lead_id}/conversations/{conversation_id}/messages")
def append_conversation_message(
    lead_id: str,
    conversation_id: str,
    body: dict,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> dict:
    require_module(ctx, "crm")
    if not _crm.get_lead(db, lead_id):
        raise HTTPException(status_code=404, detail="lead_not_found")
    convo = db.get(CrmConversation, conversation_id)
    if not convo or convo.lead_id != lead_id:
        raise HTTPException(status_code=404, detail="conversation_not_found")
    text = str(body.get("body") or "").strip()
    if not text:
        raise HTTPException(status_code=422, detail="body_required")
    msg = CrmConversationMessage(
        conversation_id=convo.id,
        direction=str(body.get("direction") or "outbound"),
        body=text,
        actor_type="staff",
        actor_id=ctx.user.id,
    )
    db.add(msg)
    lead = _crm.get_lead(db, lead_id)
    if lead:
        from porterchain_api.collaboration_engine.crm_helpers import _now

        lead.last_touch_at = _now()
    db.commit()
    db.refresh(msg)
    return {
        "id": msg.id,
        "direction": msg.direction,
        "body": msg.body,
        "occurred_at": msg.occurred_at.isoformat() if msg.occurred_at else None,
    }


@router.patch("/leads/{lead_id}", response_model=LeadOut)
def update_lead(
    lead_id: str,
    body: LeadUpdate,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> LeadOut:
    require_module(ctx, "crm")
    data = body.model_dump(exclude_unset=True)
    if not data:
        lead = _crm.get_lead(db, lead_id)
        if not lead:
            raise HTTPException(status_code=404, detail="lead_not_found")
        return LeadOut.model_validate(lead)
    try:
        lead = _crm.update_lead(db, lead_id, data)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="lead_not_found") from exc
    return LeadOut.model_validate(lead)


@router.post("/leads/{lead_id}/convert")
def convert_lead(
    lead_id: str,
    body: LeadConvertRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Lead → company (+ deal); optional merchant / customer / driver_partner branch."""
    require_module(ctx, "crm")
    lead = _crm.get_lead(db, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="lead_not_found")

    outcome = (body.outcome or lead.intent_type or "merchant").strip().lower()
    if outcome not in ("merchant", "retail_customer", "driver_partner"):
        outcome = "merchant"

    # Merchant spine (default): company + deal (+ optional seat).
    try:
        result = _crm.convert_lead(
            db,
            ctx,
            lead_id,
            create_deal=body.create_deal if outcome == "merchant" else False,
            deal_name=body.deal_name,
            expected_revenue_cents=body.expected_revenue_cents,
            target_stage=body.target_stage,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="lead_not_found") from exc

    out: dict = {**result, "to_merchant": body.to_merchant, "outcome": outcome}

    if outcome == "merchant" and body.to_merchant and result.get("company_id"):
        try:
            merchant = _crm.convert_company_to_merchant(
                db, ctx, str(result["company_id"]), settings=settings
            )
            out["merchant"] = merchant
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Refresh lead after convert mutations
    lead = _crm.get_lead(db, lead_id) or lead

    from porterchain_api.collaboration_engine.lead_scoring import clear_score_priors_cache

    clear_score_priors_cache()

    if outcome == "merchant" and lead.referred_by_merchant_id:
        from porterchain_api.collaboration_engine.lead_ops import grant_referral_credit

        credit = grant_referral_credit(
            db,
            lead=lead,
            company_id=result.get("company_id"),
            settings=settings,
        )
        if credit:
            db.commit()
            out["referral_credit"] = {
                "id": credit.id,
                "amount_cents": credit.amount_cents,
                "status": credit.status,
            }

    from porterchain_api.collaboration_engine.lead_capi import emit_lead_conversion_events

    out["capi"] = emit_lead_conversion_events(
        db, lead, event_name="LeadConverted", settings=settings
    )

    if outcome == "retail_customer" and lead.email:
        from porterchain_api.booking_engine.customer_service import CustomerService

        customer = CustomerService().ensure_from_email(
            db, email=lead.email, phone=lead.phone
        )
        db.commit()
        out["customer_id"] = customer.id
        _crm.update_lead(
            db,
            lead_id,
            {"intent_type": "retail_customer", "decision_status": "converted", "status": "converted"},
        )
        _crm.log_activity(
            db,
            entity_type="lead",
            entity_id=lead_id,
            activity_type="status_change",
            subject="Converted to retail customer",
            actor_id=ctx.user.id,
        )

    if outcome == "driver_partner":
        _crm.update_lead(
            db,
            lead_id,
            {
                "intent_type": "driver_partner",
                "decision_status": "converted",
                "status": "converted",
                "tags": list({*(lead.tags or []), "driver_partner_converted"}),
            },
        )
        _crm.create_task(
            db,
            ctx,
            {
                "title": f"Onboard driver partner: {lead.company_name}",
                "task_type": "follow_up",
                "entity_type": "lead",
                "entity_id": lead_id,
                "priority": "high",
            },
        )
        out["driver_partner"] = {"queued": True, "hint": "/drivers"}
        _crm.log_activity(
            db,
            entity_type="lead",
            entity_id=lead_id,
            activity_type="status_change",
            subject="Converted to driver partner queue",
            actor_id=ctx.user.id,
        )

    return out


@router.delete("/leads/{lead_id}", status_code=204)
def delete_lead(
    lead_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> None:
    """Hard-delete a CRM lead. Super_admin only (SpiceDB system_all)."""
    try:
        require_module(ctx, "system:all")
    except PermissionError as exc:
        _perm(exc)
    try:
        _crm.delete_lead(db, lead_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="lead_not_found") from exc
