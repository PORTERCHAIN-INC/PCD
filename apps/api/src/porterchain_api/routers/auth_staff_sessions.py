"""Staff session, passkey, and step-up routes. Shared /v1/auth router."""

from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from porterchain_api.auth import staff_webauthn
from porterchain_api.auth.sli_metrics import note_auth_event
from porterchain_api.auth.staff_session import (
    clear_session_cookie,
    delete_passkey,
    get_session,
    list_passkeys,
    list_sessions_for_user,
    mark_step_up,
    revoke_all_for_user,
    revoke_session,
    staff_cookie_params,
)
from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db
from porterchain_api.routers.auth import (
    _current_staff_sid,
    _invoke,
    router,
)


@router.get("/staff/sessions")
async def staff_list_sessions(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """List Redis sessions for the current staff user."""
    from porterchain_api.auth.admin import get_admin_context

    ctx = await get_admin_context(request, authorization, db, settings, None)
    current = _current_staff_sid(request, authorization)
    return {"sessions": list_sessions_for_user(ctx.user.id, current_session_id=current)}


@router.get("/staff/security-status")
async def staff_security_status(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Passkey gate + recent security events for Account → Security / soft banner."""
    from porterchain_shared.config.project_mode import runtime_posture_from_settings

    from porterchain_api.auth.admin import get_admin_context
    from porterchain_api.auth.staff_security_events import list_security_events

    ctx = await get_admin_context(request, authorization, db, settings, None)
    passkeys = list_passkeys(db, ctx.user.id)
    posture = runtime_posture_from_settings(settings)
    cookie = staff_cookie_params(settings)
    return {
        "passkey_count": len(passkeys),
        "passkey_recommended": len(passkeys) == 0,
        "events": list_security_events(ctx.user.id, limit=20),
        "cookie_posture": {
            "domain_mode": posture.cookie_domain_mode,
            "secure": cookie["secure"],
            "samesite": cookie["samesite"],
            "httponly": cookie["httponly"],
            "domain": cookie["domain"],
        },
    }


@router.delete("/staff/sessions/{session_id}")
async def staff_revoke_session(
    session_id: str,
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Revoke one of the caller's sessions (or self via logout)."""
    from porterchain_api.auth.admin import get_admin_context

    ctx = await get_admin_context(request, authorization, db, settings, None)
    session = None

    session = get_session(session_id, touch=False)
    if session is None or session.admin_user_id != ctx.user.id:
        raise HTTPException(status_code=404, detail="session_not_found")
    revoke_session(session_id)
    note_auth_event("staff_session_revoke", "ok")
    current = _current_staff_sid(request, authorization)
    if current == session_id:
        return clear_session_cookie(JSONResponse({"ok": True, "signed_out": True}), settings)
    return {"ok": True, "signed_out": False}


@router.post("/staff/sessions/revoke-others")
async def staff_revoke_other_sessions(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Keep the current session; revoke every other device session."""
    from porterchain_api.auth.admin import get_admin_context

    ctx = await get_admin_context(request, authorization, db, settings, None)
    current = _current_staff_sid(request, authorization)
    revoked = revoke_all_for_user(ctx.user.id, except_session_id=current)
    note_auth_event("staff_session_revoke_others", "ok")
    return {"ok": True, "revoked": revoked}


@router.get("/staff/passkeys")
async def staff_list_passkeys(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    from porterchain_api.auth.admin import get_admin_context

    ctx = await get_admin_context(request, authorization, db, settings, None)
    return {"passkeys": list_passkeys(db, ctx.user.id)}


@router.delete("/staff/passkeys/{credential_id}")
async def staff_delete_passkey(
    credential_id: str,
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    from porterchain_api.auth.admin import get_admin_context

    ctx = await get_admin_context(request, authorization, db, settings, None)
    ok = delete_passkey(db, admin_user_id=ctx.user.id, credential_row_id=credential_id)
    if not ok:
        raise HTTPException(status_code=404, detail="passkey_not_found")
    return {"ok": True}


@router.post("/staff/step-up/options")
async def staff_step_up_options(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """WebAuthn options for refreshing the step-up window (authenticated)."""
    from porterchain_api.auth.admin import get_admin_context

    ctx = await get_admin_context(request, authorization, db, settings, None)
    return _invoke(staff_webauthn.step_up_options, db, settings, admin_user=ctx.user)


@router.post("/staff/step-up")
async def staff_step_up(
    body: dict,
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Confirm passkey to refresh step-up window (required for enroll after idle)."""
    from porterchain_api.auth.admin import get_admin_context

    ctx = await get_admin_context(request, authorization, db, settings, None)
    sid = _current_staff_sid(request, authorization)
    if not sid:
        raise HTTPException(status_code=401, detail="staff_session_invalid")

    challenge_id = (body.get("challenge_id") or "").strip()
    assertion = body.get("passkey_assertion") or body.get("credential") or {}
    credential = assertion.get("credential") if isinstance(assertion, dict) and "credential" in assertion else assertion
    if not challenge_id or not isinstance(credential, dict):
        raise HTTPException(status_code=400, detail="passkey_assertion_invalid")

    _invoke(
        staff_webauthn.confirm_passkey_for_admin,
        db,
        settings,
        admin_user=ctx.user,
        challenge_id=challenge_id,
        credential=credential,
    )
    updated = mark_step_up(sid)
    if updated is None:
        note_auth_event("staff_step_up", "fail")
        raise HTTPException(status_code=503, detail="staff_session_redis_unavailable")
    note_auth_event("staff_step_up", "ok")
    return {"ok": True, "step_up_at": updated.step_up_at}
