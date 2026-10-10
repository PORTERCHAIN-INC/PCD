"""CRM domain states for the Porterchain Merchant CRM.

These power the logistics merchant acquisition pipeline: every business
inquiry becomes a lead, then a company + deal, and finally an active merchant.
"""

from enum import StrEnum


class LeadStatus(StrEnum):
    """Five-stage pipeline: New → Replied → Quoted → Won / Lost.

    ``archived`` is a visibility flag (hidden from the inbox), not a stage.
    The pre-2026-10 names stay as enum *aliases* so existing callers keep
    working; the stored value is always one of the five stages.
    """

    NEW = "new"
    REPLIED = "replied"
    QUOTED = "quoted"
    WON = "won"
    LOST = "lost"
    ARCHIVED = "archived"
    # Legacy aliases (same value → same member).
    CONTACTED = "replied"
    QUALIFIED = "replied"
    NURTURING = "replied"
    CONVERTED = "won"
    UNQUALIFIED = "lost"


# Old stored value → new stage (migration lp0leadpipe1a2b + API back-compat).
LEGACY_LEAD_STATUS: dict[str, str] = {
    "contacted": "replied",
    "qualified": "replied",
    "nurturing": "replied",
    "converted": "won",
    "unqualified": "lost",
}

PIPELINE_STATUSES: tuple[str, ...] = ("new", "replied", "quoted", "won", "lost")

LOST_REASONS: tuple[str, ...] = (
    "price",
    "timing",
    "no_response",
    "competitor",
    "out_of_area",
    "not_a_fit",
    "other",
)


def normalize_lead_status(value: str | None) -> str | None:
    """Accept old names from older clients; return the stored stage value."""
    if value is None:
        return None
    v = str(value).strip().lower()
    return LEGACY_LEAD_STATUS.get(v, v)


class LeadPriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class LeadSourceChannel(StrEnum):
    """Coarse channel for inbox filters (Jeff Dean fan-in taxonomy)."""

    WEBSITE = "website"
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    LINKEDIN = "linkedin"
    TWITTER = "twitter"
    YOUTUBE = "youtube"
    WHATSAPP = "whatsapp"
    GOOGLE_ADS = "google_ads"
    GOOGLE_BUSINESS_PROFILE = "google_business_profile"
    MERCHANT_REFERRAL = "merchant_referral"
    PHONE_CALL = "phone_call"
    SMS = "sms"
    MANUAL = "manual"
    CAPACITY_GUIDE = "capacity_guide"
    WEBSITE_BOOKING = "website_booking"
    EMAIL = "email"
    APP_INSTALL = "app_install"  # Shopify app store installs
    MERCHANT_SIGNUP = "merchant_signup"
    DRIVER_SIGNUP = "driver_signup"
    OTHER = "other"


class LeadIntentType(StrEnum):
    """Conversion branch on the same lead spine (founder lock 1=B)."""

    MERCHANT = "merchant"
    RETAIL_CUSTOMER = "retail_customer"
    DRIVER_PARTNER = "driver_partner"
    UNKNOWN = "unknown"


class LeadDecisionStatus(StrEnum):
    """Sales conversation state — orthogonal to LeadStatus funnel hygiene."""

    NEW = "new"
    RESEARCHING = "researching"
    QUESTIONS_OPEN = "questions_open"
    OBJECTION = "objection"
    READY_TO_CONVERT = "ready_to_convert"
    DEFERRED = "deferred"
    LOST = "lost"
    CONVERTED = "converted"


class LeadIdentityKind(StrEnum):
    EMAIL = "email"
    PHONE_E164 = "phone_e164"
    META_LEAD_ID = "meta_lead_id"
    WHATSAPP_WA_ID = "whatsapp_wa_id"
    LINKEDIN_URN = "linkedin_urn"
    GBP_CONVERSATION_ID = "gbp_conversation_id"
    VISITOR_SESSION = "visitor_session"
    REFERRAL_CODE = "referral_code"


# Fine source → coarse channel (adapters may override).
SOURCE_TO_CHANNEL: dict[str, str] = {
    "website": LeadSourceChannel.WEBSITE.value,
    "website_business": LeadSourceChannel.WEBSITE.value,
    "website_contact": LeadSourceChannel.WEBSITE.value,
    "website_quote": LeadSourceChannel.WEBSITE.value,
    "website_demo": LeadSourceChannel.WEBSITE.value,
    "website_newsletter": LeadSourceChannel.WEBSITE.value,
    "website_booking": LeadSourceChannel.WEBSITE_BOOKING.value,
    "website_driver_partner": LeadSourceChannel.WEBSITE.value,
    "website_capacity_guide": LeadSourceChannel.CAPACITY_GUIDE.value,
    "instagram": LeadSourceChannel.INSTAGRAM.value,
    "facebook": LeadSourceChannel.FACEBOOK.value,
    "linkedin": LeadSourceChannel.LINKEDIN.value,
    "twitter": LeadSourceChannel.TWITTER.value,
    "youtube": LeadSourceChannel.YOUTUBE.value,
    "whatsapp": LeadSourceChannel.WHATSAPP.value,
    "google_ads": LeadSourceChannel.GOOGLE_ADS.value,
    "google_business_profile": LeadSourceChannel.GOOGLE_BUSINESS_PROFILE.value,
    "merchant_referral": LeadSourceChannel.MERCHANT_REFERRAL.value,
    "phone_call": LeadSourceChannel.PHONE_CALL.value,
    "sms": LeadSourceChannel.SMS.value,
    "manual": LeadSourceChannel.MANUAL.value,
    "vendor_import": LeadSourceChannel.MANUAL.value,
    "crm_import": LeadSourceChannel.MANUAL.value,
    "capacity_guide": LeadSourceChannel.CAPACITY_GUIDE.value,
}


def channel_for_source(source: str | None) -> str:
    if not source:
        return LeadSourceChannel.OTHER.value
    key = source.strip().lower()
    if key in SOURCE_TO_CHANNEL:
        return SOURCE_TO_CHANNEL[key]
    if key.startswith("website_"):
        return LeadSourceChannel.WEBSITE.value
    return LeadSourceChannel.OTHER.value


class CompanyMerchantStatus(StrEnum):
    LEAD = "lead"
    PROSPECT = "prospect"
    NEGOTIATING = "negotiating"
    ACTIVE_MERCHANT = "active_merchant"
    CHURNED = "churned"


class DealStage(StrEnum):
    PROSPECTING = "prospecting"
    QUALIFIED = "qualified"
    MEETING_SCHEDULED = "meeting_scheduled"
    QUOTE_SENT = "quote_sent"
    NEGOTIATION = "negotiation"
    CONTRACT_REVIEW = "contract_review"
    WON = "won"
    LOST = "lost"
    HOLD = "hold"


# Ordered pipeline columns for the Kanban board.
PIPELINE_STAGES: list[str] = [
    DealStage.PROSPECTING.value,
    DealStage.QUALIFIED.value,
    DealStage.MEETING_SCHEDULED.value,
    DealStage.QUOTE_SENT.value,
    DealStage.NEGOTIATION.value,
    DealStage.CONTRACT_REVIEW.value,
    DealStage.WON.value,
    DealStage.LOST.value,
]

# Default win-probability suggestion per stage (percent).
STAGE_PROBABILITY: dict[str, int] = {
    DealStage.PROSPECTING.value: 10,
    DealStage.QUALIFIED.value: 25,
    DealStage.MEETING_SCHEDULED.value: 40,
    DealStage.QUOTE_SENT.value: 60,
    DealStage.NEGOTIATION.value: 75,
    DealStage.CONTRACT_REVIEW.value: 90,
    DealStage.WON.value: 100,
    DealStage.LOST.value: 0,
    DealStage.HOLD.value: 20,
}


class QuotationStatus(StrEnum):
    DRAFT = "draft"
    SENT = "sent"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CONVERTED = "converted"


class ContractStatus(StrEnum):
    DRAFT = "draft"
    PENDING_SIGNATURE = "pending_signature"
    ACTIVE = "active"
    EXPIRED = "expired"
    RENEWED = "renewed"
    TERMINATED = "terminated"


class TaskType(StrEnum):
    CALL = "call"
    EMAIL = "email"
    MEETING = "meeting"
    FOLLOW_UP = "follow_up"
    DOCUMENT = "document"
    CONTRACT_REVIEW = "contract_review"
    MERCHANT_VISIT = "merchant_visit"
    DEMO = "demo"
    TODO = "todo"


class TaskStatus(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CANCELLED = "cancelled"
