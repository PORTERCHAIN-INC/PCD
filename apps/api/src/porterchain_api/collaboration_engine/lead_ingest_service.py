"""Lead Ingest Bus — single write path for multi-channel CRM leads.

Adapters normalize to CanonicalLeadEvent; this service owns identity resolve,
idempotent ingest events, create|merge, and optional conversation seed.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from porterchain_api.collaboration_engine.crm_activity import CrmActivityMixin
from porterchain_api.collaboration_engine.crm_helpers import CrmActor, _actor, _now
from porterchain_api.collaboration_engine.crm_leads import CrmLeadsMixin
from porterchain_api.crm_models import (
    CrmConversation,
    CrmConversationMessage,
    CrmLead,
    CrmLeadIdentity,
    CrmLeadIngestEvent,
)
from porterchain_api.domain.crm_states import (
    LeadDecisionStatus,
    LeadIdentityKind,
    LeadIntentType,
    LeadPriority,
    LeadStatus,
    channel_for_source,
)


def normalize_email(email: str | None) -> str | None:
    if not email or not isinstance(email, str):
        return None
    value = email.strip().lower()
    return value if value and "@" in value else None


def normalize_phone_e164(phone: str | None, *, default_region: str = "CA") -> str | None:
    """Best-effort E.164 for NANP; returns None if too short."""
    if not phone or not isinstance(phone, str):
        return None
    digits = re.sub(r"\D", "", phone.strip())
    if not digits:
        return None
    if default_region in ("CA", "US") and len(digits) == 10:
        digits = "1" + digits
    if len(digits) < 10:
        return None
    return f"+{digits}"


@dataclass
class CanonicalLeadEvent:
    channel: str
    source: str
    provider: str
    external_event_id: str
    company_name: str
    primary_contact_name: str | None = None
    email: str | None = None
    phone: str | None = None
    intent_type: str = LeadIntentType.MERCHANT.value
    priority: str = LeadPriority.MEDIUM.value
    status: str = LeadStatus.NEW.value
    decision_status: str = LeadDecisionStatus.NEW.value
    message: str | None = None
    tags: list[str] = field(default_factory=list)
    custom_fields: dict[str, Any] = field(default_factory=dict)
    consent: dict[str, Any] = field(default_factory=dict)
    attribution: dict[str, Any] = field(default_factory=dict)
    external_ids: dict[str, str] = field(default_factory=dict)
    referred_by_merchant_id: str | None = None
    actor: CrmActor | None = None
    seed_conversation: bool = True
    sla_first_response_minutes: int = 60


@dataclass
class IngestResult:
    lead: CrmLead
    created: bool
    merged: bool
    merge_candidate: bool
    ingest_event_id: str


class LeadIngestService:
    """Fan-in ingest with deterministic identity matching."""

    def ingest(self, db: Session, event: CanonicalLeadEvent) -> IngestResult:
        existing_evt = (
            db.query(CrmLeadIngestEvent)
            .filter(
                CrmLeadIngestEvent.provider == event.provider,
                CrmLeadIngestEvent.external_event_id == event.external_event_id,
            )
            .first()
        )
        if existing_evt and existing_evt.lead_id:
            lead = db.get(CrmLead, existing_evt.lead_id)
            if lead:
                return IngestResult(
                    lead=lead,
                    created=False,
                    merged=False,
                    merge_candidate=bool(lead.merge_candidate_of),
                    ingest_event_id=existing_evt.id,
                )

        email = normalize_email(event.email)
        phone = normalize_phone_e164(event.phone)
        channel = event.channel or channel_for_source(event.source)

        identities: list[tuple[str, str, str | None]] = []
        if email:
            identities.append((LeadIdentityKind.EMAIL.value, email, event.email))
        if phone:
            identities.append((LeadIdentityKind.PHONE_E164.value, phone, event.phone))
        for kind, raw in (event.external_ids or {}).items():
            if not raw:
                continue
            identities.append((kind, str(raw).strip().lower(), str(raw)))

        matched = self._resolve_lead(db, identities)
        merge_candidate = False
        created = False
        merged = False

        custom = dict(event.custom_fields or {})
        for k, v in (event.attribution or {}).items():
            if v is not None and v != "":
                custom.setdefault(k, v)
        if event.message:
            custom.setdefault("message", event.message)

        now = _now()
        from porterchain_api.collaboration_engine.lead_ops import sla_minutes_for_channel

        sla_mins = sla_minutes_for_channel(channel)
        # Explicit per-event override only when adapters set a non-default value.
        if event.sla_first_response_minutes and event.sla_first_response_minutes != 60:
            sla_mins = max(5, int(event.sla_first_response_minutes))
        sla_due = now + timedelta(minutes=sla_mins)

        if matched:
            lead = matched
            merged = True
            self._merge_fields(
                lead,
                db=db,
                company_name=event.company_name,
                contact_name=event.primary_contact_name,
                email=email,
                phone=phone[:32] if phone else None,
                source=event.source,
                channel=channel,
                intent_type=event.intent_type,
                priority=event.priority,
                custom_fields=custom,
                consent=event.consent,
                referred_by_merchant_id=event.referred_by_merchant_id,
                notes=event.message,
            )
            lead.last_touch_at = now
            if not lead.sla_first_response_due_at and lead.status == LeadStatus.NEW.value:
                lead.sla_first_response_due_at = sla_due
        else:
            soft = self._soft_company_match(db, event.company_name, email)
            lead = CrmLead(
                company_name=event.company_name,
                primary_contact_name=event.primary_contact_name,
                email=email,
                phone=(phone[:32] if phone else None),
                source=event.source,
                channel=channel,
                intent_type=event.intent_type or LeadIntentType.MERCHANT.value,
                decision_status=event.decision_status or LeadDecisionStatus.NEW.value,
                status=event.status or LeadStatus.NEW.value,
                priority=event.priority or LeadPriority.MEDIUM.value,
                tags=list(event.tags or []),
                internal_notes=(event.message or "").strip() or None,
                custom_fields=custom,
                consent=dict(event.consent or {}),
                referred_by_merchant_id=event.referred_by_merchant_id,
                assigned_to=_actor(event.actor),
                last_touch_at=now,
                sla_first_response_due_at=sla_due,
                merge_candidate_of=soft.id if soft else None,
            )
            lead.lead_score = CrmLeadsMixin.score_lead(lead, db=db)
            db.add(lead)
            db.flush()
            created = True
            merge_candidate = soft is not None

        for kind, value, raw in identities:
            self._ensure_identity(db, lead.id, kind, value, raw)

        if event.seed_conversation and event.message:
            self._seed_message(db, lead, channel=channel, body=event.message)

        evt_id = str(uuid.uuid4())
        ingest = CrmLeadIngestEvent(
            id=evt_id,
            provider=event.provider,
            external_event_id=event.external_event_id,
            channel=channel,
            lead_id=lead.id,
            payload={
                "source": event.source,
                "email": email,
                "phone": phone,
                "external_ids": event.external_ids,
                "attribution": event.attribution,
            },
            status="processed",
            processed_at=now if isinstance(now, datetime) else datetime.now(UTC),
        )
        db.add(ingest)

        if not lead.assigned_to:
            from porterchain_api.collaboration_engine.lead_ops import apply_territory_assignment

            apply_territory_assignment(db, lead)

        from porterchain_api.collaboration_engine.lead_ops import (
            notify_unassigned_high_priority,
        )

        notify_unassigned_high_priority(db, lead)

        if created:
            from porterchain_api.collaboration_engine.lead_nurture import (
                apply_nurture_after_ingest,
            )
            from porterchain_api.config import get_settings

            apply_nurture_after_ingest(
                db,
                lead,
                created=True,
                website_url=getattr(get_settings(), "website_url", "") or "",
            )

        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            # Race on idempotency or identity unique — re-read and return.
            raced = (
                db.query(CrmLeadIngestEvent)
                .filter(
                    CrmLeadIngestEvent.provider == event.provider,
                    CrmLeadIngestEvent.external_event_id == event.external_event_id,
                )
                .first()
            )
            if raced and raced.lead_id:
                lead2 = db.get(CrmLead, raced.lead_id)
                if lead2:
                    return IngestResult(
                        lead=lead2,
                        created=False,
                        merged=True,
                        merge_candidate=bool(lead2.merge_candidate_of),
                        ingest_event_id=raced.id,
                    )
            raise

        db.refresh(lead)
        CrmActivityMixin().log_activity(
            db,
            entity_type="lead",
            entity_id=lead.id,
            activity_type="system",
            subject=(
                f"Lead ingested from {event.source}"
                if created
                else f"Lead merged ingest from {event.source}"
            ),
            actor_id=_actor(event.actor),
            metadata={"provider": event.provider, "channel": channel, "created": created},
        )
        return IngestResult(
            lead=lead,
            created=created,
            merged=merged,
            merge_candidate=merge_candidate,
            ingest_event_id=evt_id,
        )

    def _resolve_lead(
        self, db: Session, identities: list[tuple[str, str, str | None]]
    ) -> CrmLead | None:
        # Prefer provider IDs, then email, then phone.
        priority = {
            LeadIdentityKind.META_LEAD_ID.value: 0,
            LeadIdentityKind.WHATSAPP_WA_ID.value: 1,
            LeadIdentityKind.GBP_CONVERSATION_ID.value: 2,
            LeadIdentityKind.LINKEDIN_URN.value: 3,
            LeadIdentityKind.EMAIL.value: 4,
            LeadIdentityKind.PHONE_E164.value: 5,
            LeadIdentityKind.VISITOR_SESSION.value: 6,
            LeadIdentityKind.REFERRAL_CODE.value: 7,
        }
        ordered = sorted(identities, key=lambda t: priority.get(t[0], 99))
        for kind, value, _raw in ordered:
            row = (
                db.query(CrmLeadIdentity)
                .filter(
                    CrmLeadIdentity.kind == kind,
                    CrmLeadIdentity.value_normalized == value,
                )
                .first()
            )
            if row:
                lead = db.get(CrmLead, row.lead_id)
                if lead:
                    return lead
            if kind == LeadIdentityKind.EMAIL.value:
                lead = (
                    db.query(CrmLead)
                    .filter(CrmLead.email == value)
                    .order_by(CrmLead.created_at.desc())
                    .first()
                )
                if lead:
                    return lead
            if kind == LeadIdentityKind.PHONE_E164.value:
                from sqlalchemy import or_

                short = value[-10:] if len(value) >= 10 else value
                lead = (
                    db.query(CrmLead)
                    .filter(CrmLead.phone.isnot(None))
                    .filter(
                        or_(
                            CrmLead.phone == value,
                            CrmLead.phone == value.lstrip("+"),
                            CrmLead.phone.like(f"%{short}"),
                        )
                    )
                    .order_by(CrmLead.created_at.desc())
                    .first()
                )
                if lead:
                    return lead
        return None

    def _soft_company_match(
        self, db: Session, company_name: str, email: str | None
    ) -> CrmLead | None:
        name = (company_name or "").strip()
        if len(name) < 3:
            return None
        q = db.query(CrmLead).filter(CrmLead.company_name.ilike(name))
        if email:
            q = q.filter((CrmLead.email.is_(None)) | (CrmLead.email != email))
        return q.order_by(CrmLead.created_at.desc()).first()

    def _merge_fields(
        self,
        lead: CrmLead,
        *,
        db: Session,
        company_name: str,
        contact_name: str | None,
        email: str | None,
        phone: str | None,
        source: str,
        channel: str,
        intent_type: str,
        priority: str,
        custom_fields: dict[str, Any],
        consent: dict[str, Any],
        referred_by_merchant_id: str | None,
        notes: str | None,
    ) -> None:
        if company_name and (
            not lead.company_name or lead.company_name == (lead.primary_contact_name or "")
        ):
            lead.company_name = company_name
        if contact_name and not lead.primary_contact_name:
            lead.primary_contact_name = contact_name
        if email and not lead.email:
            lead.email = email
        if phone and not lead.phone:
            lead.phone = phone
        # Never downgrade richer channel attribution on merge; keep first source, tag new.
        tags = list(lead.tags or [])
        if source and source not in tags:
            tags.append(f"via:{source}")
        lead.tags = tags
        if channel and lead.channel in (None, "", "other", "website"):
            lead.channel = channel
        if intent_type and lead.intent_type in (None, "", LeadIntentType.UNKNOWN.value):
            lead.intent_type = intent_type
        if priority in (LeadPriority.HIGH.value, LeadPriority.URGENT.value):
            if lead.priority not in (LeadPriority.URGENT.value,):
                lead.priority = priority
        merged_custom = dict(lead.custom_fields or {})
        merged_custom.update({k: v for k, v in custom_fields.items() if v is not None})
        lead.custom_fields = merged_custom
        if consent:
            c = dict(lead.consent or {})
            c.update(consent)
            lead.consent = c
        if referred_by_merchant_id and not lead.referred_by_merchant_id:
            lead.referred_by_merchant_id = referred_by_merchant_id
        if notes:
            prev = (lead.internal_notes or "").strip()
            note = notes.strip()
            if note and note not in prev:
                lead.internal_notes = f"{prev}\n{note}".strip() if prev else note
        lead.lead_score = CrmLeadsMixin.score_lead(lead, db=db)

    def _ensure_identity(
        self,
        db: Session,
        lead_id: str,
        kind: str,
        value: str,
        raw: str | None,
    ) -> None:
        existing = (
            db.query(CrmLeadIdentity)
            .filter(
                CrmLeadIdentity.kind == kind,
                CrmLeadIdentity.value_normalized == value,
            )
            .first()
        )
        if existing:
            return
        db.add(
            CrmLeadIdentity(
                lead_id=lead_id,
                kind=kind,
                value_normalized=value,
                raw_value=(raw[:512] if raw else None),
            )
        )

    def _seed_message(
        self, db: Session, lead: CrmLead, *, channel: str, body: str
    ) -> None:
        text = (body or "").strip()
        if not text:
            return
        convo = (
            db.query(CrmConversation)
            .filter(
                CrmConversation.lead_id == lead.id,
                CrmConversation.channel == channel,
                CrmConversation.status == "open",
            )
            .order_by(CrmConversation.created_at.desc())
            .first()
        )
        if not convo:
            convo = CrmConversation(lead_id=lead.id, channel=channel, status="open")
            db.add(convo)
            db.flush()
        db.add(
            CrmConversationMessage(
                conversation_id=convo.id,
                direction="inbound",
                body=text,
                actor_type="prospect",
                metadata_json={"seed": True},
            )
        )


__all__ = [
    "CanonicalLeadEvent",
    "IngestResult",
    "LeadIngestService",
    "normalize_email",
    "normalize_phone_e164",
]
