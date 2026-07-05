"""admin routes — support."""

from porterchain_api.routers.admin._deps import *  # noqa: F403

@router.get("/support/dashboard", response_model=TicketDashboardResponse)
def support_dashboard(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> TicketDashboardResponse:
    require_module(ctx, "support_read")
    return TicketDashboardResponse(**_support.dashboard(db))


@router.get("/support/reports")
def support_reports(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "support_read")
    return _support.reports(db)


@router.get("/support/tickets", response_model=list[TicketListItem])
def list_tickets(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    status: str | None = None,
    category: str | None = None,
    priority: str | None = None,
    agent_id: str | None = None,
    merchant_id: str | None = None,
    driver_id: str | None = None,
    customer_id: str | None = None,
    sla: str | None = None,
    module: str | None = None,
    search: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = Query(500, le=1000),
) -> list[TicketListItem]:
    require_module(ctx, "support_read")
    from datetime import datetime

    filters = SupportFilters(
        status=status,
        category=category,
        priority=priority,
        agent_id=agent_id,
        merchant_id=merchant_id,
        driver_id=driver_id,
        customer_id=customer_id,
        sla=sla,
        module=module,
        search=search,
        date_from=datetime.fromisoformat(date_from) if date_from else None,
        date_to=datetime.fromisoformat(date_to) if date_to else None,
        limit=limit,
    )
    return [TicketListItem(**row) for row in _support.list_enriched(db, filters)]


@router.get("/support/tickets/{ticket_id}", response_model=TicketDetailResponse)
def get_ticket_detail(
    ticket_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> TicketDetailResponse:
    require_module(ctx, "support_read")
    detail = _support.get_detail(db, ticket_id)
    if not detail:
        raise HTTPException(404, "ticket_not_found")
    return TicketDetailResponse(**detail)


@router.post("/support/tickets", response_model=TicketListItem)
def create_ticket(
    body: TicketCreateRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> TicketListItem:
    require_module(ctx, "support")
    t = _support.create_ticket(db, ctx, **body.model_dump())
    return TicketListItem(**_support._row(db, t))


@router.post("/support/tickets/{ticket_id}/status", response_model=TicketDetailResponse)
def update_ticket_status(
    ticket_id: str,
    body: TicketStatusRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> TicketDetailResponse:
    require_module(ctx, "support")
    try:
        _support.update_status(db, ctx, ticket_id, body.status)
    except LookupError:
        raise HTTPException(404, "ticket_not_found") from None
    except ValueError:
        raise HTTPException(400, "invalid_status") from None
    detail = _support.get_detail(db, ticket_id)
    return TicketDetailResponse(**detail)


@router.post("/support/tickets/{ticket_id}/assign", response_model=TicketDetailResponse)
def assign_ticket(
    ticket_id: str,
    body: TicketAssignRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> TicketDetailResponse:
    require_module(ctx, "support")
    try:
        _support.assign_agent(db, ctx, ticket_id, body.agent_id)
    except LookupError:
        raise HTTPException(404, "ticket_not_found") from None
    detail = _support.get_detail(db, ticket_id)
    return TicketDetailResponse(**detail)


@router.post("/support/tickets/{ticket_id}/auto-assign", response_model=TicketDetailResponse)
def auto_assign_ticket(
    ticket_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> TicketDetailResponse:
    require_module(ctx, "support")
    try:
        _support.auto_assign(db, ctx, ticket_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from None
    detail = _support.get_detail(db, ticket_id)
    return TicketDetailResponse(**detail)


@router.post("/support/tickets/{ticket_id}/notes", response_model=TicketDetailResponse)
def add_ticket_note(
    ticket_id: str,
    body: TicketNoteRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> TicketDetailResponse:
    require_module(ctx, "support")
    try:
        _support.add_note(db, ctx, ticket_id, body=body.body, internal=body.internal, channel=body.channel)
    except LookupError:
        raise HTTPException(404, "ticket_not_found") from None
    detail = _support.get_detail(db, ticket_id)
    return TicketDetailResponse(**detail)


@router.post("/support/tickets/{ticket_id}/sla/pause", response_model=TicketDetailResponse)
def pause_ticket_sla(
    ticket_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> TicketDetailResponse:
    require_module(ctx, "support")
    try:
        _support.pause_sla(db, ctx, ticket_id)
    except LookupError:
        raise HTTPException(404, "ticket_not_found") from None
    detail = _support.get_detail(db, ticket_id)
    return TicketDetailResponse(**detail)


@router.post("/support/tickets/{ticket_id}/sla/resume", response_model=TicketDetailResponse)
def resume_ticket_sla(
    ticket_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> TicketDetailResponse:
    require_module(ctx, "support")
    try:
        _support.resume_sla(db, ctx, ticket_id)
    except LookupError:
        raise HTTPException(404, "ticket_not_found") from None
    detail = _support.get_detail(db, ticket_id)
    return TicketDetailResponse(**detail)


@router.post("/support/bulk")
def support_bulk(
    body: TicketBulkRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "support")
    return {
        "results": _support.bulk_action(
            db,
            ctx,
            body.ticket_ids,
            body.action,
            agent_id=body.agent_id,
            status=body.status,
        )
    }


@router.get("/support/knowledge-base")
def get_support_kb(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "support_read")
    return _support.get_knowledge_base(db)


@router.post("/support/knowledge-base/articles")
def save_support_kb_article(
    body: SupportKbArticleRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "support")
    return _support.save_kb_article(db, ctx, body.model_dump())


@router.get("/support/macros")
def get_support_macros(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "support_read")
    return _support.get_macros(db)


@router.post("/support/macros")
def save_support_macro(
    body: SupportMacroRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "support")
    return _support.save_macro(db, ctx, body.model_dump())


@router.get("/support/automation")
def get_support_automation(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "support_read")
    return _support.get_automation_rules(db)


@router.post("/support/automation")
def set_support_automation(
    body: SupportAutomationRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "support")
    return _support.set_automation_rules(db, ctx, body.model_dump(exclude_none=True))


@router.get("/support/settings/sla")
def get_support_sla(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "support_read")
    return _support._sla_config(db)


@router.post("/support/settings/sla")
def set_support_sla(
    body: SupportSlaConfigRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "support")
    return _support.set_sla_config(db, ctx, body.model_dump(exclude_none=True))


