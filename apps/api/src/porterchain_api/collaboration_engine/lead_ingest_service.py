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
from porterchain_api.collaboration_engine.lead_ingest_resolve import (
    LeadIngestResolveMixin,
)
from porterchain_api.crm_models import (
    CrmLead,
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


# Providers whose external_event_id is a real message id (thread idempotency).
_THREADED_PROVIDERS = frozenset(
    {
        "meta_messaging_whatsapp_business_account",
        "meta_messaging_page",
        "meta_messaging_instagram",
        "email_inbound",
    }
)


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
    # Bulk CSV / vendor import: skip nurture, unassigned alerts, soft-match, event bus.
    quiet: bool = False
    # Website calculator etc.: keep SLA/assignment but no automatic welcome email or nurture.
    skip_outreach: bool = False


@dataclass
class IngestResult:
    lead: CrmLead
    created: bool
    merged: bool
    merge_candidate: bool
    ingest_event_id: str


class LeadIngestService(LeadIngestResolveMixin):
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
        custom.pop("message_meta", None)
        for k, v in (event.attribution or {}).items():
            if v is not None and v != "":
                custom.setdefault(k, v)
        if event.message:
            custom.setdefault("message", event.message)

        now = _now()
        from porterchain_api.collaboration_engine.lead_ops import (
            sla_minutes_for_channel,
        )

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
            soft = None
            if not event.quiet:
                soft = self._soft_company_match(db, event.company_name, email)
            from porterchain_api.collaboration_engine.lead_suppression import (
                apply_consent_for_ingest,
            )

            consent_bag = apply_consent_for_ingest(
                db,
                event.consent if isinstance(event.consent, dict) else {},
                email=email,
                phone=phone[:32] if phone else None,
            )
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
                consent=consent_bag,
                referred_by_merchant_id=event.referred_by_merchant_id,
                assigned_to=_actor(event.actor),
                last_touch_at=now,
                sla_first_response_due_at=None if event.quiet else sla_due,
                merge_candidate_of=soft.id if soft else None,
            )
            lead.lead_score = CrmLeadsMixin.score_lead(
                lead, db=None if event.quiet else db
            )
            db.add(lead)
            db.flush()
            created = True
            merge_candidate = soft is not None

        for kind, value, raw in identities:
            self._ensure_identity(db, lead.id, kind, value, raw)

        self._stamp_visitor_spine(lead, event)

        if event.seed_conversation and event.message:
            self._seed_message(
                db,
                lead,
                channel=channel,
                body=event.message,
                external_message_id=(
                    event.external_event_id if event.provider in _THREADED_PROVIDERS else None
                ),
                metadata=event.custom_fields.get("message_meta") if event.custom_fields else None,
            )
            if not event.quiet:
                # Unified inbox: a person wrote to us and is waiting on a human.
                lead.awaiting_reply = True
                lead.last_inbound_at = now
                if lead.status == LeadStatus.ARCHIVED.value:
                    lead.status = LeadStatus.NEW.value

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

        if not event.quiet and not lead.assigned_to:
            from porterchain_api.collaboration_engine.lead_ops import (
                apply_territory_assignment,
            )

            apply_territory_assignment(db, lead)

        if not event.quiet:
            from porterchain_api.collaboration_engine.lead_ops import (
                notify_unassigned_high_priority,
            )

            notify_unassigned_high_priority(db, lead)
            from porterchain_api.collaboration_engine.lead_ops import notify_hot_lead

            notify_hot_lead(db, lead, created=created)

        if created and not event.quiet and not event.skip_outreach:
            from porterchain_api.collaboration_engine.lead_nurture import (
                apply_nurture_after_ingest,
            )
            from porterchain_api.config import get_settings

            settings = get_settings()
            website = getattr(settings, "website_url", "") or ""
            apply_nurture_after_ingest(
                db,
                lead,
                created=True,
                website_url=website,
            )
            # Zero-human agent — email welcome when consent holds (idempotent tag).
            try:
                from porterchain_api.collaboration_engine.lead_agent import (
                    run_lead_agent,
                )

                run_lead_agent(db, lead, trigger="ingest", website_url=website)
            except Exception:
                logger = __import__("logging").getLogger(__name__)
                logger.exception("lead_agent_ingest_failed lead=%s", lead.id)

        # Domain event for observability bus (publish after surrounding commit).
        if not event.quiet:
            try:
                from porterchain_api.platform.lead_events import (
                    LEAD_CREATED,
                    LEAD_MERGED,
                    emit_lead_event,
                )

                emit_lead_event(
                    db,
                    event_type=LEAD_CREATED if created else LEAD_MERGED,
                    lead_id=lead.id,
                    correlation_id=evt_id,
                    actor_type="system" if not _actor(event.actor) else "staff",
                    actor_id=_actor(event.actor),
                    payload={
                        "source": event.source,
                        "channel": channel,
                        "provider": event.provider,
                        "created": created,
                        "merged": merged,
                        "ingest_event_id": evt_id,
                        "priority": getattr(lead, "priority", None),
                        "company_name": getattr(lead, "company_name", None),
                        "lead_id": lead.id,
                    },
                )
            except Exception:
                # Never fail ingest on bus/audit issues.
                pass

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


__all__ = [
    "CanonicalLeadEvent",
    "IngestResult",
    "LeadIngestService",
    "normalize_email",
    "normalize_phone_e164",
]
