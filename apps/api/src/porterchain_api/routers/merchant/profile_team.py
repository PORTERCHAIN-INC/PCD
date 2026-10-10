"""merchant routes — profile_team."""

from collections.abc import Callable
from typing import TypeVar

from porterchain_api.merchant_engine.team_service import (
    list_switcher_memberships,
    serialize_member,
)
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
    MerchantSeats,
    MerchantTwoFactorRequest,
    Query,
    RecipientCreateRequest,
    RecipientResponse,
    RecipientUpdateRequest,
    SavedAddressCreateRequest,
    SavedAddressResponse,
    SavedAddressUpdateRequest,
    Session,
    TeamInviteRequest,
    TeamMemberResponse,
    TeamMemberUpdateRequest,
    TeamRoleUpdateRequest,
    _contacts,
    _handle_permission,
    _profile,
    _profile_response,
    _recipient_out,
    _saved_address_out,
    _team,
    get_db,
    get_merchant_context,
    get_merchant_seats,
    require_module,
    router,
)

T = TypeVar("T")


def _invoke(ctx: MerchantContext, module: str, fn: Callable[..., T], *args: object, **kwargs: object) -> T:
    try:
        require_module(ctx, module)
        return fn(*args, **kwargs)
    except PermissionError as exc:
        _handle_permission(exc)
        raise
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _member_response(user) -> TeamMemberResponse:
    return TeamMemberResponse(**serialize_member(user))


@router.get("/session")
def merchant_session(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> dict:
    """M-25/M-26: active merchant + role modules for portal nav / X-Merchant-Id."""
    return _profile.session_payload(ctx, db)


@router.get("/me")
def merchant_me(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
) -> dict:
    """Seat-only identity: who is signed in, which company, which role. No secrets."""
    return _profile.me_payload(ctx)


@router.get("/memberships")
def list_memberships(
    seats: Annotated[MerchantSeats, Depends(get_merchant_seats)],
    db: Session = Depends(get_db),
) -> dict:
    """Seats for this Clerk user — switch companies with X-Merchant-Id, not Clerk orgs.

    Suspended and closed companies are listed with ``can_open: false`` so the
    switcher still works when the selected company stopped working (BF).
    """
    return list_switcher_memberships(db, seats.seats, seats.selected_merchant_id)


@router.get("/profile", response_model=MerchantProfileResponse)
def get_profile(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> MerchantProfileResponse:
    return _invoke(ctx, "settings", lambda: _profile_response(_profile.get_profile(ctx), db))


@router.patch("/profile", response_model=MerchantProfileResponse)
def update_profile(
    body: MerchantProfileUpdateRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> MerchantProfileResponse:
    merchant = _invoke(ctx, "settings", _profile.update_profile, db, ctx, body)
    return _profile_response(merchant, db)


@router.get("/addresses", response_model=list[SavedAddressResponse])
def list_addresses(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> list[SavedAddressResponse]:
    return _invoke(ctx, "settings", lambda: [_saved_address_out(r) for r in _profile.list_saved_addresses(db, ctx)])


@router.post("/addresses", response_model=SavedAddressResponse)
def create_address(
    body: SavedAddressCreateRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> SavedAddressResponse:
    r = _invoke(ctx, "settings", _profile.create_saved_address, db, ctx, **body.model_dump())
    return _saved_address_out(r)


@router.patch("/addresses/{address_id}", response_model=SavedAddressResponse)
def update_address(
    address_id: str,
    body: SavedAddressUpdateRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> SavedAddressResponse:
    r = _invoke(ctx, "settings", _profile.update_saved_address, db, ctx, address_id, body)
    return _saved_address_out(r)


@router.post("/addresses/{address_id}/default", response_model=SavedAddressResponse)
def set_default_address(
    address_id: str,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> SavedAddressResponse:
    r = _invoke(ctx, "settings", _profile.set_default_saved_address, db, ctx, address_id)
    return _saved_address_out(r)


@router.get("/recipients", response_model=list[RecipientResponse])
def list_recipients(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> list[RecipientResponse]:
    return _invoke(ctx, "settings", lambda: [_recipient_out(r) for r in _profile.list_recipients(db, ctx)])


@router.post("/recipients", response_model=RecipientResponse)
def create_recipient(
    body: RecipientCreateRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> RecipientResponse:
    r = _invoke(ctx, "settings", _profile.create_recipient, db, ctx, **body.model_dump())
    return _recipient_out(r)


@router.patch("/recipients/{recipient_id}", response_model=RecipientResponse)
def update_recipient(
    recipient_id: str,
    body: RecipientUpdateRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> RecipientResponse:
    r = _invoke(ctx, "settings", _profile.update_recipient, db, ctx, recipient_id, body)
    return _recipient_out(r)


@router.delete("/recipients/{recipient_id}", status_code=204)
def delete_recipient(
    recipient_id: str,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> None:
    return _invoke(ctx, "settings", _profile.delete_recipient, db, ctx, recipient_id)


@router.get("/contacts", response_model=list[MerchantContactResponse])
def list_contacts(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> list[MerchantContactResponse]:
    return _invoke(ctx, "users", lambda: [MerchantContactResponse(**row) for row in _contacts.list_contacts(db, ctx)])


@router.post("/contacts", response_model=MerchantContactResponse, status_code=201)
def create_contact(
    body: MerchantContactCreateRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> MerchantContactResponse:
    row = _invoke(ctx, "users", _contacts.create_contact, db, ctx, body.model_dump())
    return MerchantContactResponse(**row)


@router.patch("/contacts/{contact_id}", response_model=MerchantContactResponse)
def update_contact(
    contact_id: str,
    body: MerchantContactUpdateRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> MerchantContactResponse:
    row = _invoke(
        ctx, "users", _contacts.update_contact, db, ctx, contact_id, body.model_dump(exclude_unset=True)
    )
    return MerchantContactResponse(**row)


@router.delete("/contacts/{contact_id}", status_code=204)
def delete_contact(
    contact_id: str,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> None:
    return _invoke(ctx, "users", _contacts.delete_contact, db, ctx, contact_id)


@router.get("/team/overview")
def team_overview(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    return _invoke(ctx, "users", _team.overview, db, ctx)


@router.get("/team/activity")
def team_activity(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
    limit: int = Query(50, le=200),
):
    return _invoke(ctx, "users", _team.activity_log, db, ctx, limit=limit)


@router.get("/team/roles")
def team_roles(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
):
    return _invoke(ctx, "users", _team.roles_and_permissions)


@router.get("/team/two-factor")
def team_two_factor_get(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
):
    return _invoke(ctx, "users", _team.two_factor_status, ctx)


@router.patch("/team/two-factor")
def team_two_factor_patch(
    body: MerchantTwoFactorRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    return _invoke(ctx, "users", _team.update_two_factor, db, ctx, enabled=body.enabled, method=body.method)


@router.get("/team", response_model=list[TeamMemberResponse])
def list_team(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> list[TeamMemberResponse]:
    return _invoke(ctx, "users", lambda: [_member_response(m) for m in _team.list_seats(db, ctx)])


@router.post("/team/seats", response_model=TeamMemberResponse, status_code=201)
def add_team_seat(
    body: TeamInviteRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> TeamMemberResponse:
    """Reserve a teammate seat by email. Teammate self-signs-up on Platform; no Clerk invite."""
    m = _invoke(ctx, "users", _team.add_seat, db, ctx, email=body.email, role=body.role)
    return _member_response(m)


@router.delete("/team/{user_id}", status_code=204)
def remove_team_member(
    user_id: str,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> None:
    return _invoke(ctx, "users", _team.remove_member, db, ctx, user_id)


@router.patch("/team/{user_id}", response_model=TeamMemberResponse)
def update_team_member(
    user_id: str,
    body: TeamMemberUpdateRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> TeamMemberResponse:
    m = _invoke(ctx, "users", _team.update_member, db, ctx, user_id, role=body.role, is_active=body.is_active)
    return _member_response(m)


@router.patch("/team/{user_id}/role", response_model=TeamMemberResponse)
def update_team_role(
    user_id: str,
    body: TeamRoleUpdateRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> TeamMemberResponse:
    m = _invoke(ctx, "users", _team.update_member, db, ctx, user_id, role=body.role, is_active=body.is_active)
    return _member_response(m)
