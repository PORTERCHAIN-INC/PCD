"""Public (unauthenticated) website ingest schemas."""

from datetime import datetime

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


class PublicInquiryResponse(BaseModel):
    id: str
    status: str = "accepted"


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
    created_at: datetime
    updated_at: datetime


class PublicBlogPostItem(PublicBlogPostMeta):
    body_md: str = ""
