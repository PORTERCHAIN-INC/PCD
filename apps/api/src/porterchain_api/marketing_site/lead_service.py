"""Calculator lead capture -> existing CRM lead pipeline (LeadIngestService).

* Honeypot / too-fast submissions get the same 202 as real ones and create nothing.
* CASL: marketing consent is its own unchecked box; the evidence bag records it.
* Calculator leads never trigger the automatic welcome email or nurture
  (`skip_outreach`), so no outbound email is sent from this path.
"""

from __future__ import annotations

import logging
import re
import uuid
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.collaboration_engine.lead_consent import casl_evidence
from porterchain_api.collaboration_engine.lead_ingest_service import (
    CanonicalLeadEvent,
    LeadIngestService,
)
from porterchain_api.domain.crm_states import (
    LeadIntentType,
    LeadPriority,
    LeadSourceChannel,
    LeadStatus,
)
from porterchain_api.marketing_site.schemas import (
    CALCULATOR_VEHICLES,
    INDUSTRIES,
    MONTHLY_VOLUMES,
    CalculatorLeadRequest,
)

logger = logging.getLogger(__name__)

SOURCE = "website_calculator"
PROVIDER = "website_calculator"
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")
_PHONE_DIGITS = re.compile(r"\d")
_FSA = re.compile(r"^[A-Z]\d[A-Z]$")
_UTM_KEYS = ("utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content")

_ingest = LeadIngestService()


def is_probably_bot(body: CalculatorLeadRequest, *, min_fill_seconds: int) -> bool:
    if (body.website or "").strip():
        return True
    if body.form_elapsed_ms is not None and body.form_elapsed_ms < min_fill_seconds * 1000:
        return True
    return False


def _fsa(value: str | None) -> str | None:
    code = (value or "").strip().upper().replace(" ", "")[:3]
    return code if _FSA.match(code) else None


def validate_lead(body: CalculatorLeadRequest) -> dict[str, Any]:
    """Return cleaned values or raise ValueError('<field>_invalid')."""
    email = body.email.strip().lower()
    if not _EMAIL.match(email):
        raise ValueError("email_invalid")
    phone = body.phone.strip()
    if len(_PHONE_DIGITS.findall(phone)) < 10:
        raise ValueError("phone_invalid")
    business = body.business_name.strip()
    if not business:
        raise ValueError("business_name_invalid")
    industry = body.industry.strip().lower()
    if industry not in INDUSTRIES:
        raise ValueError("industry_invalid")
    volume = body.monthly_volume.strip()
    if volume not in MONTHLY_VOLUMES:
        raise ValueError("monthly_volume_invalid")
    vehicle = (body.vehicle_class or "").strip().lower() or None
    if vehicle and vehicle not in CALCULATOR_VEHICLES:
        vehicle = None
    return {
        "email": email,
        "phone": phone,
        "business": business,
        "industry": industry,
        "volume": volume,
        "vehicle": vehicle,
        "pickup_fsa": _fsa(body.pickup_fsa),
        "dropoff_fsa": _fsa(body.dropoff_fsa),
    }


def submit_calculator_lead(
    db: Session, body: CalculatorLeadRequest, *, min_fill_seconds: int = 2, auto_outreach: bool = False
) -> dict[str, Any]:
    if is_probably_bot(body, min_fill_seconds=min_fill_seconds):
        logger.info("calculator lead dropped (spam signal)")
        return {"status": "received", "created": False, "spam": True}
    clean = validate_lead(body)
    attribution = {k: getattr(body, k).strip() for k in _UTM_KEYS if (getattr(body, k) or "").strip()}
    custom_fields = {
        k: v
        for k, v in {
            "form": "calculator",
            "industry": clean["industry"],
            "monthly_volume": clean["volume"],
            "pickup_fsa": clean["pickup_fsa"],
            "dropoff_fsa": clean["dropoff_fsa"],
            "vehicle_class": clean["vehicle"],
            "estimate_cents": body.estimate_cents,
            "landing_page": (body.landing_page or "").strip() or None,
            "referrer": (body.referrer or "").strip() or None,
            "source_page": (body.source_page or "").strip() or None,
            "hero_variant": (body.hero_variant or "").strip() or None,
            "visitor_id": (body.visitor_id or "").strip() or None,
            "phone_full": clean["phone"],
        }.items()
        if v not in (None, "")
    }
    consent = casl_evidence(
        {"marketing": bool(body.marketing_consent)},
        source=SOURCE,
        actor="lead",
        force_marketing=bool(body.marketing_consent),
    )
    external_ids = {"visitor_session": custom_fields["visitor_id"]} if custom_fields.get("visitor_id") else {}
    result = _ingest.ingest(
        db,
        CanonicalLeadEvent(
            channel=LeadSourceChannel.WEBSITE.value,
            source=SOURCE,
            provider=PROVIDER,
            external_event_id=f"calc:{clean['email']}:{uuid.uuid4()}",
            company_name=clean["business"],
            primary_contact_name=None,
            email=clean["email"],
            phone=clean["phone"],
            intent_type=LeadIntentType.MERCHANT.value,
            priority=LeadPriority.MEDIUM.value,
            status=LeadStatus.NEW.value,
            tags=["calculator", clean["industry"]],
            custom_fields=custom_fields,
            consent=consent,
            attribution=attribution,
            external_ids=external_ids,
            seed_conversation=False,
            skip_outreach=not auto_outreach,
        ),
    )
    lead = result.lead
    # First-class CRM columns so the leads workspace can filter on them.
    if not lead.industry:
        lead.industry = clean["industry"]
    if not lead.estimated_deliveries_per_month:
        lead.estimated_deliveries_per_month = MONTHLY_VOLUMES[clean["volume"]]
    if clean["vehicle"] and not lead.preferred_vehicle:
        lead.preferred_vehicle = clean["vehicle"]
    if clean["pickup_fsa"] and not lead.service_area:
        lead.service_area = clean["pickup_fsa"]
    db.commit()
    return {"status": "received", "created": result.created, "lead_id": lead.id}
