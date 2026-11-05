"""admin routes — claims under the cargo insurance policy (letters, broker notice). Drafts only."""

from porterchain_api.routers.admin._deps import (
    AdminContext,
    Annotated,
    ClaimBrokerNotifiedRequest,
    ClaimLetterRequest,
    Depends,
    HTTPException,
    Session,
    _claims,
    commit_admin_write,
    get_admin_context,
    get_db,
    require_module,
    router,
)


# ── Insurance-policy claims handling (COI B5000191409). Drafts only: nothing is sent from the API. ──


@router.post("/claims/{claim_id}/letters")
def draft_claim_letter(
    claim_id: str,
    body: ClaimLetterRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> dict:
    require_module(ctx, "claims")
    try:
        out = _claims.draft_letter(
            db, ctx, claim_id, body.kind, amount_cents=body.amount_cents, reason=body.reason, details=body.details
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="claim_not_found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    commit_admin_write(db)
    return out


@router.post("/claims/{claim_id}/broker-notice")
def prepare_claim_broker_notice(
    claim_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> dict:
    require_module(ctx, "claims")
    try:
        out = _claims.prepare_broker_notice(db, ctx, claim_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="claim_not_found") from exc
    commit_admin_write(db)
    return out


@router.post("/claims/{claim_id}/broker-notice/sent")
def record_claim_broker_notified(
    claim_id: str,
    body: ClaimBrokerNotifiedRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> dict:
    require_module(ctx, "claims")
    try:
        out = _claims.record_broker_notified(
            db, ctx, claim_id, sent_on=body.sent_on, method=body.method, broker_reference=body.broker_reference
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="claim_not_found") from exc
    commit_admin_write(db)
    return out
