"""Settings → Compliance: registers, breach log, data-subject requests, erasure."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.rbac import AdminContext, require_module
from porterchain_api.auth.admin import get_admin_context
from porterchain_api.db import db_transaction, get_db
from porterchain_api.routers.admin._deps import router

public_router = APIRouter(prefix="/v1/public", tags=["public"])


@router.get("/compliance")
def compliance_overview(ctx: Annotated[AdminContext, Depends(get_admin_context)], db: Session = Depends(get_db)) -> dict:
    """Region profile, retention schedule, Art. 30 records, subprocessors, DPIA, breaches, requests."""
    require_module(ctx, "settings")
    from porterchain_api.platform.compliance import overview

    return overview(db)


@router.post("/privacy/erase")
def privacy_erase(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    body: dict = Body(...),
) -> dict:
    """Erase one person's contact data (dry run by default); keeps what tax law requires."""
    require_module(ctx, "settings")
    from porterchain_api.platform.privacy_erasure import erase_subject

    dry = bool(body.get("dry_run", True))
    try:
        if dry:
            return erase_subject(db, email=body.get("email"), phone=body.get("phone"), dry_run=True)
        with db_transaction(db):
            return erase_subject(
                db, email=body.get("email"), phone=body.get("phone"), dry_run=False, actor=str(getattr(ctx.user, "porterchain_user_id", None) or "admin")
            )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@public_router.get("/region")
def public_region(db: Session = Depends(get_db)) -> dict:
    """Locale, currency, tax label and whether the cookie banner must ask first (EU)."""
    from porterchain_api.platform.compliance import public_region as _public

    return _public(db)


@router.get("/security/my-ip")
def my_ip(ctx: Annotated[AdminContext, Depends(get_admin_context)], request: Request) -> dict:
    """The IP the API sees for you (add it before enabling the admin IP allowlist)."""
    from porterchain_api.platform.client_ip import client_ip

    return {"ip": client_ip(request)}


@router.get("/compliance/breaches/{breach_id}/evidence")
def breach_evidence(
    breach_id: str, ctx: Annotated[AdminContext, Depends(get_admin_context)], db: Session = Depends(get_db)
) -> dict:
    """One-click evidence pack (OPC / police): record, timeline, notifications, audit chain."""
    try:
        require_module(ctx, "settings")
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    from porterchain_api.platform.breach_evidence import evidence_pack

    try:
        return evidence_pack(db, breach_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/compliance/audit-chain/verify")
def audit_chain_verify(ctx: Annotated[AdminContext, Depends(get_admin_context)], db: Session = Depends(get_db)) -> dict:
    from porterchain_api.platform import forensics

    return {**forensics.verify(db), "public_key": forensics.public_key_b64()}
