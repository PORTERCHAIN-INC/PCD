from pydantic import BaseModel, Field


class AuthMeResponse(BaseModel):
    user_id: str
    clerk_user_id: str | None = None
    user_type: str  # Deprecated hint for routing; prefer permissions / session-context
    roles: list[str]
    permissions: list[str]
    modules: list[str] = Field(default_factory=list)
    workspaces: list[dict] = Field(default_factory=list)
    # Deprecated: same as roles[0] / permissions — kept for older clients
    enterprise_role: str | None = Field(
        default=None,
        description="Deprecated. Use roles from SpiceDB session-context.",
    )
    enterprise_permissions: list[str] = Field(
        default_factory=list,
        description="Deprecated. Use permissions.",
    )
    org_id: str | None = None
    email: str | None = None
    phone: str | None = None
    role: str | None = None
    status: str | None = None
    profile: dict | None = None
    fleetbase_console_eligible: bool = False
    organization_ids: list[str] = Field(default_factory=list)


class SessionContextResponse(BaseModel):
    """Unified session context — permissions/workspaces from SpiceDB."""

    user_id: str
    status: str
    onboarding_status: str
    default_workspace: str | None = None
    email: str | None = None
    roles: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    modules: list[str] = Field(default_factory=list)
    organization_ids: list[str] = Field(default_factory=list)
    role_assignments: list[dict] = Field(default_factory=list)
    workspaces: list[dict] = Field(default_factory=list)
    legacy_profile_ids: dict[str, str] = Field(default_factory=dict)
    auth: dict = Field(default_factory=dict)


class FleetbaseSsoResponse(BaseModel):
    sso_token: str
    expires_in: int
    console_url: str
    fleetbase_user_uuid: str | None = None
    roles: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    fleetbase_session: dict | None = None


class PortalOnboardingStep(BaseModel):
    id: str
    label: str
    description: str
    complete: bool
    status: str
    missing: list[str] = Field(default_factory=list)


class PortalOnboardingResponse(BaseModel):
    ready: bool
    blockers: list[str]
    status: str
    clerk_linked: bool
    steps: list[PortalOnboardingStep]
    pending_documents: int = 0
    can_access_portal: bool
    company_name: str | None = None
    merchant_id: str | None = None
    vertical: str | None = None
    vertical_label: str | None = None
    vertical_options: list[dict[str, str]] = Field(default_factory=list)


class MerchantVerticalRequest(BaseModel):
    vertical: str = Field(..., description="construction | medical | food-beverage | wholesale")
