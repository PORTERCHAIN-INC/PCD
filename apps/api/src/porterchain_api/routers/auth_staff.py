"""Staff IdP login routes. Registered on the shared /v1/auth router."""

from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.staff_idp_service import StaffIdpService
from porterchain_api.auth import staff_webauthn
from porterchain_api.auth.sli_metrics import note_auth_event
from porterchain_api.auth.staff_rate_limit import enforce_staff_auth_rate
from porterchain_api.auth.staff_session import (
    authentication_options_for_email,
    clear_session_cookie,
    client_meta_from_request,
    login_from_body,
    passkey_credential_payload,
    peek_enrollment,
    revoke_session,
    verify_registration_from_body,
)
from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db
from porterchain_api.routers.auth import (
    _current_staff_sid,
    _invoke,
    _staff_session_response,
    router,
)
from fastapi.responses import JSONResponse

@router.get("/staff/enrollment/{token}")
def peek_staff_enrollment(token: str, request: Request) -> dict:
    """Public peek for staff IdP activation UI (no Clerk)."""
    enforce_staff_auth_rate(request)
    return _invoke(peek_enrollment, token)


@router.post("/staff/enrollment/{token}/activate")
def activate_staff_enrollment(
    token: str,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Consume enrollment token, mint Redis session, set ``pc_staff_sid`` cookie."""
    enforce_staff_auth_rate(request)
    try:
        payload = _invoke(
            StaffIdpService().activate,
            db,
            token,
            settings=settings,
            client_meta=client_meta_from_request(request),
        )
        note_auth_event("staff_activate", "ok")
        return _staff_session_response(payload, settings)
    except HTTPException as exc:
        note_auth_event("staff_activate", "fail")
        raise exc


@router.post("/staff/local-session")
def mint_local_super_admin_session(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Development only — mint Staff IdP session as Local Super Admin (Jeff Dean: one path).

    Requires ``CLERK_DEV_BYPASS`` + development project mode. Production always 400.
    Returns the same ``bearer_token`` + cookie shape as enrollment activate.
    """
    enforce_staff_auth_rate(request)
    try:
        payload = _invoke(
            StaffIdpService().mint_local_super_admin_session,
            db,
            settings,
            client_meta=client_meta_from_request(request),
        )
        note_auth_event("staff_local_session", "ok")
        return _staff_session_response(payload, settings)
    except HTTPException as exc:
        note_auth_event("staff_local_session", "fail")
        raise exc


@router.post("/staff/login-request")
def staff_login_request(
    body: dict,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Email a one-time staff login link (token included only in local env)."""
    email = body.get("email") or ""
    enforce_staff_auth_rate(request, email=str(email))
    try:
        out = _invoke(StaffIdpService().request_login, db, settings, email=email)
        note_auth_event("staff_login_request", "ok")
        return out
    except HTTPException as exc:
        note_auth_event("staff_login_request", "fail")
        raise exc


@router.post("/staff/passkey/register/options")
async def staff_passkey_register_options(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """WebAuthn registration options for an authenticated staff session."""
    from porterchain_api.auth.admin import get_admin_context

    ctx = await get_admin_context(request, authorization, db, settings, None)
    return _invoke(staff_webauthn.registration_options, db, settings, ctx.user)


@router.post("/staff/passkey/register/verify")
async def staff_passkey_register_verify(
    body: dict,
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Verify WebAuthn registration and persist credential."""
    from porterchain_api.auth.admin import get_admin_context

    ctx = await get_admin_context(request, authorization, db, settings, None)
    row = _invoke(verify_registration_from_body, db, settings, admin_user=ctx.user, body=body)
    return passkey_credential_payload(row)


@router.post("/staff/passkey/login/options")
def staff_passkey_login_options(
    body: dict,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """WebAuthn authentication options for staff email (public)."""
    email = body.get("email") or ""
    enforce_staff_auth_rate(request, email=str(email))
    return _invoke(authentication_options_for_email, db, settings, email=email)


@router.post("/staff/login")
def staff_login(
    body: dict,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Activate via enrollment_token or passkey_assertion. Sets staff session cookie."""
    enforce_staff_auth_rate(request)
    factor = "passkey" if body.get("passkey_assertion") else "enrollment"
    try:
        payload = _invoke(
            login_from_body,
            db,
            settings,
            body,
            client_meta=client_meta_from_request(request),
        )
        note_auth_event(f"staff_login_{factor}", "ok")
        return _staff_session_response(payload, settings)
    except HTTPException as exc:
        note_auth_event(f"staff_login_{factor}", "fail")
        raise exc


@router.post("/staff/logout")
def staff_logout(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
    settings: Settings = Depends(get_settings),
):
    """Revoke staff session + clear cookie."""
    sid = _current_staff_sid(request, authorization)
    if sid:
        revoke_session(sid)
        note_auth_event("staff_logout", "ok")
    else:
        note_auth_event("staff_logout", "noop")
    return clear_session_cookie(JSONResponse({"ok": True}), settings)


@router.get("/impersonation/me")
def impersonation_me(
    authorization: Annotated[str | None, Header()] = None,
):
    """Portal banner — resolve active audited impersonation from ``pc_imp_`` bearer."""
    from porterchain_api.auth.impersonation_session import resolve_from_authorization

    session = resolve_from_authorization(authorization)
    if not session:
        raise HTTPException(status_code=401, detail="impersonation_expired")
    return session.public_dict()


@router.post("/impersonation/end")
def impersonation_end_self(
    authorization: Annotated[str | None, Header()] = None,
):
    """End impersonation from the portal banner (actor token)."""
    from porterchain_api.auth.impersonation_session import (
        resolve_from_authorization,
        revoke_session,
    )

    session = resolve_from_authorization(authorization)
    if not session:
        raise HTTPException(status_code=401, detail="impersonation_expired")
    revoke_session(session.session_id)
    note_auth_event("impersonation_end", "ok")
    return {"ok": True, "session_id": session.session_id}

