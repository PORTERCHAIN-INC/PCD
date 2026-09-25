"""Admin settings directory routes — users and staff IdP. Shared admin router."""

from typing import Annotated

from fastapi import Depends, Header, Query, Request
from sqlalchemy.orm import Session

from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db
from porterchain_api.routers.admin._deps import (
    AdminContext,
    PlatformUserAuthorizeRequest,
    PlatformUserAuthorizeResponse,
    PlatformUserCreateRequest,
    PlatformUserDeleteRequest,
    PlatformUserInviteRequest,
    PlatformUserUpdateRequest,
    PlatformUsersResponse,
    StaffEnrollResponse,
    StaffInviteRequest,
    StaffItem,
    StaffRoleUpdateRequest,
    _clerk_directory,
    _settings,
    get_admin_context,
    require_module,
    router,
)
from porterchain_api.routers.admin.settings import (
    _invoke,
    _reject_staff_clerk_route,
    _staff_idp,
    _staff_item,
    _step_up,
)

@router.get("/settings/staff", response_model=list[StaffItem])
def list_staff(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> list[StaffItem]:
    return _invoke(ctx, lambda: [_staff_item(u) for u in _settings.list_staff(db)])


@router.get("/settings/users/{user_type}", response_model=PlatformUsersResponse)
def list_platform_users(
    user_type: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    limit: int = Query(5000, ge=1, le=20000),
    search: str | None = Query(None, max_length=200),
    access_status: str | None = Query(None),
    invite_status: str | None = Query(None),
    identity_status: str | None = Query(None),
    account_status: str | None = Query(None),
    clerk_status: str | None = Query(None),
) -> PlatformUsersResponse:
    return _invoke(
        ctx,
        _settings.list_platform_users,
        db,
        settings,
        user_type,
        limit=limit,
        search=search,
        access_status=access_status,
        invite_status=invite_status,
        identity_status=identity_status,
        account_status=account_status,
        clerk_status=clerk_status,
    )


@router.post("/settings/users/{user_type}", status_code=201)
def create_platform_user(
    user_type: str,
    body: PlatformUserCreateRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    _reject_staff_clerk_route(user_type)
    return _invoke(
        ctx,
        _clerk_directory.create_user,
        db,
        ctx,
        settings,
        user_type,
        email=body.email,
        name=body.name,
        role=body.role,
        password=body.password,
        send_invite=body.send_invite,
        merchant_id=body.merchant_id,
        module="settings_identity",
    )


@router.patch("/settings/users/{user_type}/clerk")
def update_platform_clerk_user(
    user_type: str,
    body: PlatformUserUpdateRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    _reject_staff_clerk_route(user_type)
    return _invoke(
        ctx,
        _clerk_directory.update_clerk_user,
        db,
        ctx,
        settings,
        user_type,
        body.clerk_user_id,
        name=body.name,
        password=body.password,
        banned=body.banned,
        module="settings_identity",
    )


@router.post("/settings/users/{user_type}/delete", status_code=204)
def delete_platform_user(
    user_type: str,
    body: PlatformUserDeleteRequest,
    request: Request,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    _step_up(request, authorization, settings)
    return _invoke(
        ctx,
        _clerk_directory.delete_clerk_user,
        db,
        ctx,
        settings,
        user_type,
        clerk_user_id=body.clerk_user_id,
        platform_user_id=body.platform_user_id,
        module="settings_identity",
    )


@router.post("/settings/users/{user_type}/authorize", response_model=PlatformUserAuthorizeResponse)
def authorize_platform_user(
    user_type: str,
    body: PlatformUserAuthorizeRequest,
    request: Request,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    authorization: Annotated[str | None, Header()] = None,
) -> PlatformUserAuthorizeResponse:
    _step_up(request, authorization, settings)
    return _invoke(
        ctx,
        _settings.authorize_platform_user,
        db,
        ctx,
        settings,
        user_type,
        platform_user_id=body.platform_user_id,
        clerk_user_id=body.clerk_user_id,
        email=body.email,
        name=body.name,
        reason=body.reason,
        module="settings_identity",
    )


@router.post("/settings/users/{user_type}/invite")
def invite_platform_user(
    user_type: str,
    body: PlatformUserInviteRequest,
    request: Request,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    authorization: Annotated[str | None, Header()] = None,
) -> dict:
    """Re-send Clerk invite for driver/customer. Merchant seats bind on sign-in."""
    _reject_staff_clerk_route(user_type)
    _step_up(request, authorization, settings)
    return _invoke(
        ctx,
        _clerk_directory.invite_user,
        db,
        ctx,
        settings,
        user_type,
        platform_user_id=body.platform_user_id,
        module="settings_identity",
    )


@router.post("/settings/staff/enroll", response_model=StaffEnrollResponse, status_code=201)
def enroll_staff(
    body: StaffInviteRequest,
    request: Request,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    authorization: Annotated[str | None, Header()] = None,
) -> StaffEnrollResponse:
    """Provision AdminUser + staff IdP enrollment token (emails activate link).

    Requires a fresh step-up (login or passkey within 15 minutes).
    """
    _step_up(request, authorization, settings)
    result = _invoke(
        ctx,
        _staff_idp.enroll,
        db,
        ctx,
        settings,
        email=body.email,
        role=body.role,
        name=body.name,
        module="settings_identity",
    )
    return StaffEnrollResponse(**result)


@router.post("/settings/staff/{user_id}/enroll-reissue", response_model=StaffEnrollResponse, status_code=201)
def reissue_staff_enrollment(
    user_id: str,
    request: Request,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    authorization: Annotated[str | None, Header()] = None,
) -> StaffEnrollResponse:
    """Re-issue enrollment token for existing staff (lost link / expired session)."""
    _step_up(request, authorization, settings)
    result = _invoke(ctx, _staff_idp.reissue, db, ctx, settings, user_id, module="settings_identity")
    return StaffEnrollResponse(**result)


@router.post("/settings/staff/{user_id}/recover-device", response_model=StaffEnrollResponse, status_code=201)
def recover_staff_device(
    user_id: str,
    request: Request,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    authorization: Annotated[str | None, Header()] = None,
    reason: str | None = Query(None),
) -> StaffEnrollResponse:
    """Lost-device recovery — wipe passkeys, revoke sessions, email a fresh activate link."""
    _step_up(request, authorization, settings)
    result = _invoke(
        ctx,
        _staff_idp.recover_device,
        db,
        ctx,
        settings,
        user_id,
        reason=reason,
        module="settings_identity",
    )
    return StaffEnrollResponse(**result)


@router.patch("/settings/staff/{user_id}/role", response_model=StaffItem)
def update_staff_role(
    user_id: str,
    body: StaffRoleUpdateRequest,
    request: Request,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    authorization: Annotated[str | None, Header()] = None,
) -> StaffItem:
    _step_up(request, authorization, settings)
    u = _invoke(
        ctx,
        _settings.update_staff_role,
        db,
        ctx,
        user_id,
        body.role,
        reason=body.reason,
        module="settings_identity",
    )
    return _staff_item(u)

