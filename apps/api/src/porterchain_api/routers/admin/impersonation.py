"""Admin audited impersonation routes — Super Admin break-glass only."""

from typing import Annotated

from fastapi import Depends, Header, Request
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.impersonation_service import ImpersonationService
from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db
from porterchain_api.routers.admin._deps import (
    AdminContext,
    ImpersonationSessionResponse,
    ImpersonationStartRequest,
    ImpersonationStopRequest,
    get_admin_context,
    require_module,
    router,
)
from porterchain_api.routers.admin.settings import _invoke, _step_up

_impersonation = ImpersonationService()


@router.post("/impersonation/start", response_model=ImpersonationSessionResponse)
def start_impersonation(
    body: ImpersonationStartRequest,
    request: Request,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    authorization: Annotated[str | None, Header()] = None,
) -> ImpersonationSessionResponse:
    """Mint a short-lived audited persona session (no forged Clerk JWT)."""
    _step_up(request, authorization, settings)
    from porterchain_api.auth.staff_session import session_id_from_authorization

    result = _invoke(
        ctx,
        _impersonation.start,
        db,
        ctx,
        settings,
        target_type=body.target_type,
        target_id=body.target_id,
        reason=body.reason,
        staff_session_id=session_id_from_authorization(authorization) or "",
        module="impersonation",
    )
    return ImpersonationSessionResponse(**result)


@router.post("/impersonation/stop")
def stop_impersonation(
    body: ImpersonationStopRequest,
    request: Request,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    authorization: Annotated[str | None, Header()] = None,
) -> dict:
    _step_up(request, authorization, settings)
    return _invoke(
        ctx,
        _impersonation.stop,
        db,
        ctx,
        session_id=body.session_id,
        module="impersonation",
    )


@router.get("/impersonation/{session_id}", response_model=ImpersonationSessionResponse)
def impersonation_status(
    session_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
) -> ImpersonationSessionResponse:
    require_module(ctx, "impersonation")
    status = _impersonation.status(session_id)
    if not status:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="impersonation_not_found")
    return ImpersonationSessionResponse(**status)
