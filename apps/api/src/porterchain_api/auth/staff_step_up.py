"""Shared staff step-up enforcement for sensitive admin mutations."""

from __future__ import annotations

from fastapi import HTTPException, Request

from porterchain_api.auth.dev import allow_auth_dev_bypass
from porterchain_api.auth.staff_session import (
    STAFF_COOKIE_NAME,
    assert_recent_step_up,
    get_session,
    session_id_from_authorization,
)
from porterchain_api.config import Settings


def enforce_staff_step_up(
    request: Request,
    authorization: str | None,
    settings: Settings,
) -> None:
    """Require a fresh step-up (login / passkey within 15m). Bearer ``dev`` skips."""
    from porterchain_api.auth.sli_metrics import note_auth_event

    token = (authorization or "").removeprefix("Bearer ").strip()
    if token == "dev" and allow_auth_dev_bypass(settings):
        return
    sid = session_id_from_authorization(authorization) or request.cookies.get(STAFF_COOKIE_NAME)
    try:
        assert_recent_step_up(get_session(sid, touch=False) if sid else None)
        note_auth_event("staff_step_up_check", "ok")
    except PermissionError as exc:
        note_auth_event("staff_step_up_check", "required")
        raise HTTPException(status_code=403, detail=str(exc)) from exc
