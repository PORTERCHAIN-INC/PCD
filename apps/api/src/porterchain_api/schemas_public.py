"""Public (unauthenticated) website ingest schemas."""

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
