
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


class QuietHoursUpdateRequest(BaseModel):
    quiet_hours_enabled: bool | None = None
    quiet_start_hour: int | None = Field(default=None, ge=0, le=23)
    quiet_end_hour: int | None = Field(default=None, ge=0, le=23)
    timezone: str | None = Field(default=None, max_length=64)


class BroadcastRequest(BaseModel):
    recipient_type: str
    recipient_id: str
    title: str
    body: str
    channel: str = "in_app"


class SendTestRequest(BaseModel):
    template_key: str = Field(min_length=1, max_length=64)
    channel: str = Field(default="email", max_length=16)
    recipient_address: str | None = Field(default=None, max_length=512)
    recipient_type: str = Field(default="admin", max_length=32)
    recipient_id: str | None = Field(default=None, max_length=36)
