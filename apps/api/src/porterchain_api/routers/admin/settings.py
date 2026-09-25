"""admin routes — settings."""

from collections.abc import Callable
from typing import TypeVar

from fastapi import Header, Request

from porterchain_api.admin_engine.settings_bindings import bindings_payload, resolve_writable_config_key
from porterchain_api.admin_engine.settings_service import SETTINGS_SECTIONS
from porterchain_api.admin_engine.staff_idp_service import StaffIdpService
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
    StaffEnrollResponse,
    StaffInviteRequest,
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

_staff_idp = StaffIdpService()
T = TypeVar("T")
_SETTINGS_UNAVAILABLE = frozenset(
    {"clerk_not_configured", "staff_enrollment_redis_unavailable", "impersonation_redis_unavailable"}
)


def _reject_staff_clerk_route(user_type: str) -> None:
    """Staff uses /settings/staff/* IdP endpoints — not Clerk directory mutate routes."""
    if user_type == "staff":
        raise HTTPException(status_code=400, detail="staff_use_staff_idp_endpoints")


def _step_up(
    request: Request,
    authorization: str | None,
    settings: Settings,
) -> None:
    from porterchain_api.auth.staff_step_up import enforce_staff_step_up

    enforce_staff_step_up(request, authorization, settings)

def _invoke(
    ctx: AdminContext,
    fn: Callable[..., T],
    *args: object,
    module: str = "settings",
    **kwargs: object,
) -> T:
    try:
        require_module(ctx, module)
        return fn(*args, **kwargs)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        detail = str(exc)
        if detail in _SETTINGS_UNAVAILABLE:
            raise HTTPException(status_code=503, detail=detail) from exc
        raise HTTPException(status_code=400, detail=detail) from exc


def _staff_item(u) -> StaffItem:
    return StaffItem(id=u.id, email=u.email, name=u.name, role=u.role, created_at=u.created_at)


@router.get("/settings/dashboard")
def settings_dashboard(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    return _invoke(ctx, _settings.dashboard, db, settings)


@router.post("/settings/project-mode")
def settings_project_mode_change(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    settings: Settings = Depends(get_settings),
):
    """Refuse in-process mode flips — APP_ENV is boot-time only (Jeff Dean)."""
    require_module(ctx, "settings")
    raise HTTPException(
        status_code=403,
        detail={
            "code": "project_mode_immutable",
            "message": settings.runtime_posture.get("change_control")
            or "Set APP_ENV in Doppler or env/.env, then restart.",
            "current": settings.runtime_posture,
            "hint": "pnpm mode:set development|testing|production",
        },
    )


@router.get("/settings/center")
def settings_center(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    return _invoke(ctx, _settings.center, db, settings)


@router.get("/settings/health")
def settings_health(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    return _invoke(ctx, _settings.integration_health, db, settings)


@router.get("/settings/sections")
def settings_sections(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
):
    return _invoke(ctx, lambda: SETTINGS_SECTIONS)


@router.get("/settings/audit")
def settings_audit(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    limit: int = Query(100, le=500),
):
    return _invoke(ctx, _settings.audit_log, db, limit=limit)


@router.post("/settings/audit/{audit_id}/restore")
def settings_audit_restore(
    audit_id: str,
    request: Request,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    authorization: Annotated[str | None, Header()] = None,
    reason: str | None = Query(None),
):
    _step_up(request, authorization, settings)

    def _restore() -> dict:
        record = _settings.restore_config_from_audit(db, ctx, audit_id, reason=reason)
        return {"key": record.key, "value": record.value}

    return _invoke(ctx, _restore, module="settings_commercial")


@router.get("/settings/search")
def settings_search(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    q: str = "",
):
    return _invoke(ctx, _settings.search, q)


@router.get("/settings/validate")
def settings_validate(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    return _invoke(ctx, _settings.validate, settings, db)


@router.get("/settings/export")
def settings_export(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
):
    return _invoke(ctx, _settings.export_configuration, db)


@router.get("/settings/bindings")
def settings_bindings(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
):
    return _invoke(ctx, bindings_payload)


@router.post("/settings/import")
def settings_import(
    body: SettingsImportRequest,
    request: Request,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    authorization: Annotated[str | None, Header()] = None,
):
    if not body.dry_run:
        _step_up(request, authorization, settings)
    return _invoke(
        ctx,
        _settings.import_configuration,
        db,
        ctx,
        body.config,
        reason=body.reason,
        dry_run=body.dry_run,
        module="settings_commercial",
    )



@router.get("/settings/vehicles/overview")
def settings_vehicles_overview(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
):
    return _invoke(ctx, _settings.vehicles_overview, db)


@router.get("/settings/config")
def get_system_config(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
):
    def _payload() -> dict:
        return {
            "config": _settings.default_config(db),
            "module_config": _settings.module_config_links(db),
        }

    return _invoke(ctx, _payload)


@router.put("/settings/config/{key}")
def update_system_config(
    key: str,
    body: SettingsConfigUpdateRequest,
    request: Request,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    authorization: Annotated[str | None, Header()] = None,
):
    from porterchain_api.admin_engine.settings_bindings import COMMERCIAL_WRITE_KEYS

    _step_up(request, authorization, settings)

    def _put() -> dict:
        resolved = resolve_writable_config_key(key, reason=body.reason)
        record = _settings.set_config(db, ctx, resolved, body.value, reason=body.reason)
        return {"key": record.key, "value": record.value}

    return _invoke(
        ctx,
        _put,
        module="settings_commercial" if key in COMMERCIAL_WRITE_KEYS else "settings",
    )


@router.get("/settings/lead-ingest")
def settings_lead_ingest_get(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    settings: Settings = Depends(get_settings),
):
    """Lead webhook / CAPI / territory status — secret values never returned."""
    from porterchain_api.admin_engine.lead_ingest_settings import lead_ingest_settings_status

    return _invoke(ctx, lead_ingest_settings_status, settings)


@router.put("/settings/lead-ingest")
def settings_lead_ingest_put(
    body: dict,
    request: Request,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    authorization: Annotated[str | None, Header()] = None,
):
    """Write lead secrets/config to Doppler and refresh this process env."""
    from porterchain_api.admin_engine.lead_ingest_settings import update_lead_ingest_settings

    _step_up(request, authorization, settings)
    return _invoke(ctx, update_lead_ingest_settings, db, ctx, body, settings=settings)
