"""Admin CRM leads — list, detail, status updates, appointment calendar."""

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
from porterchain_api.platform.pagination import as_page, clamp_page
from porterchain_api.schemas_crm import (
    LeadConvertRequest,
    LeadCreate,
    LeadOut,
    LeadUpdate,
)
from pydantic import BaseModel, Field

_crm = CrmSalesService()
_ingest = LeadIngestService()


class LeadListPage(BaseModel):
    items: list[LeadOut]
    total: int
    limit: int
    offset: int


@router.get("/leads", response_model=LeadListPage)
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
    has_open_draft: bool | None = None,
    nurture_scheduled: bool | None = None,
    has_abandoned: bool | None = None,
    search: str | None = None,
    city: str | None = None,
    tag: str | None = None,
    has_phone: bool | None = None,
    awaiting_reply: bool | None = None,
    view: str | None = None,
    include_archived: bool = False,
    sort: str = "smart",
    limit: int | None = None,
    offset: int | None = None,
) -> dict:
    require_module(ctx, "crm_read")
    page_limit, page_offset = clamp_page(limit, offset, default=50, max_limit=500)
    filter_kwargs = dict(
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
        has_open_draft=has_open_draft,
        nurture_scheduled=nurture_scheduled,
        has_abandoned=has_abandoned,
        search=search,
        city=city,
        tag=tag,
        has_phone=has_phone,
        awaiting_reply=awaiting_reply,
        view=view,
        include_archived=include_archived,
        sort=sort,
    )
    total = _crm.count_leads(
        db,
        **{k: v for k, v in filter_kwargs.items() if k != "sort"},
    )
    rows = _crm.list_leads(db, **filter_kwargs, limit=page_limit, offset=page_offset)
    return as_page(
        [LeadOut.model_validate(row) for row in rows],
        total,
        page_limit,
        page_offset,
    )


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
    from porterchain_api.collaboration_engine.lead_consent import LEGAL_BASIS_VALUES, casl_evidence

    raw_consent = dict(data.get("consent") or {})
    if raw_consent.get("marketing") is True:
        basis = str(raw_consent.get("legal_basis") or "").strip().lower()
        if basis not in LEGAL_BASIS_VALUES:
            raise HTTPException(status_code=422, detail="legal_basis_required_for_marketing")
    consent = casl_evidence(
        raw_consent,
        source=f"admin_{source}",
        actor="staff",
        legal_basis=raw_consent.get("legal_basis"),
    )
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


@router.get("/leads/suppressions")
def list_lead_suppressions(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> dict:
    """List hashed DNC rows (no raw email/phone)."""
    require_module(ctx, "crm_read")
    from porterchain_api.crm_models import CrmSuppression

    total = db.query(CrmSuppression).count()
    rows = (
        db.query(CrmSuppression)
        .order_by(CrmSuppression.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {
        "items": [
            {
                "id": r.id,
                "hash_kind": r.hash_kind,
                "value_hash": r.value_hash,
                "source": r.source,
                "lead_id": r.lead_id,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/leads/privacy/ropa")
def get_lead_ropa(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
) -> dict:
    """Static CrmLead processing inventory (Art.30 / PIPEDA-style). No multi-region product."""
    require_module(ctx, "crm_read")
    from porterchain_api.collaboration_engine.lead_privacy import lead_ropa_inventory

    return lead_ropa_inventory()


@router.delete("/leads/suppressions/{suppression_id}", status_code=204)
def delete_lead_suppression(
    suppression_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> None:
    """Clear one suppression row (re-opt-in after staff review). Super-admin only."""
    try:
        require_module(ctx, "system:all")
    except PermissionError as exc:
        _perm(exc)
    from porterchain_api.crm_models import CrmSuppression

    row = db.get(CrmSuppression, suppression_id)
    if not row:
        raise HTTPException(status_code=404, detail="suppression_not_found")
    db.delete(row)
    db.commit()


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
    from porterchain_api.collaboration_engine.lead_assist_apply import (
        LeadAssistBlocked,
        apply_lead_assist_decision,
    )

    try:
        return apply_lead_assist_decision(
            db,
            _crm,
            lead,
            lead_id=lead_id,
            proposal_id=body.proposal_id,
            decision=body.decision,
            draft_reply=body.draft_reply,
            decision_status=body.decision_status,
            actor_id=ctx.user.id,
        )
    except LeadAssistBlocked as exc:
        raise HTTPException(status_code=409, detail=exc.code) from exc


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
    from porterchain_api.lead_convert_flow import convert_lead_with_outcome

    try:
        return convert_lead_with_outcome(
            db, _crm, ctx, lead, lead_id, body=body, settings=settings
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc) if str(exc) else "lead_not_found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/leads/{lead_id}/privacy/export")
def export_lead_privacy(
    lead_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> dict:
    require_module(ctx, "crm_read")
    from porterchain_api.collaboration_engine.lead_privacy import LeadPrivacyService
    from porterchain_api.crm_models import CrmLead

    lead = db.get(CrmLead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="lead_not_found")
    return LeadPrivacyService().export_lead(db, lead, actor_user_id=ctx.user.id)


@router.post("/leads/{lead_id}/privacy/delete-request")
def request_lead_privacy_deletion(
    lead_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    reason: str | None = None,
) -> dict:
    require_module(ctx, "crm")
    from porterchain_api.collaboration_engine.lead_privacy import LeadPrivacyService
    from porterchain_api.crm_models import CrmLead

    lead = db.get(CrmLead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="lead_not_found")
    out = LeadPrivacyService().request_deletion(
        db, lead, actor_user_id=ctx.user.id, reason=reason
    )
    db.commit()
    return out


@router.post("/leads/{lead_id}/privacy/erase")
def erase_lead_privacy(
    lead_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> dict:
    try:
        require_module(ctx, "system:all")
    except PermissionError as exc:
        _perm(exc)
    from porterchain_api.collaboration_engine.lead_privacy import LeadPrivacyError, LeadPrivacyService
    from porterchain_api.crm_models import CrmLead

    lead = db.get(CrmLead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="lead_not_found")
    try:
        out = LeadPrivacyService().erase_lead(db, lead, actor_user_id=ctx.user.id)
    except LeadPrivacyError as exc:
        raise HTTPException(status_code=409, detail=exc.code) from exc
    db.commit()
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
