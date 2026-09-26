"""Normalize Meta / WhatsApp / Google lead webhook payloads → CanonicalLeadEvent.

Adapters stay pure: no DB. LeadIngestService owns identity + persistence.
"""

from __future__ import annotations

import hashlib
import hmac
import uuid
from typing import Any

from porterchain_api.collaboration_engine.lead_ingest_service import CanonicalLeadEvent
from porterchain_api.domain.crm_states import (
    LeadIdentityKind,
    LeadIntentType,
    LeadPriority,
    LeadSourceChannel,
    LeadStatus,
)


def verify_meta_signature(*, app_secret: str, raw_body: bytes, signature_header: str | None) -> bool:
    """X-Hub-Signature-256: sha256=<hex>."""
    if not app_secret or not signature_header:
        return False
    prefix = "sha256="
    if not signature_header.startswith(prefix):
        return False
    expected = hmac.new(app_secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header[len(prefix) :])


def _field_map(field_data: list[dict[str, Any]] | None) -> dict[str, str]:
    out: dict[str, str] = {}
    for row in field_data or []:
        name = str(row.get("name") or "").strip().lower()
        values = row.get("values") or []
        if name and values:
            out[name] = str(values[0]).strip()
    return out


def events_from_meta_payload(payload: dict[str, Any]) -> list[CanonicalLeadEvent]:
    """Graph webhook: leadgen + messaging (WhatsApp / IG / Page)."""
    events: list[CanonicalLeadEvent] = []
    obj = str(payload.get("object") or "")

    for entry in payload.get("entry") or []:
        for change in entry.get("changes") or []:
            field = str(change.get("field") or "")
            value = change.get("value") or {}
            if field == "leadgen":
                events.append(_meta_leadgen_event(value, entry_id=str(entry.get("id") or "")))
            elif field in ("messages",) and obj in ("whatsapp_business_account", "page", "instagram"):
                events.extend(_messaging_events(value, object_type=obj))

        # WhatsApp Cloud API often puts messages under entry.changes already;
        # also support entry.messaging (Messenger-style).
        for msg in entry.get("messaging") or []:
            events.extend(_messenger_style(msg))

    return [e for e in events if e.company_name or e.email or e.phone]


def _meta_leadgen_event(value: dict[str, Any], *, entry_id: str) -> CanonicalLeadEvent:
    lead_id = str(value.get("leadgen_id") or value.get("id") or uuid.uuid4())
    fields = _field_map(value.get("field_data"))
    email = fields.get("email")
    phone = fields.get("phone_number") or fields.get("phone")
    name = fields.get("full_name") or fields.get("first_name") or ""
    if fields.get("last_name") and "full_name" not in fields:
        name = f"{name} {fields['last_name']}".strip()
    company = fields.get("company_name") or fields.get("company") or name or email or "Meta lead"
    form_id = str(value.get("form_id") or "")
    page_id = str(value.get("page_id") or entry_id)
    channel = LeadSourceChannel.FACEBOOK.value
    source = "facebook"
    # Instagram lead ads still use leadgen; tag when adgroup hints IG.
    ad_name = str(value.get("ad_name") or "").lower()
    if "instagram" in ad_name or "ig_" in ad_name:
        channel = LeadSourceChannel.INSTAGRAM.value
        source = "instagram"

    return CanonicalLeadEvent(
        channel=channel,
        source=source,
        provider="meta_leadgen",
        external_event_id=f"meta_lead:{lead_id}",
        company_name=str(company)[:255],
        primary_contact_name=name or None,
        email=email,
        phone=phone,
        intent_type=LeadIntentType.MERCHANT.value,
        priority=LeadPriority.HIGH.value,
        status=LeadStatus.NEW.value,
        message=fields.get("message") or fields.get("work_email") or None,
        tags=["meta", "leadgen", source],
        custom_fields={
            "meta_form_id": form_id,
            "meta_page_id": page_id,
            "meta_ad_id": value.get("ad_id"),
            "meta_field_data": fields,
        },
        attribution={"meta_lead_id": lead_id, "fbclid": value.get("ad_id")},
        external_ids={LeadIdentityKind.META_LEAD_ID.value: lead_id},
        seed_conversation=bool(fields.get("message")),
    )


def _messaging_events(value: dict[str, Any], *, object_type: str) -> list[CanonicalLeadEvent]:
    events: list[CanonicalLeadEvent] = []
    contacts = {c.get("wa_id"): c for c in (value.get("contacts") or []) if c.get("wa_id")}
    for msg in value.get("messages") or []:
        wa_id = str(msg.get("from") or "")
        contact = contacts.get(wa_id) or {}
        profile = (contact.get("profile") or {}) if isinstance(contact, dict) else {}
        name = str(profile.get("name") or wa_id or "WhatsApp contact")
        body = ""
        if msg.get("type") == "text":
            body = str((msg.get("text") or {}).get("body") or "")
        elif msg.get("type") == "button":
            body = str((msg.get("button") or {}).get("text") or "")
        mid = str(msg.get("id") or uuid.uuid4())
        channel = (
            LeadSourceChannel.WHATSAPP.value
            if object_type == "whatsapp_business_account"
            else LeadSourceChannel.INSTAGRAM.value
            if object_type == "instagram"
            else LeadSourceChannel.FACEBOOK.value
        )
        source = channel
        ext: dict[str, str] = {}
        if channel == LeadSourceChannel.WHATSAPP.value and wa_id:
            ext[LeadIdentityKind.WHATSAPP_WA_ID.value] = wa_id
        events.append(
            CanonicalLeadEvent(
                channel=channel,
                source=source,
                provider=f"meta_messaging_{object_type}",
                external_event_id=f"meta_msg:{mid}",
                company_name=name[:255],
                primary_contact_name=name,
                phone=wa_id if channel == LeadSourceChannel.WHATSAPP.value else None,
                intent_type=LeadIntentType.MERCHANT.value,
                priority=LeadPriority.HIGH.value,
                message=body or None,
                tags=["meta", "dm", source],
                custom_fields={"meta_message_type": msg.get("type"), "wa_id": wa_id},
                external_ids=ext,
                seed_conversation=True,
            )
        )
    return events


def _messenger_style(msg: dict[str, Any]) -> list[CanonicalLeadEvent]:
    sender = (msg.get("sender") or {}).get("id")
    text = ((msg.get("message") or {}).get("text")) or ""
    mid = str((msg.get("message") or {}).get("mid") or uuid.uuid4())
    if not sender and not text:
        return []
    name = str(sender or "Messenger contact")
    return [
        CanonicalLeadEvent(
            channel=LeadSourceChannel.FACEBOOK.value,
            source="facebook",
            provider="meta_messenger",
            external_event_id=f"meta_msgr:{mid}",
            company_name=name[:255],
            primary_contact_name=name,
            intent_type=LeadIntentType.MERCHANT.value,
            priority=LeadPriority.MEDIUM.value,
            message=str(text) or None,
            tags=["meta", "messenger"],
            custom_fields={"psid": sender},
            seed_conversation=bool(text),
        )
    ]


def event_from_google_lead(payload: dict[str, Any]) -> CanonicalLeadEvent:
    """Google Ads lead form / GBP message — normalized JSON envelope."""
    channel_raw = str(payload.get("channel") or "google_ads").strip().lower()
    if channel_raw in ("gbp", "google_business_profile", "google_business"):
        channel = LeadSourceChannel.GOOGLE_BUSINESS_PROFILE.value
        source = "google_business_profile"
    else:
        channel = LeadSourceChannel.GOOGLE_ADS.value
        source = "google_ads"

    email = (payload.get("email") or "").strip() or None
    phone = (payload.get("phone") or "").strip() or None
    name = (payload.get("name") or payload.get("full_name") or "").strip()
    company = (payload.get("company_name") or payload.get("business_name") or name or email or "Google lead")
    external_id = str(payload.get("lead_id") or payload.get("gclid") or uuid.uuid4())
    ext: dict[str, str] = {}
    if payload.get("conversation_id"):
        ext[LeadIdentityKind.GBP_CONVERSATION_ID.value] = str(payload["conversation_id"])

    return CanonicalLeadEvent(
        channel=channel,
        source=source,
        provider="google_lead",
        external_event_id=f"google:{external_id}",
        company_name=str(company)[:255],
        primary_contact_name=name or None,
        email=email,
        phone=phone,
        intent_type=LeadIntentType.MERCHANT.value,
        priority=LeadPriority.HIGH.value,
        message=(payload.get("message") or payload.get("user_column_data_summary") or None),
        tags=["google", source],
        custom_fields={
            k: v
            for k, v in {
                "gclid": payload.get("gclid"),
                "form_id": payload.get("form_id"),
                "campaign_id": payload.get("campaign_id"),
                "raw_columns": payload.get("user_column_data"),
            }.items()
            if v
        },
        attribution={
            k: v
            for k, v in {
                "gclid": payload.get("gclid"),
                "utm_source": payload.get("utm_source") or "google",
                "utm_campaign": payload.get("utm_campaign"),
            }.items()
            if v
        },
        external_ids=ext,
        seed_conversation=bool(payload.get("message")),
    )


def event_from_referral(
    *,
    company_name: str,
    email: str | None,
    phone: str | None,
    contact_name: str | None,
    referred_by_merchant_id: str,
    notes: str | None,
) -> CanonicalLeadEvent:
    from porterchain_api.collaboration_engine.lead_consent import casl_evidence

    return CanonicalLeadEvent(
        channel=LeadSourceChannel.MERCHANT_REFERRAL.value,
        source="merchant_referral",
        provider="merchant_referral",
        external_event_id=f"referral:{referred_by_merchant_id}:{email or phone or uuid.uuid4()}",
        company_name=company_name[:255],
        primary_contact_name=contact_name,
        email=email,
        phone=phone,
        intent_type=LeadIntentType.MERCHANT.value,
        priority=LeadPriority.HIGH.value,
        message=notes,
        tags=["referral", "network"],
        referred_by_merchant_id=referred_by_merchant_id,
        custom_fields={"referred_by_merchant_id": referred_by_merchant_id},
        consent=casl_evidence(
            {"marketing": False},
            source="merchant_referral",
            actor="staff",
            legal_basis="legitimate_interest",
            force_marketing=False,
        ),
        seed_conversation=bool(notes),
    )


def event_from_linkedin_lead(payload: dict[str, Any]) -> CanonicalLeadEvent:
    """LinkedIn Lead Gen Forms — normalized JSON (Zapier/partner or direct)."""
    email = (payload.get("email") or payload.get("emailAddress") or "").strip() or None
    phone = (payload.get("phone") or payload.get("phoneNumber") or "").strip() or None
    name = (
        payload.get("fullName")
        or " ".join(
            p
            for p in [payload.get("firstName"), payload.get("lastName")]
            if p
        ).strip()
        or ""
    )
    company = (
        payload.get("companyName")
        or payload.get("company")
        or payload.get("company_name")
        or name
        or email
        or "LinkedIn lead"
    )
    external_id = str(
        payload.get("id") or payload.get("leadId") or payload.get("formResponseId") or uuid.uuid4()
    )
    urn = str(payload.get("linkedin_urn") or payload.get("personUrn") or "").strip()
    ext: dict[str, str] = {}
    if urn:
        ext[LeadIdentityKind.LINKEDIN_URN.value] = urn.lower()
    return CanonicalLeadEvent(
        channel=LeadSourceChannel.LINKEDIN.value,
        source="linkedin",
        provider="linkedin_leadgen",
        external_event_id=f"linkedin:{external_id}",
        company_name=str(company)[:255],
        primary_contact_name=name or None,
        email=email,
        phone=phone,
        intent_type=LeadIntentType.MERCHANT.value,
        priority=LeadPriority.HIGH.value,
        message=(payload.get("message") or payload.get("notes") or None),
        tags=["linkedin", "leadgen"],
        custom_fields={
            k: v
            for k, v in {
                "form_id": payload.get("formId") or payload.get("form_id"),
                "campaign_id": payload.get("campaignId"),
            }.items()
            if v
        },
        attribution={"utm_source": "linkedin", "linkedin_lead_id": external_id},
        external_ids=ext,
        seed_conversation=bool(payload.get("message")),
    )


def event_from_x_lead(payload: dict[str, Any]) -> CanonicalLeadEvent:
    """X/Twitter lead card or DM capture — normalized JSON."""
    email = (payload.get("email") or "").strip() or None
    phone = (payload.get("phone") or "").strip() or None
    handle = (payload.get("username") or payload.get("screen_name") or "").strip()
    name = (payload.get("name") or handle or email or "X lead").strip()
    company = payload.get("company_name") or payload.get("company") or name
    external_id = str(payload.get("id") or payload.get("lead_id") or uuid.uuid4())
    return CanonicalLeadEvent(
        channel=LeadSourceChannel.TWITTER.value,
        source="twitter",
        provider="x_lead",
        external_event_id=f"x:{external_id}",
        company_name=str(company)[:255],
        primary_contact_name=name,
        email=email,
        phone=phone,
        intent_type=LeadIntentType.MERCHANT.value,
        priority=LeadPriority.MEDIUM.value,
        message=(payload.get("message") or payload.get("text") or None),
        tags=["twitter", "x"],
        custom_fields={"username": handle} if handle else {},
        attribution={"utm_source": "twitter", "x_lead_id": external_id},
        seed_conversation=bool(payload.get("message") or payload.get("text")),
    )


def event_from_youtube_lead(payload: dict[str, Any]) -> CanonicalLeadEvent:
    """YouTube form / UTM capture / moderated comment promote."""
    email = (payload.get("email") or "").strip() or None
    phone = (payload.get("phone") or "").strip() or None
    name = (payload.get("name") or email or "YouTube lead").strip()
    company = payload.get("company_name") or payload.get("company") or name
    external_id = str(payload.get("id") or payload.get("comment_id") or uuid.uuid4())
    return CanonicalLeadEvent(
        channel=LeadSourceChannel.YOUTUBE.value,
        source="youtube",
        provider="youtube_lead",
        external_event_id=f"youtube:{external_id}",
        company_name=str(company)[:255],
        primary_contact_name=name,
        email=email,
        phone=phone,
        intent_type=LeadIntentType.MERCHANT.value,
        priority=LeadPriority.MEDIUM.value,
        message=(payload.get("message") or payload.get("comment") or None),
        tags=["youtube"],
        custom_fields={
            k: v
            for k, v in {
                "video_id": payload.get("video_id"),
                "comment_id": payload.get("comment_id"),
            }.items()
            if v
        },
        attribution={
            k: v
            for k, v in {
                "utm_source": payload.get("utm_source") or "youtube",
                "utm_campaign": payload.get("utm_campaign"),
                "utm_content": payload.get("utm_content"),
            }.items()
            if v
        },
        seed_conversation=bool(payload.get("message") or payload.get("comment")),
    )


__all__ = [
    "event_from_google_lead",
    "event_from_linkedin_lead",
    "event_from_referral",
    "event_from_x_lead",
    "event_from_youtube_lead",
    "events_from_meta_payload",
    "verify_meta_signature",
]
