from pydantic import BaseModel, Field


class AuthMeResponse(BaseModel):
    user_id: str
    user_type: str
    roles: list[str]
    permissions: list[str]
    org_id: str | None = None
    email: str | None = None
    fleetbase_console_eligible: bool = False


class FleetbaseSsoResponse(BaseModel):
    sso_token: str
    expires_in: int
    console_url: str
    fleetbase_user_uuid: str | None = None
    roles: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    fleetbase_session: dict | None = None
