"""Public capacity-guide ingest — leads, transcript, slots, appointments."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from porterchain_api.collaboration_engine import CrmSalesService
from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db
from porterchain_api.domain.crm_states import LeadPriority, LeadStatus
from porterchain_api.routers.public_ingest_auth import verify_public_ingest_key
from porterchain_api.schemas_public import (
    PublicGuideAppointmentCreate,
    PublicGuideAppointmentResponse,
    PublicGuideLeadCreate,
    PublicGuideLeadResponse,
    PublicGuideSlot,
    PublicGuideSlotsResponse,
    PublicGuideTranscriptCreate,
    PublicGuideTranscriptResponse,
)

router = APIRouter(prefix="/v1/public/guide", tags=["public-guide"])
_crm = CrmSalesService()

GUIDE_SOURCE = "website_capacity_guide"
GUIDE_TZ = ZoneInfo("America/Toronto")
TRANSCRIPT_MAX_CHARS = 16_000
TRANSCRIPT_MAX_TURNS = 40
SLOT_HOURS = range(9, 17)  # 09:00–16:00 starts → end by 17:00
SLOT_COUNT = 10


def _phone_trim(raw: str | None) -> str | None:
    phone_raw = (raw or "").strip() or None
    return phone_raw[:32] if phone_raw else None


def _merge_custom(existing: dict | None, patch: dict) -> dict:
    base = dict(existing or {})
    for key, value in patch.items():
        if value is not None and value != "":
            base[key] = value
    return base


def _append_transcript(existing: dict | None, turns: list[dict], summary: str | None) -> dict:
    fields = dict(existing or {})
    history = fields.get("transcript")
    if not isinstance(history, list):
        history = []
    for turn in turns:
        history.append(
            {
                "role": turn.get("role", "user"),
                "content": str(turn.get("content", ""))[:4000],
                "at": datetime.now(UTC).isoformat(),
            }
        )
    history = history[-TRANSCRIPT_MAX_TURNS:]
    # Cap serialized size roughly
    while history and len(str(history)) > TRANSCRIPT_MAX_CHARS:
        history = history[1:]
    fields["transcript"] = history
    if summary:
        fields["transcript_summary"] = summary[:4000]
    return fields


def _next_slots(*, meeting_type: str, count: int = SLOT_COUNT) -> list[PublicGuideSlot]:
    now = datetime.now(GUIDE_TZ)
    cursor = now + timedelta(hours=1)
    # Snap to next half-hour boundary
    if cursor.minute < 30:
        cursor = cursor.replace(minute=30, second=0, microsecond=0)
    else:
        cursor = (cursor + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)

    slots: list[PublicGuideSlot] = []
    guard = 0
    while len(slots) < count and guard < 400:
        guard += 1
        if cursor.weekday() < 5 and cursor.hour in SLOT_HOURS:
            if cursor > now:
                end = cursor + timedelta(minutes=30)
                try:
                    label = cursor.strftime("%a %b %-d · %-I:%M %p")
                except ValueError:
                    label = cursor.strftime("%a %b %d · %I:%M %p")
                slots.append(
                    PublicGuideSlot(
                        start=cursor.astimezone(UTC),
                        end=end.astimezone(UTC),
                        label=label,
                        meeting_type=meeting_type,
                    )
                )
        cursor += timedelta(minutes=30)
    return slots


@router.post("/leads", response_model=PublicGuideLeadResponse, status_code=201)
def upsert_guide_lead(
    body: PublicGuideLeadCreate,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    x_ingest_key: Annotated[str | None, Header(alias="X-Ingest-Key")] = None,
) -> PublicGuideLeadResponse:
    verify_public_ingest_key(settings, x_ingest_key)

    email = body.email.strip()
    if not email or "@" not in email:
        raise HTTPException(status_code=422, detail="email_required")

    contact_name = (body.name or "").strip() or email.split("@", 1)[0]
    company_name = (body.business_name or "").strip() or contact_name
    phone = _phone_trim(body.phone)

    existing = _crm.find_lead_by_email(db, email)

    custom_patch = {
        "form": "capacity_guide",
        "intent": body.intent,
        "session_id": body.session_id,
        "source_page": body.source_page or "/",
        "utm_source": body.utm_source,
        "utm_campaign": body.utm_campaign,
        "utm_medium": body.utm_medium,
        **({"phone_full": (body.phone or "").strip()} if body.phone and phone != (body.phone or "").strip() else {}),
        **({"guide_notes": body.notes} if body.notes else {}),
    }

    if existing:
        patch: dict = {
            "custom_fields": _merge_custom(existing.custom_fields, custom_patch),
        }
        if contact_name and contact_name != existing.primary_contact_name:
            patch["primary_contact_name"] = contact_name
        if company_name and (not existing.company_name or existing.company_name == existing.primary_contact_name):
            patch["company_name"] = company_name
        if phone:
            patch["phone"] = phone
        if body.notes:
            note = (body.notes or "").strip()
            prev = (existing.internal_notes or "").strip()
            patch["internal_notes"] = f"{prev}\n{note}".strip() if prev and note not in prev else (note or prev or None)
        if existing.source != GUIDE_SOURCE and (existing.source or "").startswith("website_"):
            # Keep original source; tag capacity guide in custom_fields only
            pass
        elif not existing.source:
            patch["source"] = GUIDE_SOURCE
        lead = _crm.update_lead(db, existing.id, patch)
        _crm.log_activity(
            db,
            entity_type="lead",
            entity_id=lead.id,
            activity_type="note",
            subject="Capacity guide contact updated",
            body=body.notes,
            metadata={"session_id": body.session_id, "source": GUIDE_SOURCE},
        )
        return PublicGuideLeadResponse(
            id=lead.id,
            created=False,
            status=lead.status,
            email=lead.email or email,
            phone=lead.phone,
        )

    lead = _crm.create_lead(
        db,
        None,
        {
            "company_name": company_name,
            "primary_contact_name": contact_name,
            "email": email,
            "phone": phone,
            "source": GUIDE_SOURCE,
            "status": LeadStatus.NEW.value,
            "priority": LeadPriority.HIGH.value
            if (body.intent or "") in ("quote", "call", "meeting", "demo")
            else LeadPriority.MEDIUM.value,
            "internal_notes": (body.notes or "").strip() or None,
            "custom_fields": {k: v for k, v in custom_patch.items() if v},
            "tags": [t for t in ["capacity_guide", body.intent] if t],
        },
    )
    return PublicGuideLeadResponse(
        id=lead.id,
        created=True,
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

    fields = _append_transcript(lead.custom_fields, turns, body.summary)
    if body.session_id:
        fields["session_id"] = body.session_id
    _crm.update_lead(db, lead.id, {"custom_fields": fields})

    excerpt = body.summary or "\n".join(
        f"{t['role']}: {t['content'][:500]}" for t in turns[-6:]
    )
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
    slots = _next_slots(meeting_type=meeting_type)
    return PublicGuideSlotsResponse(
        timezone="America/Toronto",
        meeting_type=meeting_type,
        slots=slots,
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
        "custom_fields": _merge_custom(
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
