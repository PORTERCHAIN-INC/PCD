"""BF — memberships list for the seat switcher; X-Merchant-Id is the only selector."""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from fastapi import HTTPException

from porterchain_api.auth.claims import ClerkClaims
from porterchain_api.auth.merchant import get_merchant_context, get_merchant_seats
from porterchain_api.config import Settings
from porterchain_api.domain.merchant_states import MerchantRole, MerchantStatus
from porterchain_api.merchant_models import Merchant, MerchantUser
from porterchain_api.notification_engine.principal import _resolve_merchant_recipient
from porterchain_api.routers.merchant.profile_team import list_memberships


def _settings() -> Settings:
    return Settings(app_env="local", clerk_dev_bypass=False)


def _claims(clerk_id: str, email: str) -> ClerkClaims:
    return ClerkClaims(clerk_user_id=clerk_id, email=email, clerk_app="merchant")


def _company(
    db,
    *,
    clerk_id: str,
    email: str,
    name: str,
    status: str = MerchantStatus.ACTIVE.value,
    role: str = MerchantRole.OWNER.value,
) -> Merchant:
    merchant = Merchant(
        company_name=name,
        email=f"{uuid4().hex[:8]}@bf.test",
        status=status,
        payment_terms="NET_30",
    )
    db.add(merchant)
    db.flush()
    db.add(
        MerchantUser(
            merchant_id=merchant.id,
            clerk_user_id=clerk_id,
            email=email,
            role=role,
            is_active=True,
        )
    )
    db.commit()
    return merchant


def _two_companies(db) -> tuple[str, str, Merchant, Merchant]:
    """One working company and one suspended company on the same Clerk seat."""
    clerk_id = f"user_{uuid4().hex[:12]}"
    email = f"{clerk_id}@bf.test"
    working = _company(db, clerk_id=clerk_id, email=email, name="Working Co")
    stopped = _company(
        db,
        clerk_id=clerk_id,
        email=email,
        name="Stopped Co",
        status=MerchantStatus.SUSPENDED.value,
        role=MerchantRole.FINANCE.value,
    )
    return clerk_id, email, working, stopped


def _seats(db, clerk_id: str, email: str, selected: str | None = None):
    return get_merchant_seats(
        claims=_claims(clerk_id, email),
        db=db,
        settings=_settings(),
        x_merchant_id=selected,
    )


def test_memberships_name_every_company_in_english(db) -> None:
    clerk_id, email, working, stopped = _two_companies(db)

    body = list_memberships(_seats(db, clerk_id, email, working.id), db=db)
    rows = {m["company_name"]: m for m in body["memberships"]}

    assert set(rows) == {"Working Co", "Stopped Co"}
    assert rows["Working Co"]["can_open"] is True
    assert rows["Working Co"]["is_current"] is True
    assert rows["Working Co"]["role_label"] == "Owner"
    assert rows["Stopped Co"]["can_open"] is False
    assert rows["Stopped Co"]["status_label"] == "Suspended"
    assert rows["Stopped Co"]["role_label"] == "Accounting"
    # Openable companies are listed first.
    assert body["memberships"][0]["company_name"] == "Working Co"
    for row in body["memberships"]:
        assert "merchant_" not in row["role_label"]


def test_switcher_survives_a_suspended_selection(db) -> None:
    """The whole point of BF: you can still switch away from a dead company."""
    clerk_id, email, working, stopped = _two_companies(db)

    # The portal gate refuses the suspended company (AZ) ...
    with pytest.raises(HTTPException) as exc:
        get_merchant_context(
            claims=_claims(clerk_id, email),
            db=db,
            settings=_settings(),
            x_merchant_id=stopped.id,
        )
    assert exc.value.status_code == 403
    assert exc.value.detail == "merchant_suspended"

    # ... but memberships still list both, so the switcher can move them.
    body = list_memberships(_seats(db, clerk_id, email, stopped.id), db=db)
    names = [m["company_name"] for m in body["memberships"]]
    assert names == ["Working Co", "Stopped Co"]
    assert [m["merchant_id"] for m in body["memberships"] if m["can_open"]] == [working.id]


def test_stale_company_header_opens_this_users_seat(db) -> None:
    """A leftover X-Merchant-Id from another sign-in must not blank the portal."""
    clerk_id, email, working, _stopped = _two_companies(db)
    other = Merchant(
        company_name="Someone Else Co",
        email=f"{uuid4().hex[:8]}@bf.test",
        status=MerchantStatus.ACTIVE.value,
    )
    db.add(other)
    db.commit()

    ctx = get_merchant_context(
        claims=_claims(clerk_id, email),
        db=db,
        settings=_settings(),
        x_merchant_id=other.id,
    )
    assert ctx.merchant.id == working.id
    assert ctx.role == MerchantRole.OWNER


def test_a_company_you_have_no_seat_on_is_refused(db) -> None:
    clerk_id, email, _working, _stopped = _two_companies(db)
    other = Merchant(
        company_name="Someone Else Co",
        email=f"{uuid4().hex[:8]}@bf.test",
        status=MerchantStatus.ACTIVE.value,
    )
    db.add(other)
    db.commit()

    with pytest.raises(HTTPException) as exc:
        _seats(db, clerk_id, email, other.id)
    assert exc.value.status_code == 403
    assert exc.value.detail == "merchant_membership_not_found"


def test_seat_turned_off_leaves_the_switcher(db) -> None:
    clerk_id, email, working, stopped = _two_companies(db)
    seat = (
        db.query(MerchantUser)
        .filter(MerchantUser.clerk_user_id == clerk_id, MerchantUser.merchant_id == stopped.id)
        .one()
    )
    seat.is_active = False
    db.commit()

    body = list_memberships(_seats(db, clerk_id, email, working.id), db=db)
    assert [m["merchant_id"] for m in body["memberships"]] == [working.id]


def test_inbox_and_websocket_share_one_company_selector(db) -> None:
    clerk_id, _email, working, _stopped = _two_companies(db)
    settings = _settings()

    inbox = _resolve_merchant_recipient(db, settings, clerk_id, working.id)
    assert inbox is not None and inbox.user_id == working.id

    from porterchain_api.notification_engine.principal import resolve_notification_ws_user

    # The websocket takes the same company id under the same name — no org_id.
    import inspect

    params = inspect.signature(resolve_notification_ws_user).parameters
    assert "merchant_id" in params
    assert "org_id" not in params

    from porterchain_api.notification_engine.principal import get_notification_user

    inbox_params = inspect.signature(get_notification_user).parameters
    assert "x_merchant_id" in inbox_params
    assert "x_merchant_org_id" not in inbox_params


def test_suspended_company_has_no_inbox(db) -> None:
    clerk_id, _email, working, stopped = _two_companies(db)
    settings = _settings()

    assert _resolve_merchant_recipient(db, settings, clerk_id, stopped.id) is None
    # With no selector it falls back to the company that still works.
    fallback = _resolve_merchant_recipient(db, settings, clerk_id, None)
    assert fallback is not None and fallback.user_id == working.id


def test_websocket_rejects_a_company_without_a_seat(db) -> None:
    clerk_id, _email, _working, _stopped = _two_companies(db)
    other = Merchant(
        company_name="Not Yours Co",
        email=f"{uuid4().hex[:8]}@bf.test",
        status=MerchantStatus.ACTIVE.value,
    )
    db.add(other)
    db.commit()

    assert _resolve_merchant_recipient(db, _settings(), clerk_id, other.id) is None
    assert asyncio.run(_no_ws_user(other.id)) is None


async def _no_ws_user(merchant_id: str):
    from porterchain_api.notification_engine.principal import resolve_notification_ws_user

    return await resolve_notification_ws_user("", merchant_id=merchant_id)
