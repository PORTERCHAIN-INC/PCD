"""admin routes — settings."""

from porterchain_api.routers.admin._deps import (
    AdminContext,
    Annotated,
    Depends,
    HTTPException,
    PlatformUserAuthorizeRequest,
    PlatformUserAuthorizeResponse,
    PlatformUserCreateRequest,
    PlatformUserDeleteRequest,
    PlatformUserUpdateRequest,
    PlatformUsersResponse,
    Query,
    Session,
    Settings,
    SettingsConfigUpdateRequest,
    SettingsImportRequest,
    StaffInviteRequest,
    StaffInviteResponse,
    StaffItem,
    StaffRoleUpdateRequest,
    _clerk_directory,
    _settings,
    get_admin_context,
    get_db,
    get_settings,
    require_module,
    router,
)


@router.get("/settings/dashboard")
def settings_dashboard(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    require_module(ctx, "settings")
    return _settings.dashboard(db, settings)


@router.get("/settings/center")
def settings_center(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    require_module(ctx, "settings")
    return _settings.center(db, settings)


@router.get("/settings/health")
def settings_health(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    require_module(ctx, "settings")
    return _settings.integration_health(db, settings)


@router.get("/settings/sections")
def settings_sections(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
):
    require_module(ctx, "settings")
    from porterchain_api.admin_engine.settings_service import SETTINGS_SECTIONS

    return SETTINGS_SECTIONS


@router.get("/settings/audit")
def settings_audit(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    limit: int = Query(100, le=500),
):
    require_module(ctx, "settings")
    return _settings.audit_log(db, limit=limit)


@router.get("/settings/search")
def settings_search(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    q: str = "",
):
    require_module(ctx, "settings")
    return _settings.search(q)


@router.get("/settings/validate")
def settings_validate(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    require_module(ctx, "settings")
    return _settings.validate(settings, db)


@router.get("/settings/export")
def settings_export(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "settings")
    return _settings.export_configuration(db)


@router.post("/settings/import")
def settings_import(
    body: SettingsImportRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "settings")
    return _settings.import_configuration(db, ctx, body.config, reason=body.reason)


@router.get("/settings/staff", response_model=list[StaffItem])
def list_staff(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> list[StaffItem]:
    require_module(ctx, "settings")
    return [
        StaffItem(id=u.id, email=u.email, name=u.name, role=u.role, created_at=u.created_at)
        for u in _settings.list_staff(db)
    ]


@router.get("/settings/users/{user_type}", response_model=PlatformUsersResponse)
def list_platform_users(
    user_type: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    limit: int = Query(500, ge=1, le=2000),
    search: str | None = Query(None, max_length=200),
    access_status: str | None = Query(None),
    invite_status: str | None = Query(None),
    identity_status: str | None = Query(None),
    account_status: str | None = Query(None),
    clerk_status: str | None = Query(None),
) -> PlatformUsersResponse:
    require_module(ctx, "settings")
    if user_type not in ("staff", "driver", "customer", "merchant"):
        raise HTTPException(400, "invalid_user_type")
    try:
        return _settings.list_platform_users(
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
    except ValueError as exc:
        raise HTTPException(400, "invalid_user_type") from exc


@router.post("/settings/users/{user_type}", status_code=201)
def create_platform_user(
    user_type: str,
    body: PlatformUserCreateRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    require_module(ctx, "settings")
    if user_type not in ("staff", "driver", "customer", "merchant"):
        raise HTTPException(400, "invalid_user_type")
    try:
        return _clerk_directory.create_user(
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
        )
    except ValueError as exc:
        detail = str(exc)
        if detail == "clerk_not_configured":
            raise HTTPException(503, detail) from exc
        raise HTTPException(400, detail) from exc


@router.patch("/settings/users/{user_type}/clerk")
def update_platform_clerk_user(
    user_type: str,
    body: PlatformUserUpdateRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    require_module(ctx, "settings")
    if user_type not in ("staff", "driver", "customer", "merchant"):
        raise HTTPException(400, "invalid_user_type")
    try:
        return _clerk_directory.update_clerk_user(
            db,
            ctx,
            settings,
            user_type,
            body.clerk_user_id,
            name=body.name,
            password=body.password,
            banned=body.banned,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/settings/users/{user_type}/delete", status_code=204)
def delete_platform_user(
    user_type: str,
    body: PlatformUserDeleteRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> None:
    require_module(ctx, "settings")
    if user_type not in ("staff", "driver", "customer", "merchant"):
        raise HTTPException(400, "invalid_user_type")
    if not body.clerk_user_id and not body.platform_user_id:
        raise HTTPException(400, "clerk_user_id_or_platform_user_id_required")
    try:
        _clerk_directory.delete_clerk_user(
            db,
            ctx,
            settings,
            user_type,
            clerk_user_id=body.clerk_user_id,
            platform_user_id=body.platform_user_id,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/settings/users/{user_type}/authorize", response_model=PlatformUserAuthorizeResponse)
def authorize_platform_user(
    user_type: str,
    body: PlatformUserAuthorizeRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> PlatformUserAuthorizeResponse:
    require_module(ctx, "settings")
    if user_type not in ("staff", "driver", "customer", "merchant"):
        raise HTTPException(400, "invalid_user_type")
    if not body.platform_user_id and not body.clerk_user_id and not body.email:
        raise HTTPException(400, "platform_user_id_clerk_user_id_or_email_required")
    try:
        return _settings.authorize_platform_user(
            db,
            ctx,
            settings,
            user_type,
            platform_user_id=body.platform_user_id,
            clerk_user_id=body.clerk_user_id,
            email=body.email,
            name=body.name,
            reason=body.reason,
        )
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/settings/staff/invite", response_model=StaffInviteResponse, status_code=201)
def invite_staff(
    body: StaffInviteRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> StaffInviteResponse:
    require_module(ctx, "settings")
    try:
        user, invitation = _settings.invite_staff(
            db, ctx, settings, email=body.email, role=body.role, name=body.name
        )
    except ValueError as exc:
        detail = str(exc)
        if detail == "clerk_not_configured":
            raise HTTPException(503, "clerk_not_configured") from exc
        if detail == "invalid_admin_role":
            raise HTTPException(400, "invalid_admin_role") from exc
        raise
    return StaffInviteResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,
        clerk_action=invitation.invitation_metadata.get("clerk_action", "invited"),
        invitation_status=invitation.status,
        created_at=user.created_at,
    )


@router.patch("/settings/staff/{user_id}/role", response_model=StaffItem)
def update_staff_role(
    user_id: str,
    body: StaffRoleUpdateRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> StaffItem:
    require_module(ctx, "settings")
    try:
        u = _settings.update_staff_role(db, ctx, user_id, body.role, reason=body.reason)
    except LookupError:
        raise HTTPException(404, "staff_not_found") from None
    return StaffItem(id=u.id, email=u.email, name=u.name, role=u.role, created_at=u.created_at)


@router.get("/settings/vehicles/overview")
def settings_vehicles_overview(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "settings")
    return _settings.vehicles_overview(db)


@router.get("/settings/config")
def get_system_config(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "settings")
    return {
        "config": _settings.default_config(db),
        "module_config": _settings.module_config_links(db),
    }


@router.put("/settings/config/{key}")
def update_system_config(
    key: str,
    body: SettingsConfigUpdateRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "settings")
    from porterchain_api.admin_engine.settings_service import CONFIG_KEYS, DEFAULTS

    resolved = CONFIG_KEYS.get(key, key)
    if resolved not in DEFAULTS and not resolved.startswith("settings_"):
        raise HTTPException(400, "unknown_config_key")
    record = _settings.set_config(db, ctx, resolved, body.value, reason=body.reason)
    return {"key": record.key, "value": record.value}
