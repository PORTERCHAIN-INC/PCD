from pydantic import BaseModel, Field


class AuthMeResponse(BaseModel):
    user_id: str
    clerk_user_id: str | None = None
    user_type: str
    roles: list[str]
    permissions: list[str]
    enterprise_role: str | None = None
    enterprise_permissions: list[str] = Field(default_factory=list)
    org_id: str | None = None
    email: str | None = None
    phone: str | None = None
    role: str | None = None
    status: str | None = None
    profile: dict | None = None
    fleetbase_console_eligible: bool = False


class RbacMatrixResponse(BaseModel):
    matrix: dict
    enterprise_role: str | None = None
    enterprise_permissions: list[str] = Field(default_factory=list)
    admin_modules: list[str] = Field(default_factory=list)
    merchant_modules: list[str] = Field(default_factory=list)


class MerchantAccessResponse(BaseModel):
    user_id: str
    merchant_id: str
    email: str
    merchant_role: str
    enterprise_role: str
    company_name: str
    is_active: bool = True


class FleetbaseSsoResponse(BaseModel):
    sso_token: str
    expires_in: int
    console_url: str
    fleetbase_user_uuid: str | None = None
    roles: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    fleetbase_session: dict | None = None


class CustomerAccessResponse(BaseModel):
    """Customer record — auto-provisioned on first authenticated portal access."""

    customer_id: str
    email: str | None = None
    clerk_user_id: str
    is_active: bool = True


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


class AdminAccessResponse(BaseModel):
    """Staff record — only provisioned admin_users may access the admin portal."""

    user_id: str
    email: str
    name: str | None = None
    role: str
    is_active: bool = True
