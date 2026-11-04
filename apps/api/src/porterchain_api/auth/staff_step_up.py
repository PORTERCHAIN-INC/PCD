"""Staff step-up for sensitive admin mutations: a Keycloak login within 15 minutes."""

from __future__ import annotations

from fastapi import HTTPException, Request

from porterchain_api.auth.dev import allow_auth_dev_bypass
from porterchain_api.auth.keycloak_staff import assert_recent_login
from porterchain_api.config import Settings


def enforce_staff_step_up(
    request: Request,
    authorization: str | None,
    settings: Settings,
) -> None:
    """Require ``auth_time`` within 15m on the verified admin token. Bearer ``dev`` skips."""
    from porterchain_api.auth.sli_metrics import note_auth_event

    token = (authorization or "").removeprefix("Bearer ").strip()
    if allow_auth_dev_bypass(settings) and token == "dev":
        return
    claims = getattr(request.state, "admin_claims", None)
    try:
        assert_recent_login(claims)
        note_auth_event("staff_step_up_check", "ok")
    except PermissionError as exc:
        note_auth_event("staff_step_up_check", "required")
        raise HTTPException(status_code=403, detail=str(exc)) from exc
