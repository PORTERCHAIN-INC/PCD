from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class DeviceRegisterRequest(BaseModel):
    fcm_token: str = Field(min_length=1, max_length=512)
    platform: str = Field(default="web", max_length=16)
    device_name: str | None = Field(default=None, max_length=128)
    app_version: str | None = None
    os_version: str | None = None
    language: str = "en-CA"
    timezone: str = "America/Toronto"
    notification_permission: str = "default"


class PreferenceUpdateRequest(BaseModel):
    category: str
    email_enabled: bool | None = None
    push_enabled: bool | None = None
    sms_enabled: bool | None = None
    in_app_enabled: bool | None = None


class BroadcastRequest(BaseModel):
    recipient_type: str
    recipient_id: str
    title: str
    body: str
    channel: str = "in_app"


class NotificationRecordOut(BaseModel):
    id: str
    event_type: str | None
    template_key: str
    category: str
    channel: str
    priority: str
    recipient_type: str
    recipient_id: str
    recipient_address: str | None
    title: str
    body: str
    status: str
    retry_count: int
    failure_reason: str | None
    search_tags: dict[str, Any]
    is_read: bool
    is_archived: bool
    deep_link: str | None = None
    queued_at: datetime | None
    sent_at: datetime | None
    delivered_at: datetime | None
    opened_at: datetime | None
    clicked_at: datetime | None
    created_at: datetime
