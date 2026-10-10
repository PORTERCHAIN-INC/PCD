"""Public (unauthenticated) website ingest schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class PublicInquiryCreate(BaseModel):
    """Website contact / business inquiry payload."""

    email: str = Field(min_length=3, max_length=320)
    name: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=64)
    business_name: str | None = Field(default=None, max_length=255)
    message: str | None = Field(default=None, max_length=8000)
    intent: str | None = Field(default=None, max_length=64)
    inquiry_type: str | None = Field(default=None, max_length=64)
    source: str = Field(default="website", max_length=64)
    source_page: str | None = Field(default=None, max_length=512)
    form: str | None = Field(default=None, max_length=64)
    utm_source: str | None = Field(default=None, max_length=128)
    utm_campaign: str | None = Field(default=None, max_length=128)
    utm_medium: str | None = Field(default=None, max_length=128)
    referred_by_merchant_id: str | None = Field(default=None, max_length=64)
    # pc_vid from website visitor-tracking — stamps CrmLead.visitor_session_id.
    visitor_id: str | None = Field(default=None, max_length=128)
    # Legacy consent snapshot. CMP (cookie banner) values are ignored for email.
    consent: dict[str, Any] | None = None
    # Explicit, unchecked-by-default CASL marketing checkbox on the form.
    marketing_consent: bool | None = None
    # Required "contact me about this request" box (vehicle-partner form).
    contact_consent: bool | None = None
    locale: str | None = Field(default=None, max_length=8)
    utm_term: str | None = Field(default=None, max_length=128)
    utm_content: str | None = Field(default=None, max_length=128)
    # Spam guard (same as the calculator): honeypot + time-to-fill.
    website: str | None = Field(default=None, max_length=200)
    form_elapsed_ms: int | None = Field(default=None, ge=0)


class NewsletterSubscribeRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    source_page: str | None = Field(default=None, max_length=512)
    locale: str | None = Field(default=None, max_length=8)
    utm_source: str | None = Field(default=None, max_length=128)
    utm_medium: str | None = Field(default=None, max_length=128)
    utm_campaign: str | None = Field(default=None, max_length=128)
    website: str | None = Field(default=None, max_length=200)
    form_elapsed_ms: int | None = Field(default=None, ge=0)


class NewsletterSubscribeResponse(BaseModel):
    status: str = "pending_confirmation"


class NewsletterConfirmRequest(BaseModel):
    token: str = Field(min_length=16, max_length=256)


class NewsletterConfirmResponse(BaseModel):
    status: str


class PublicInquiryResponse(BaseModel):
    id: str
    status: str = "accepted"


# --- Capacity guide (welcome agent) ---


class PublicGuideLeadCreate(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    name: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=64)
    business_name: str | None = Field(default=None, max_length=255)
    intent: str | None = Field(default=None, max_length=64)
    session_id: str | None = Field(default=None, max_length=128)
    visitor_id: str | None = Field(default=None, max_length=128)
    source_page: str | None = Field(default=None, max_length=512)
    notes: str | None = Field(default=None, max_length=4000)
    marketing_consent: bool | None = None
    locale: str | None = Field(default=None, max_length=8)
    website: str | None = Field(default=None, max_length=200)
    form_elapsed_ms: int | None = Field(default=None, ge=0)
    utm_source: str | None = Field(default=None, max_length=128)
    utm_campaign: str | None = Field(default=None, max_length=128)
    utm_medium: str | None = Field(default=None, max_length=128)
    guide_stage: str | None = Field(default=None, max_length=32)
    referred_by_merchant_id: str | None = Field(default=None, max_length=64)
    consent: dict[str, Any] | None = None


class PublicGuideLeadResponse(BaseModel):
    id: str
    created: bool
    status: str
    email: str
    phone: str | None = None


class PublicGuideTranscriptTurn(BaseModel):
    role: str = Field(max_length=32)
    content: str = Field(max_length=8000)


class PublicGuideTranscriptCreate(BaseModel):
    lead_id: str = Field(min_length=1, max_length=64)
    session_id: str | None = Field(default=None, max_length=128)
    turns: list[PublicGuideTranscriptTurn] = Field(default_factory=list, max_length=40)
    summary: str | None = Field(default=None, max_length=4000)


class PublicGuideTranscriptResponse(BaseModel):
    lead_id: str
    turn_count: int
    status: str = "saved"


class PublicGuideSlot(BaseModel):
    start: datetime
    end: datetime
    label: str
    meeting_type: str


class PublicGuideSlotsResponse(BaseModel):
    timezone: str
    meeting_type: str
    slots: list[PublicGuideSlot]


class PublicGuideAppointmentCreate(BaseModel):
    lead_id: str = Field(min_length=1, max_length=64)
    meeting_type: str = Field(default="call", max_length=32)  # call | meeting
    start: datetime
    session_id: str | None = Field(default=None, max_length=128)
    notes: str | None = Field(default=None, max_length=2000)


class PublicGuideAppointmentResponse(BaseModel):
    task_id: str
    lead_id: str
    meeting_type: str
    due_at: datetime
    title: str
    status: str = "booked"


class PublicBlogPostMeta(BaseModel):
    id: str
    slug: str
    locale: str
    title: str
    description: str
    category: str
    author_id: str
    status: str
    featured: bool = False
    trending: bool = False
    case_study: bool = False
    on_time_percent: str | None = None
    cost_delta_percent: str | None = None
    volume_metric: str | None = None
    tags: list[str] = Field(default_factory=list)
    cover_image_url: str | None = None
    published_at: str | None = None
    reading_minutes: int = 1
    created_at: datetime
    updated_at: datetime


class PublicBlogPostItem(PublicBlogPostMeta):
    body_md: str = ""


class PublicBlogAuthor(BaseModel):
    id: str
    name: str
    role: str = ""
    bio: str = ""


class SecurityAuditEvent(BaseModel):
    event_type: str
    app_kind: str = Field(pattern="^(customer|driver)$")
    occurred_at: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SecurityAuditBatch(BaseModel):
    events: list[SecurityAuditEvent] = Field(min_length=1, max_length=50)
