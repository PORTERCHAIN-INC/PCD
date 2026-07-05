"""merchant routes — support_claims."""

from porterchain_api.routers.merchant._deps import *  # noqa: F403

@router.get("/support/tickets")
def support_tickets_list(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
    limit: int = Query(50, le=100),
):
    require_module(ctx, "support")
    return _support.list_tickets(db, ctx, limit=limit)


@router.get("/support/tickets/{ticket_id}")
def support_ticket_detail(
    ticket_id: str,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "support")
    try:
        return _support.get_ticket(db, ctx, ticket_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="ticket_not_found") from None


@router.post("/support/tickets")
def support_ticket_create(
    body: MerchantSupportTicketRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "support")
    try:
        return _support.create_ticket(db, ctx, **body.model_dump())
    except LookupError:
        raise HTTPException(status_code=404, detail="order_not_found") from None


@router.get("/support/knowledge-base")
def support_knowledge_base(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "support")
    return _support.knowledge_base(db)


@router.get("/claims")
def merchant_claims_list(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
    limit: int = Query(50, le=100),
):
    require_module(ctx, "claims")
    return _support.list_claims(db, ctx, limit=limit)


@router.get("/claims/{claim_id}")
def merchant_claim_detail(
    claim_id: str,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "claims")
    try:
        return _support.get_claim(db, ctx, claim_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="claim_not_found") from None


@router.post("/claims")
def merchant_claim_open(
    body: MerchantClaimOpenRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "claims")
    try:
        return _support.open_claim(db, ctx, **body.model_dump())
    except LookupError:
        raise HTTPException(status_code=404, detail="order_not_found") from None
