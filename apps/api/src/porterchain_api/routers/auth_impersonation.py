"""Portal impersonation banner routes (audited ``pc_imp_`` actor tokens)."""

from typing import Annotated

from fastapi import Header, HTTPException

from porterchain_api.auth.sli_metrics import note_auth_event
from porterchain_api.routers.auth import router


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

