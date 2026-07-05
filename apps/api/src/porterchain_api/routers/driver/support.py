"""driver routes — support."""

from porterchain_api.routers.driver._deps import *  # noqa: F403

@router.get("/support")
def list_support(ctx: Annotated[DriverContext, Depends(get_driver_context)], db: Session = Depends(get_db)):
    return {"tickets": _svc.platform.support_hub.list_tickets(db, ctx.driver.id)}


@router.get("/support/hub")
def support_hub(
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
):
    return _svc.platform.support_hub.snapshot(db, ctx.driver)


@router.get("/support/knowledge-base")
def support_knowledge_base(ctx: Annotated[DriverContext, Depends(get_driver_context)], db: Session = Depends(get_db)):
    return _svc.platform.support_hub.knowledge_base(db)


@router.get("/support/claims")
def list_driver_claims(ctx: Annotated[DriverContext, Depends(get_driver_context)], db: Session = Depends(get_db)):
    return {"claims": _svc.platform.support_hub.list_claims(db, ctx.driver.id)}


@router.post("/support/claims")
def open_driver_claim(
    body: DriverClaimOpenRequest,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
):
    try:
        claim = _svc.platform.support_hub.open_claim(
            db,
            ctx.driver,
            order_id=body.order_id,
            claim_type=body.claim_type,
            description=body.description,
        )
        db.commit()
        return claim
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/support/emergency-contact")
def get_emergency_contact(ctx: Annotated[DriverContext, Depends(get_driver_context)]):
    return _svc.platform.support_hub.emergency_contact(ctx.driver)


@router.put("/support/emergency-contact")
def update_emergency_contact(
    body: EmergencyContactUpdateRequest,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
):
    result = _svc.platform.support_hub.update_emergency_contact(
        db, ctx.driver, name=body.name, phone=body.phone, relationship=body.relationship
    )
    db.commit()
    return result


@router.post("/support")
def create_support(
    body: SupportTicketRequest,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
):
    try:
        ticket = _svc.platform.support.create_ticket(
            db,
            ctx.driver,
            subject=body.subject,
            description=body.description,
            order_id=body.order_id,
            priority=body.priority,
            category=body.category,
        )
        db.commit()
        return ticket
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/incidents")
def list_incidents(ctx: Annotated[DriverContext, Depends(get_driver_context)], db: Session = Depends(get_db)):
    return {"incidents": _svc.platform.incidents.list_incidents(db, ctx.driver.id)}


@router.post("/incidents")
def report_incident(
    body: IncidentRequest,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
):
    incident = _svc.platform.incidents.report_incident(
        db,
        ctx.driver,
        incident_type=body.incident_type,
        description=body.description,
        order_id=body.order_id,
        location=body.location,
    )
    db.commit()
    return incident


@router.post("/emergency")
def emergency(
    body: EmergencyRequest,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
):
    result = _svc.platform.emergency.trigger(db, ctx.driver, location=body.location, message=body.message)
    db.commit()
    return result

