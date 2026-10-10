"""Public capacity-guide ingest — leads, transcript, slots, appointments."""

from __future__ import annotations

from datetime import UTC
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from sqlalchemy.orm import Session

from porterchain_api.booking_engine.visitor_tracking_service import (
    VisitorTrackingService,
)
from porterchain_api.collaboration_engine import CrmSalesService
from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db
from porterchain_api.domain.crm_states import LeadPriority, LeadStatus
from porterchain_api.routers.public_guide_support import (
    GUIDE_SOURCE,
    GUIDE_TZ,
    append_transcript,
    merge_custom,
    next_slots,
    phone_trim,
)
from porterchain_api.routers.public_ingest_auth import verify_public_ingest_key
from porterchain_api.schemas_public import (
    PublicGuideAppointmentCreate,
    PublicGuideAppointmentResponse,
    PublicGuideLeadCreate,
    PublicGuideLeadResponse,
    PublicGuideSlotsResponse,
    PublicGuideTranscriptCreate,
    PublicGuideTranscriptResponse,
)

router = APIRouter(prefix="/v1/public/guide", tags=["public-guide"])
_crm = CrmSalesService()
_visitors = VisitorTrackingService()


def _guide_consent(body: PublicGuideLeadCreate, *, ip: str | None = None) -> dict:
    from porterchain_api.collaboration_engine.lead_consent import (
        casl_evidence,
        form_consent_evidence,
    )

    if body.marketing_consent is not None:
        return form_consent_evidence(
            marketing=bool(body.marketing_consent),
            source="capacity_guide",
            ip=ip,
            locale=body.locale,
            page=body.source_page,
        )
    # Cookie-banner flags are stripped inside casl_evidence.
    return casl_evidence(body.consent, source="capacity_guide", actor="lead")


@router.post("/leads", response_model=PublicGuideLeadResponse, status_code=201)
def upsert_guide_lead(
    body: PublicGuideLeadCreate,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    x_ingest_key: Annotated[str | None, Header(alias="X-Ingest-Key")] = None,
) -> PublicGuideLeadResponse:
    verify_public_ingest_key(settings, x_ingest_key)
    from porterchain_api.marketing_site.form_guard import client_ip, looks_like_bot

    # The guide calls this server-to-server several times per chat, so only the
    # honeypot / fill-time checks apply here (no per-IP form rate limit).
    if looks_like_bot(
        honeypot=body.website, form_elapsed_ms=body.form_elapsed_ms, min_fill_seconds=2
    ):
        raise HTTPException(status_code=422, detail="rejected")
    guide_ip = client_ip(request)

    email = body.email.strip()
    if not email or "@" not in email:
        raise HTTPException(status_code=422, detail="email_required")

    contact_name = (body.name or "").strip() or email.split("@", 1)[0]
    company_name = (body.business_name or "").strip() or contact_name
    phone = phone_trim(body.phone)

    visitor_key = (body.visitor_id or body.session_id or "").strip() or None
    if visitor_key:
        _visitors.ensure_session(
            db,
            session_id=visitor_key[:64],
            utm_source=body.utm_source,
            utm_medium=body.utm_medium,
            utm_campaign=body.utm_campaign,
            signals={
                "intent": body.intent,
                "guide_stage": body.guide_stage or "capture",
                "source_page": body.source_page or "/",
                "from_page": "capacity_guide",
            },
        )

    custom_patch = {
        "form": "capacity_guide",
        "intent": body.intent,
        "session_id": body.session_id or visitor_key,
        "visitor_id": visitor_key,
        "guide_stage": body.guide_stage,
        "source_page": body.source_page or "/",
        **(
            {"phone_full": (body.phone or "").strip()}
            if body.phone and phone != (body.phone or "").strip()
            else {}
        ),
        **({"guide_notes": body.notes} if body.notes else {}),
    }
    external_ids = {}
    if visitor_key:
        external_ids["visitor_session"] = visitor_key[:64]

    import uuid

    from porterchain_api.collaboration_engine.lead_ingest_service import (
        CanonicalLeadEvent,
        LeadIngestService,
    )
    from porterchain_api.domain.crm_states import LeadIntentType, LeadSourceChannel

    result = LeadIngestService().ingest(
        db,
        CanonicalLeadEvent(
            channel=LeadSourceChannel.CAPACITY_GUIDE.value,
            source=GUIDE_SOURCE,
            provider="website_capacity_guide",
            external_event_id=(
                f"guide:{email.lower()}:{visitor_key or body.guide_stage or 'capture'}:{uuid.uuid4().hex[:12]}"
            ),
            company_name=company_name,
            primary_contact_name=contact_name,
            email=email,
            phone=phone,
            intent_type=LeadIntentType.MERCHANT.value,
            priority=LeadPriority.HIGH.value
            if (body.intent or "") in ("quote", "call", "meeting", "demo")
            else LeadPriority.MEDIUM.value,
            status=LeadStatus.NEW.value,
            message=(body.notes or "").strip() or None,
            tags=[t for t in ["capacity_guide", body.intent] if t],
            custom_fields={k: v for k, v in custom_patch.items() if v},
            consent=_guide_consent(body, ip=guide_ip),
            attribution={
                k: v
                for k, v in {
                    "utm_source": body.utm_source,
                    "utm_campaign": body.utm_campaign,
                    "utm_medium": body.utm_medium,
                    "referred_by_merchant_id": (body.referred_by_merchant_id or "").strip() or None,
                }.items()
                if v
            },
            referred_by_merchant_id=(body.referred_by_merchant_id or "").strip() or None,
            external_ids=external_ids,
            seed_conversation=bool((body.notes or "").strip()),
        ),
    )
    lead = result.lead
    return PublicGuideLeadResponse(
        id=lead.id,
        created=result.created,
        status=lead.status,
        email=lead.email or email,
        phone=lead.phone,
    )


@router.post("/transcript", response_model=PublicGuideTranscriptResponse)
def save_guide_transcript(
    body: PublicGuideTranscriptCreate,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    x_ingest_key: Annotated[str | None, Header(alias="X-Ingest-Key")] = None,
) -> PublicGuideTranscriptResponse:
    verify_public_ingest_key(settings, x_ingest_key)

    lead = _crm.get_lead(db, body.lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="lead_not_found")

    turns = [{"role": t.role, "content": t.content} for t in body.turns]
    if not turns and not body.summary:
        raise HTTPException(status_code=422, detail="turns_or_summary_required")

    fields = append_transcript(lead.custom_fields, turns, body.summary)
    if body.session_id:
        fields["session_id"] = body.session_id
        fields["visitor_id"] = fields.get("visitor_id") or body.session_id
        _visitors.ensure_session(
            db,
            session_id=body.session_id[:64],
            signals={
                "guide_stage": "capture",
                "intent": (lead.custom_fields or {}).get("intent")
                if isinstance(lead.custom_fields, dict)
                else None,
            },
        )
    _crm.update_lead(db, lead.id, {"custom_fields": fields})

    excerpt = body.summary or "\n".join(f"{t['role']}: {t['content'][:500]}" for t in turns[-6:])
    _crm.log_activity(
        db,
        entity_type="lead",
        entity_id=lead.id,
        activity_type="note",
        subject="Capacity guide chat",
        body=excerpt[:4000],
        metadata={"session_id": body.session_id, "turn_count": len(turns)},
    )
    history = fields.get("transcript") if isinstance(fields.get("transcript"), list) else []
    return PublicGuideTranscriptResponse(lead_id=lead.id, turn_count=len(history))


@router.get("/slots", response_model=PublicGuideSlotsResponse)
def list_guide_slots(
    meeting_type: str = Query(default="call", pattern="^(call|meeting)$"),
    settings: Settings = Depends(get_settings),
    x_ingest_key: Annotated[str | None, Header(alias="X-Ingest-Key")] = None,
) -> PublicGuideSlotsResponse:
    verify_public_ingest_key(settings, x_ingest_key)
    return PublicGuideSlotsResponse(
        timezone="America/Toronto",
        meeting_type=meeting_type,
        slots=next_slots(meeting_type=meeting_type),
    )


@router.post("/appointments", response_model=PublicGuideAppointmentResponse, status_code=201)
def book_guide_appointment(
    body: PublicGuideAppointmentCreate,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    x_ingest_key: Annotated[str | None, Header(alias="X-Ingest-Key")] = None,
) -> PublicGuideAppointmentResponse:
    verify_public_ingest_key(settings, x_ingest_key)

    meeting_type = (body.meeting_type or "call").strip().lower()
    if meeting_type not in ("call", "meeting"):
        raise HTTPException(status_code=422, detail="invalid_meeting_type")

    lead = _crm.get_lead(db, body.lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="lead_not_found")
    if not (lead.phone or "").strip():
        raise HTTPException(status_code=422, detail="phone_required")
    if not (lead.email or "").strip():
        raise HTTPException(status_code=422, detail="email_required")

    due_at = body.start
    if due_at.tzinfo is None:
        due_at = due_at.replace(tzinfo=UTC)
    due_at = due_at.astimezone(UTC)

    name = lead.primary_contact_name or lead.company_name or "Lead"
    kind = "call" if meeting_type == "call" else "meeting"
    title = f"Capacity guide {kind} — {name}"

    task = _crm.create_task(
        db,
        None,
        {
            "title": title,
            "description": (body.notes or "").strip()
            or f"Booked via website capacity guide. Session: {body.session_id or 'n/a'}",
            "task_type": kind,
            "priority": LeadPriority.HIGH.value,
            "entity_type": "lead",
            "entity_id": lead.id,
            "due_at": due_at,
            "status": "open",
        },
    )

    status_patch: dict = {
        "custom_fields": merge_custom(
            lead.custom_fields,
            {
                "session_id": body.session_id,
                "last_appointment_task_id": task.id,
                "last_appointment_at": due_at.isoformat(),
                "last_appointment_type": kind,
            },
        )
    }
    if lead.status == LeadStatus.NEW.value:
        status_patch["status"] = LeadStatus.CONTACTED.value
    _crm.update_lead(db, lead.id, status_patch)

    local = due_at.astimezone(GUIDE_TZ)
    try:
        when = local.strftime("%a %b %-d · %-I:%M %p %Z")
    except ValueError:
        when = local.strftime("%a %b %d · %I:%M %p %Z")

    _crm.log_activity(
        db,
        entity_type="lead",
        entity_id=lead.id,
        activity_type="meeting" if kind == "meeting" else "call",
        subject=title,
        body=f"Scheduled for {when}",
        metadata={"task_id": task.id, "session_id": body.session_id},
    )

    return PublicGuideAppointmentResponse(
        task_id=task.id,
        lead_id=lead.id,
        meeting_type=kind,
        due_at=due_at,
        title=title,
    )
