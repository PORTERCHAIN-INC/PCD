"""admin routes — wholesale route templates (§8.1.10)."""

from porterchain_api.routers.admin._deps import (
    AdminContext,
    Annotated,
    Depends,
    HTTPException,
    RouteTemplateCreateRequest,
    RouteTemplateItem,
    RouteTemplateUpdateRequest,
    Session,
    _route_templates,
    get_admin_context,
    get_db,
    log_admin_audit,
    require_module,
    router,
)


def _serialize(record) -> RouteTemplateItem:
    return RouteTemplateItem(**_route_templates.serialize(record))


@router.get("/route-templates", response_model=list[RouteTemplateItem])
def list_route_templates(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    merchant_id: str | None = None,
    include_inactive: bool = False,
) -> list[RouteTemplateItem]:
    require_module(ctx, "routes_dispatch")
    rows = _route_templates.list_templates(
        db, merchant_id=merchant_id, active_only=not include_inactive
    )
    return [_serialize(row) for row in rows]


@router.get("/route-templates/{template_id}", response_model=RouteTemplateItem)
def get_route_template(
    template_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> RouteTemplateItem:
    require_module(ctx, "routes_dispatch")
    record = _route_templates.get_template(db, template_id)
    if not record:
        raise HTTPException(status_code=404, detail="route_template_not_found")
    return _serialize(record)


@router.post("/route-templates", response_model=RouteTemplateItem, status_code=201)
def create_route_template(
    body: RouteTemplateCreateRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> RouteTemplateItem:
    require_module(ctx, "routes_dispatch")
    record = _route_templates.create_template(
        db,
        name=body.name,
        merchant_id=body.merchant_id,
        zone=body.zone,
        schedule=body.schedule,
        stops=body.stops,
        config=body.config,
        created_by=ctx.user.id,
    )
    log_admin_audit(
        db,
        ctx,
        action="route_template_create",
        resource_type="route_template",
        resource_id=record.id,
        payload={"name": body.name, "merchant_id": body.merchant_id},
    )
    return _serialize(record)


@router.patch("/route-templates/{template_id}", response_model=RouteTemplateItem)
def update_route_template(
    template_id: str,
    body: RouteTemplateUpdateRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> RouteTemplateItem:
    require_module(ctx, "routes_dispatch")
    try:
        record = _route_templates.update_template(
            db,
            template_id,
            name=body.name,
            merchant_id=body.merchant_id,
            zone=body.zone,
            schedule=body.schedule,
            stops=body.stops,
            config=body.config,
            is_active=body.is_active,
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="route_template_not_found") from None
    log_admin_audit(
        db,
        ctx,
        action="route_template_update",
        resource_type="route_template",
        resource_id=template_id,
        payload=body.model_dump(exclude_unset=True),
    )
    return _serialize(record)


@router.delete("/route-templates/{template_id}", status_code=204)
def delete_route_template(
    template_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> None:
    require_module(ctx, "routes_dispatch")
    try:
        _route_templates.delete_template(db, template_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="route_template_not_found") from None
    log_admin_audit(
        db,
        ctx,
        action="route_template_deactivate",
        resource_type="route_template",
        resource_id=template_id,
    )
