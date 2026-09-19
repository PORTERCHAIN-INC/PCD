"""Booking draft API — persistent checkout lifecycle."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from porterchain_api.auth.clerk import get_optional_clerk_user_id
from porterchain_api.booking_engine.booking_draft_service import BookingDraftService
from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db
from porterchain_api.schemas import (
    BookingDraftAuditItem,
    BookingDraftDetailResponse,
    BookingDraftResponse,
    CreateBookingDraftRequest,
    UpdateBookingDraftRequest,
)

router = APIRouter(prefix="/v1/booking-drafts", tags=["booking-drafts"])
_drafts = BookingDraftService()


def _continue_url(draft_id: str, quote_id: str | None, settings: Settings) -> str | None:
    if not quote_id:
        return None
    base = settings.retail_checkout_cancel_url.rsplit("?", 1)[0]
    return f"{base}?quote_id={quote_id}&draft_id={draft_id}"


def _draft_response(
    db: Session, draft, settings: Settings, *, include_audits: bool = False
) -> BookingDraftResponse | BookingDraftDetailResponse:
    data = _drafts.draft_to_dict(db, draft)
    base = BookingDraftResponse(
        **{k: data[k] for k in BookingDraftResponse.model_fields if k in data},
        continue_url=_continue_url(draft.id, draft.quote_id, settings),
    )
    if not include_audits:
        return base
    audits = [
        BookingDraftAuditItem(
            event_label=a.event_label,
            from_state=a.from_state,
            to_state=a.to_state,
            actor_type=a.actor_type,
            actor_id=a.actor_id,
            occurred_at=a.occurred_at,
            payload=a.payload,
        )
        for a in draft.audits
    ]
    return BookingDraftDetailResponse(
        **base.model_dump(),
        customer_email=data.get("customer_email"),
        audits=audits,
    )


def _access_denied(exc: PermissionError) -> HTTPException:
    return HTTPException(status_code=403, detail=str(exc))


@router.post("", response_model=BookingDraftResponse)
def create_booking_draft(
    body: CreateBookingDraftRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> BookingDraftResponse:
    if not body.session_id.strip():
        raise HTTPException(status_code=400, detail="session_id_required")
    from porterchain_api.admin_engine.platform_settings import booking_self_service

    if not booking_self_service(db):
        raise HTTPException(status_code=403, detail="booking_self_service_disabled")
    draft = _drafts.create_or_update_draft(db, settings, body)
    return _draft_response(db, draft, settings)


@router.get("/active", response_model=BookingDraftResponse | None)
def get_active_booking_draft(
    session_id: str | None = Query(None),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    clerk_user_id: Annotated[str | None, Depends(get_optional_clerk_user_id)] = None,
) -> BookingDraftResponse | None:
    """Restore the latest active booking draft for a visitor or authenticated customer."""
    if not session_id and not clerk_user_id:
        raise HTTPException(status_code=400, detail="session_or_auth_required")
    try:
        draft = _drafts.restore_active(db, session_id=session_id, clerk_user_id=clerk_user_id)
    except LookupError:
        return None
    return _draft_response(db, draft, settings)


@router.get("/{draft_id}", response_model=BookingDraftDetailResponse)
def get_booking_draft(
    draft_id: str,
    session_id: str | None = Query(None),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    clerk_user_id: Annotated[str | None, Depends(get_optional_clerk_user_id)] = None,
) -> BookingDraftDetailResponse:
    draft = _drafts.get_by_id(db, draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="draft_not_found")
    try:
        _drafts.assert_access(db, draft, session_id=session_id, clerk_user_id=clerk_user_id)
    except PermissionError as exc:
        raise _access_denied(exc) from exc
    draft = _drafts.restore_draft(db, draft)
    return _draft_response(db, draft, settings, include_audits=True)


@router.patch("/{draft_id}", response_model=BookingDraftResponse)
def update_booking_draft(
    draft_id: str,
    body: UpdateBookingDraftRequest,
    session_id: str | None = Query(None),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    clerk_user_id: Annotated[str | None, Depends(get_optional_clerk_user_id)] = None,
) -> BookingDraftResponse:
    draft = _drafts.get_by_id(db, draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="draft_not_found")
    try:
        _drafts.assert_access(db, draft, session_id=session_id, clerk_user_id=clerk_user_id)
        draft = _drafts.update_draft(db, settings, draft, body)
    except PermissionError as exc:
        raise _access_denied(exc) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _draft_response(db, draft, settings)


@router.post("/{draft_id}/cancel", response_model=BookingDraftResponse)
def cancel_booking_draft(
    draft_id: str,
    session_id: str | None = Query(None),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    clerk_user_id: Annotated[str | None, Depends(get_optional_clerk_user_id)] = None,
) -> BookingDraftResponse:
    draft = _drafts.get_by_id(db, draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="draft_not_found")
    try:
        _drafts.assert_access(db, draft, session_id=session_id, clerk_user_id=clerk_user_id)
        draft = _drafts.cancel_draft(
            db,
            draft,
            actor_type="customer" if clerk_user_id else "visitor",
            actor_id=clerk_user_id or session_id,
            reason="customer_cancelled",
        )
    except PermissionError as exc:
        raise _access_denied(exc) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _draft_response(db, draft, settings)
