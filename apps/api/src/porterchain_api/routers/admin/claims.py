"""admin routes — claims."""

from porterchain_api.routers.admin._deps import *  # noqa: F403

@router.get("/claims/dashboard", response_model=ClaimDashboardResponse)
def claims_dashboard(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> ClaimDashboardResponse:
    require_module(ctx, "claims_read")
    return ClaimDashboardResponse(**_claims.dashboard(db))


@router.get("/claims/reports")
def claims_reports(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> dict:
    require_module(ctx, "claims_read")
    return _claims.reports(db)


@router.get("/claims", response_model=list[ClaimListItem])
def list_claims(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    status: str | None = None,
    claim_type: str | None = None,
    priority: str | None = None,
    investigator_id: str | None = None,
    merchant_id: str | None = None,
    driver_id: str | None = None,
    insurance: bool | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    amount_min_cents: int | None = None,
    amount_max_cents: int | None = None,
    risk_min: int | None = None,
    search: str | None = None,
) -> list[ClaimListItem]:
    require_module(ctx, "claims_read")
    from datetime import datetime

    filters = ClaimFilters(
        status=status,
        claim_type=claim_type,
        priority=priority,
        investigator_id=investigator_id,
        merchant_id=merchant_id,
        driver_id=driver_id,
        insurance=insurance,
        date_from=datetime.fromisoformat(date_from) if date_from else None,
        date_to=datetime.fromisoformat(date_to) if date_to else None,
        amount_min_cents=amount_min_cents,
        amount_max_cents=amount_max_cents,
        risk_min=risk_min,
        search=search,
    )
    return [ClaimListItem(**row) for row in _claims.list_enriched(db, filters)]


@router.get("/claims/{claim_id}", response_model=ClaimDetailResponse)
def get_claim_detail(
    claim_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> ClaimDetailResponse:
    require_module(ctx, "claims_read")
    detail = _claims.get_detail(db, claim_id)
    if not detail:
        raise HTTPException(status_code=404, detail="claim_not_found")
    return ClaimDetailResponse(**detail)


@router.post("/claims", response_model=ClaimListItem)
def create_claim(
    body: ClaimCreateRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> ClaimListItem:
    require_module(ctx, "claims")
    c = _claims.open_claim(
        db,
        ctx,
        order_id=body.order_id,
        claim_type=body.claim_type,
        description=body.description,
        priority=body.priority,
    )
    log_admin_audit(db, ctx, action="claim.create", resource_type="claim", resource_id=c.id)
    db.commit()
    return ClaimListItem(**_claims.claim_row(db, c))


@router.post("/claims/{claim_id}/status", response_model=ClaimDetailResponse)
def update_claim_status(
    claim_id: str,
    body: ClaimStatusUpdateRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> ClaimDetailResponse:
    require_module(ctx, "claims")
    try:
        _claims.update_status(db, ctx, claim_id, body.status)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="claim_not_found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    log_admin_audit(db, ctx, action="claim.status", resource_type="claim", resource_id=claim_id, payload={"status": body.status})
    db.commit()
    return get_claim_detail(claim_id, ctx, db)


@router.post("/claims/{claim_id}/assign", response_model=ClaimDetailResponse)
def assign_claim(
    claim_id: str,
    body: ClaimAssignRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> ClaimDetailResponse:
    require_module(ctx, "claims")
    try:
        _claims.assign_investigator(db, ctx, claim_id, body.investigator_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="claim_not_found") from exc
    log_admin_audit(db, ctx, action="claim.assign", resource_type="claim", resource_id=claim_id)
    db.commit()
    return get_claim_detail(claim_id, ctx, db)


@router.post("/claims/{claim_id}/auto-assign", response_model=ClaimDetailResponse)
def auto_assign_claim(
    claim_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> ClaimDetailResponse:
    require_module(ctx, "claims")
    try:
        _claims.auto_assign_investigator(db, ctx, claim_id)
    except (LookupError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    return get_claim_detail(claim_id, ctx, db)


@router.post("/claims/{claim_id}/evidence", response_model=ClaimDetailResponse)
def add_claim_evidence(
    claim_id: str,
    body: ClaimEvidenceRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> ClaimDetailResponse:
    require_module(ctx, "claims")
    try:
        _claims.add_evidence(
            db, ctx, claim_id, file_type=body.file_type, name=body.name, url=body.url, meta=body.meta
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="claim_not_found") from exc
    db.commit()
    return get_claim_detail(claim_id, ctx, db)


@router.post("/claims/{claim_id}/notes", response_model=ClaimDetailResponse)
def add_claim_note(
    claim_id: str,
    body: ClaimNoteRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> ClaimDetailResponse:
    require_module(ctx, "claims")
    try:
        _claims.add_note(db, ctx, claim_id, body=body.body, internal=body.internal, channel=body.channel)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="claim_not_found") from exc
    db.commit()
    return get_claim_detail(claim_id, ctx, db)


@router.post("/claims/{claim_id}/investigation", response_model=ClaimDetailResponse)
def update_claim_investigation(
    claim_id: str,
    body: ClaimInvestigationRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> ClaimDetailResponse:
    require_module(ctx, "claims")
    try:
        _claims.update_investigation(db, ctx, claim_id, body.model_dump(exclude_none=True))
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="claim_not_found") from exc
    db.commit()
    return get_claim_detail(claim_id, ctx, db)


@router.post("/claims/{claim_id}/compensation", response_model=ClaimDetailResponse)
def set_claim_compensation(
    claim_id: str,
    body: ClaimCompensationRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> ClaimDetailResponse:
    require_module(ctx, "claims")
    try:
        _claims.set_compensation(db, ctx, claim_id, body.model_dump(exclude_none=True))
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="claim_not_found") from exc
    db.commit()
    return get_claim_detail(claim_id, ctx, db)


@router.post("/claims/{claim_id}/insurance", response_model=ClaimDetailResponse)
def set_claim_insurance(
    claim_id: str,
    body: ClaimInsuranceRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> ClaimDetailResponse:
    require_module(ctx, "claims")
    try:
        _claims.set_insurance(db, ctx, claim_id, body.model_dump(exclude_none=True))
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="claim_not_found") from exc
    db.commit()
    return get_claim_detail(claim_id, ctx, db)


@router.post("/claims/bulk")
def bulk_claim_action(
    body: ClaimBulkRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> dict:
    require_module(ctx, "claims")
    result = _claims.bulk_action(
        db,
        ctx,
        claim_ids=body.claim_ids,
        action=body.action,
        investigator_id=body.investigator_id,
        status=body.status,
    )
    log_admin_audit(db, ctx, action=f"claim.bulk_{body.action}", resource_type="claim", resource_id=None)
    db.commit()
    return result


