"""Lead ingest identity resolve / merge / seed helpers (not a *_service)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy.orm import Session

from porterchain_api.collaboration_engine.crm_leads import CrmLeadsMixin
from porterchain_api.crm_models import (
    CrmConversation,
    CrmConversationMessage,
    CrmLead,
    CrmLeadIdentity,
)
from porterchain_api.domain.crm_states import (
    LeadIdentityKind,
    LeadIntentType,
    LeadPriority,
)

if TYPE_CHECKING:
    from porterchain_api.collaboration_engine.lead_ingest_service import CanonicalLeadEvent


class LeadIngestResolveMixin:
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
        if priority in (LeadPriority.HIGH.value, LeadPriority.URGENT.value) and (
            lead.status in (None, "", "new", "archived")
        ):
            # Don't override a priority staff set on a lead they're already working.
            if lead.priority not in (LeadPriority.URGENT.value,):
                lead.priority = priority
        merged_custom = dict(lead.custom_fields or {})
        merged_custom.update({k: v for k, v in custom_fields.items() if v is not None})
        lead.custom_fields = merged_custom
        if consent:
            from porterchain_api.collaboration_engine.lead_suppression import merge_consent_safe

            lead.consent = merge_consent_safe(
                lead.consent if isinstance(lead.consent, dict) else {},
                consent,
                db=db,
                email=lead.email or email,
                phone=lead.phone or phone,
            )
        if referred_by_merchant_id and not lead.referred_by_merchant_id:
            lead.referred_by_merchant_id = referred_by_merchant_id
        if notes:
            prev = (lead.internal_notes or "").strip()
            note = notes.strip()
            if note and note not in prev:
                lead.internal_notes = f"{prev}\n{note}".strip() if prev else note
        lead.lead_score = CrmLeadsMixin.score_lead(lead, db=db)

    def _stamp_visitor_spine(self, lead: CrmLead, event: CanonicalLeadEvent) -> None:
        """Promote visitor / draft ids from event onto first-class CrmLead columns."""
        vid: str | None = None
        for key in ("visitor_session", "visitor_id"):
            raw = (event.external_ids or {}).get(key)
            if isinstance(raw, str) and raw.strip():
                vid = raw.strip()[:64]
                break
        if not vid:
            fields = event.custom_fields or {}
            for key in ("visitor_id", "session_id"):
                raw = fields.get(key)
                if isinstance(raw, str) and raw.strip():
                    vid = raw.strip()[:64]
                    break
        if vid:
            if not lead.visitor_session_id:
                lead.visitor_session_id = vid
            cf = dict(lead.custom_fields or {})
            cf.setdefault("visitor_id", vid)
            lead.custom_fields = cf

        draft_id = (event.custom_fields or {}).get("booking_draft_id")
        if isinstance(draft_id, str) and draft_id.strip() and not lead.booking_draft_id:
            lead.booking_draft_id = draft_id.strip()[:36]

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
        self,
        db: Session,
        lead: CrmLead,
        *,
        channel: str,
        body: str,
        external_message_id: str | None = None,
        metadata: dict[str, Any] | None = None,
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
                channel=channel,
                external_message_id=(external_message_id or None),
                metadata_json={"seed": True, **(metadata or {})},
            )
        )
        from porterchain_api.collaboration_engine.lead_pipeline import apply_triage

        apply_triage(lead, text)


