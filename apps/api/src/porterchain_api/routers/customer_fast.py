"""Customer fast-book API: guest checkout, tracking-page actions, Send again, email preferences.

All routes are public. Guest checkout is defended by honeypot + fill-time + disposable-email +
Redis rate windows (customer_fast.guard). Everything else needs a signed, purpose-bound link.
"""

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from porterchain_api.auth.claims import ClerkClaims
from porterchain_api.auth.clerk import get_clerk_claims
from porterchain_api.config import Settings, get_settings
from porterchain_api.customer_fast import service as fast
from porterchain_api.db import get_db

router = APIRouter(prefix="/v1", tags=["customer-fast"])


class ExpressCheckoutRequest(BaseModel):
    quote_id: str = Field(min_length=8, max_length=64)
    name: str | None = Field(default=None, max_length=120)
    email: str = Field(min_length=3, max_length=320)
    phone: str = Field(min_length=7, max_length=32)
    terms_accepted: bool = False
    privacy_accepted: bool = False
    dangerous_goods_confirmed: bool = False
    marketing_opt_in: bool = False
    anonymous_session_id: str | None = Field(default=None, max_length=64)
    #: Honeypot: hidden input humans never fill.
    website: str | None = Field(default=None, max_length=200)
    form_elapsed_ms: int | None = Field(default=None, ge=0)
    locale: str | None = Field(default=None, pattern="^(en|fr)$")


class RatingRequest(BaseModel):
    score: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=1000)


class SendAgainRequest(BaseModel):
    token: str = Field(min_length=10, max_length=600)


class PreferencesRequest(BaseModel):
    token: str = Field(min_length=10, max_length=600)
    tracking: bool | None = None
    reorder: bool | None = None
    marketing: bool | None = None


class TokenRequest(BaseModel):
    token: str = Field(min_length=10, max_length=600)


def _ip(request: Request) -> str | None:
    from porterchain_api.platform.client_ip import client_ip

    return client_ip(request, default="") or None


def _call(fn, *args, **kwargs) -> Any:
    try:
        return fn(*args, **kwargs)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail={"code": "order_not_found", "message": fast.ERROR_COPY["order_not_found"]}) from exc
    except ValueError as exc:
        code = str(exc)
        if code not in fast.ERROR_STATUS:
            raise HTTPException(status_code=400, detail={"code": "invalid", "message": "That did not work. Try again."}) from exc
        raise HTTPException(status_code=fast.ERROR_STATUS[code], detail={"code": code, "message": fast.ERROR_COPY[code]}) from exc


@router.post("/express/checkout")
def post_express_checkout(
    body: ExpressCheckoutRequest,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """Guest checkout: no account. Returns a Stripe Checkout URL (cards, Apple Pay, Google Pay)."""
    return _call(fast.express_checkout, db, settings, body, ip=_ip(request))


@router.get("/express/confirmation")
def get_express_confirmation(
    quote_id: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """Success page poll: order summary + the signed tracking link once paid."""
    return fast.express_confirmation(db, settings, quote_id)


@router.get("/delivery-manage/{tracking_number}/actions")
def get_order_actions(
    tracking_number: str,
    x_manage_token: str = Header(...),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    return _call(fast.order_actions, db, settings, tracking_number, x_manage_token)


@router.post("/delivery-manage/{tracking_number}/cancel")
def post_cancel(
    tracking_number: str,
    x_manage_token: str = Header(...),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    return _call(fast.cancel_order, db, settings, tracking_number, x_manage_token)


@router.post("/delivery-manage/{tracking_number}/rating")
def post_rating(
    tracking_number: str,
    body: RatingRequest,
    x_manage_token: str = Header(...),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    return _call(fast.rate_order, db, settings, tracking_number, x_manage_token, body.score, body.comment)


@router.post("/express/send-again")
def post_send_again(
    body: SendAgainRequest,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    return _call(fast.send_again, db, settings, body.token, ip=_ip(request))


@router.post("/email-preferences/read")
def post_preferences_read(
    body: TokenRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    # POST so the token stays out of access logs / referrers.
    return _call(fast.get_preferences, db, settings, body.token)


@router.post("/email-preferences")
def post_preferences(
    body: PreferencesRequest,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    prefs = {k: v for k, v in body.model_dump().items() if k != "token" and v is not None}
    return _call(fast.set_preferences, db, settings, body.token, prefs, ip=_ip(request))


@router.post("/email-preferences/unsubscribe")
def post_unsubscribe(
    body: TokenRequest,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    return _call(fast.unsubscribe_all, db, settings, body.token, ip=_ip(request))


@router.post("/email-preferences/delete-request")
def post_delete_request(
    body: TokenRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    return _call(fast.request_deletion, db, settings, body.token)


@router.get("/customers/me/track-link/{tracking_number}")
def get_my_track_link(
    tracking_number: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    claims: ClerkClaims = Depends(get_clerk_claims),
) -> dict[str, Any]:
    """Signed-in customers open the same single tracking page, with actions unlocked."""
    from porterchain_api.auth.customer import require_customer

    customer = require_customer(db, claims, settings)
    url = fast.owner_track_url(db, settings, customer.id, tracking_number)
    if url is None:
        raise HTTPException(status_code=404, detail="order_not_found")
    return {"url": url}


# --------------------------------------------------------------------------- signed-in account
# Orders, address book, autofill, report a problem. Clerk session; the customers row is created
# on first call (no onboarding step).


class ProblemRequest(BaseModel):
    kind: str = Field(pattern="^(late|damaged|missing|wrong_address|return|billing|other)$")
    details: str | None = Field(default=None, max_length=2000)


class SignedProblemRequest(ProblemRequest):
    token: str = Field(min_length=10, max_length=600)


class AddressRequest(BaseModel):
    formatted: str = Field(min_length=5, max_length=512)
    label: str | None = Field(default=None, max_length=64)
    postal: str | None = Field(default=None, max_length=16)
    lat: float | None = None
    lng: float | None = None
    place_id: str | None = Field(default=None, max_length=255)
    contact_name: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=32)


def _me(db: Session, claims: ClerkClaims, settings: Settings):
    from porterchain_api.customer_fast.account import ensure_customer

    return ensure_customer(db, claims, settings)


@router.get("/customers/me/deliveries")
def get_my_orders(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    claims: ClerkClaims = Depends(get_clerk_claims),
) -> dict[str, Any]:
    from porterchain_api.customer_fast import account

    return account.my_orders(db, settings, _me(db, claims, settings))


@router.get("/customers/me/addresses")
def get_my_addresses(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    claims: ClerkClaims = Depends(get_clerk_claims),
) -> list[dict[str, Any]]:
    from porterchain_api.customer_fast import account

    return account.list_addresses(db, _me(db, claims, settings))


@router.get("/customers/me/address-suggestions")
def get_my_address_suggestions(
    q: str | None = None,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    claims: ClerkClaims = Depends(get_clerk_claims),
) -> list[dict[str, Any]]:
    from porterchain_api.customer_fast import account

    return account.suggestions(db, _me(db, claims, settings), q)


@router.post("/customers/me/addresses")
def post_my_address(
    body: AddressRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    claims: ClerkClaims = Depends(get_clerk_claims),
) -> dict[str, Any]:
    from porterchain_api.customer_fast import account

    return _call(account.save_address, db, _me(db, claims, settings), body.model_dump())


@router.delete("/customers/me/addresses/{address_id}")
def delete_my_address(
    address_id: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    claims: ClerkClaims = Depends(get_clerk_claims),
) -> dict[str, Any]:
    from porterchain_api.customer_fast import account

    _call(account.delete_address, db, _me(db, claims, settings), address_id)
    return {"ok": True}


@router.post("/customers/me/orders/{tracking_number}/problem")
def post_my_problem(
    tracking_number: str,
    body: ProblemRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    claims: ClerkClaims = Depends(get_clerk_claims),
) -> dict[str, Any]:
    from porterchain_api.customer_fast import account

    return _call(account.report_problem_owner, db, _me(db, claims, settings), tracking_number, body.kind, body.details)


@router.post("/delivery-manage/{tracking_number}/problem")
def post_signed_problem(
    tracking_number: str,
    body: SignedProblemRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """Report a problem / request a return from the tracking page (signed link, no account)."""
    from porterchain_api.customer_fast import account

    return _call(account.report_problem_signed, db, settings, tracking_number, body.token, body.kind, body.details)


@router.get("/customers/me/preferences-link")
def get_my_preferences_link(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    claims: ClerkClaims = Depends(get_clerk_claims),
) -> dict[str, Any]:
    """Signed-in Account page opens the same email-preferences page the emails link to."""
    return {"url": fast.preferences_url(settings, _me(db, claims, settings))}
