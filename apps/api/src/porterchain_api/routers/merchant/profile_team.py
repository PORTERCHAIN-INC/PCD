"""merchant routes — profile_team."""

from porterchain_api.routers.merchant._deps import (
    Annotated,
    Depends,
    HTTPException,
    MerchantContactCreateRequest,
    MerchantContactResponse,
    MerchantContactUpdateRequest,
    MerchantContext,
    MerchantProfileResponse,
    MerchantProfileUpdateRequest,
    MerchantTwoFactorRequest,
    Query,
    RecipientCreateRequest,
    RecipientResponse,
    SavedAddressCreateRequest,
    SavedAddressResponse,
    Session,
    Settings,
    TeamInviteRequest,
    TeamMemberResponse,
    TeamRoleUpdateRequest,
    _contacts,
    _handle_permission,
    _profile,
    _profile_response,
    _team,
    get_db,
    get_merchant_context,
    get_settings,
    require_module,
    router,
)


@router.get("/profile", response_model=MerchantProfileResponse)
def get_profile(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
) -> MerchantProfileResponse:
    require_module(ctx, "settings")
    return _profile_response(_profile.get_profile(ctx))


@router.patch("/profile", response_model=MerchantProfileResponse)
def update_profile(
    body: MerchantProfileUpdateRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> MerchantProfileResponse:
    require_module(ctx, "settings")
    merchant = _profile.update_profile(db, ctx, body)
    return _profile_response(merchant)


@router.get("/addresses", response_model=list[SavedAddressResponse])
def list_addresses(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> list[SavedAddressResponse]:
    require_module(ctx, "settings")
    rows = _profile.list_saved_addresses(db, ctx)
    return [
        SavedAddressResponse(
            id=r.id, label=r.label, address_type=r.address_type, formatted=r.formatted, is_default=r.is_default
        )
        for r in rows
    ]


@router.post("/addresses", response_model=SavedAddressResponse)
def create_address(
    body: SavedAddressCreateRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> SavedAddressResponse:
    require_module(ctx, "settings")
    r = _profile.create_saved_address(db, ctx, **body.model_dump())
    return SavedAddressResponse(
        id=r.id, label=r.label, address_type=r.address_type, formatted=r.formatted, is_default=r.is_default
    )


@router.get("/recipients", response_model=list[RecipientResponse])
def list_recipients(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> list[RecipientResponse]:
    require_module(ctx, "settings")
    rows = _profile.list_recipients(db, ctx)
    return [
        RecipientResponse(id=r.id, name=r.name, email=r.email, phone=r.phone, company=r.company) for r in rows
    ]


@router.post("/recipients", response_model=RecipientResponse)
def create_recipient(
    body: RecipientCreateRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> RecipientResponse:
    require_module(ctx, "settings")
    r = _profile.create_recipient(db, ctx, **body.model_dump())
    return RecipientResponse(id=r.id, name=r.name, email=r.email, phone=r.phone, company=r.company)


@router.get("/contacts", response_model=list[MerchantContactResponse])
def list_contacts(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> list[MerchantContactResponse]:
    require_module(ctx, "users")
    return [MerchantContactResponse(**row) for row in _contacts.list_contacts(db, ctx)]


@router.post("/contacts", response_model=MerchantContactResponse, status_code=201)
def create_contact(
    body: MerchantContactCreateRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> MerchantContactResponse:
    require_module(ctx, "users")
    try:
        row = _contacts.create_contact(db, ctx, body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return MerchantContactResponse(**row)


@router.patch("/contacts/{contact_id}", response_model=MerchantContactResponse)
def update_contact(
    contact_id: str,
    body: MerchantContactUpdateRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> MerchantContactResponse:
    require_module(ctx, "users")
    try:
        row = _contacts.update_contact(
            db, ctx, contact_id, body.model_dump(exclude_unset=True)
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="contact_not_found") from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return MerchantContactResponse(**row)


@router.delete("/contacts/{contact_id}", status_code=204)
def delete_contact(
    contact_id: str,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> None:
    require_module(ctx, "users")
    try:
        _contacts.delete_contact(db, ctx, contact_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="contact_not_found") from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/team/overview")
def team_overview(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "users")
    return _team.overview(db, ctx)


@router.get("/team/activity")
def team_activity(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
    limit: int = Query(50, le=200),
):
    require_module(ctx, "users")
    return _team.activity_log(db, ctx, limit=limit)


@router.get("/team/roles")
def team_roles(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
):
    require_module(ctx, "users")
    return _team.roles_and_permissions()


@router.get("/team/two-factor")
def team_two_factor_get(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
):
    require_module(ctx, "users")
    return _team.two_factor_status(ctx)


@router.patch("/team/two-factor")
def team_two_factor_patch(
    body: MerchantTwoFactorRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "users")
    return _team.update_two_factor(db, ctx, enabled=body.enabled, method=body.method)


@router.get("/team", response_model=list[TeamMemberResponse])
def list_team(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> list[TeamMemberResponse]:
    require_module(ctx, "users")
    members = _team.list_members(db, ctx)
    return [
        TeamMemberResponse(id=m.id, email=m.email, role=m.role, is_active=m.is_active, created_at=m.created_at)
        for m in members
    ]


@router.post("/team/invite", response_model=TeamMemberResponse)
def invite_team_member(
    body: TeamInviteRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> TeamMemberResponse:
    require_module(ctx, "users")
    try:
        m = _team.invite_member(db, ctx, settings, email=body.email, role=body.role)
    except ValueError as exc:
        if str(exc) == "clerk_not_configured":
            raise HTTPException(status_code=503, detail="clerk_not_configured") from exc
        raise
    _contacts.sync_team_contacts(db, ctx.merchant)
    return TeamMemberResponse(id=m.id, email=m.email, role=m.role, is_active=m.is_active, created_at=m.created_at)


@router.delete("/team/{user_id}", status_code=204)
def remove_team_member(
    user_id: str,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> None:
    require_module(ctx, "users")
    try:
        _team.remove_member(db, ctx, user_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="team_member_not_found") from None
    except PermissionError as exc:
        _handle_permission(exc)
    _contacts.sync_team_contacts(db, ctx.merchant)


@router.patch("/team/{user_id}/role", response_model=TeamMemberResponse)
def update_team_role(
    user_id: str,
    body: TeamRoleUpdateRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> TeamMemberResponse:
    require_module(ctx, "users")
    try:
        m = _team.update_role(db, ctx, user_id, body.role)
        _contacts.sync_team_contacts(db, ctx.merchant)
        return TeamMemberResponse(id=m.id, email=m.email, role=m.role, is_active=m.is_active, created_at=m.created_at)
    except LookupError:
        raise HTTPException(status_code=404, detail="team_member_not_found") from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

