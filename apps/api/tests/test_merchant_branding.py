"""Logo on session, merchant track, and public track — http(s) only."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from porterchain_api.booking_engine.numbers import generate_order_number, generate_tracking_number
from porterchain_api.booking_engine.tracking_service import TrackingService
from porterchain_api.domain.merchant_states import MerchantRole, MerchantStatus
from porterchain_api.domain.states import OrderState
from porterchain_api.merchant_engine.organization_sync import (
    branding_logo_url,
    public_shipper_branding,
    sanitize_logo_url,
)
from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_api.merchant_engine.settings_service import MerchantSettingsService
from porterchain_api.merchant_engine.tracking_service import MerchantTrackingService
from porterchain_api.merchant_models import Merchant, MerchantUser
from porterchain_api.booking_models import Order


def test_sanitize_logo_url_https_only() -> None:
    assert sanitize_logo_url("https://cdn.example.com/logo.png") == "https://cdn.example.com/logo.png"
    assert sanitize_logo_url("") is None
    assert sanitize_logo_url(None) is None
    with pytest.raises(ValueError, match="logo_url_invalid"):
        sanitize_logo_url("javascript:alert(1)")
    with pytest.raises(ValueError, match="logo_url_invalid"):
        sanitize_logo_url("data:image/png;base64,aaaa")


def _ctx(db, *, logo: str | None = "https://cdn.example.com/acme.png") -> MerchantContext:
    suffix = uuid4().hex[:8]
    profile = {
        "settings": {
            "branding": {
                "logo_url": logo,
                "tracking_page_message": "Your order from Acme",
            }
        }
    }
    merchant = Merchant(
        company_name=f"Acme {suffix}",
        email=f"acme-{suffix}@test.local",
        status=MerchantStatus.ACTIVE.value,
        profile=profile,
    )
    db.add(merchant)
    db.flush()
    user = MerchantUser(
        merchant_id=merchant.id,
        clerk_user_id=f"clerk_{suffix}",
        email=f"owner-{suffix}@test.local",
        role=MerchantRole.OWNER.value,
    )
    db.add(user)
    db.flush()
    return MerchantContext(merchant=merchant, user=user, role=MerchantRole.OWNER)


def test_session_and_track_include_logo(db, settings) -> None:
    ctx = _ctx(db)
    db.commit()
    assert branding_logo_url(ctx.merchant) == "https://cdn.example.com/acme.png"
    brand = public_shipper_branding(ctx.merchant)
    assert brand["company_name"].startswith("Acme")
    assert brand["logo_url"] == "https://cdn.example.com/acme.png"
    assert brand["tracking_page_message"] == "Your order from Acme"

    order = Order(
        order_number=generate_order_number(),
        tracking_number=generate_tracking_number(),
        state=OrderState.IN_TRANSIT.value,
        merchant_id=ctx.merchant.id,
        amount_cents=1000,
        currency="cad",
        pickup={"formatted": "1 King", "lat": 43.64, "lng": -79.38},
        dropoff={"formatted": "100 Queen", "lat": 43.65, "lng": -79.38},
        scheduled_at=datetime.now(UTC),
    )
    db.add(order)
    db.commit()

    live = MerchantTrackingService().live_tracking(db, settings, ctx, order.id)
    assert live["branding"]["logo_url"] == "https://cdn.example.com/acme.png"
    assert live["branding"]["company_name"] == ctx.merchant.company_name


def test_public_track_includes_shipper_logo(db) -> None:
    ctx = _ctx(db)
    order = Order(
        order_number=generate_order_number(),
        tracking_number=generate_tracking_number(),
        state=OrderState.IN_TRANSIT.value,
        merchant_id=ctx.merchant.id,
        amount_cents=1000,
        currency="cad",
        pickup={"formatted": "1 King St W, Toronto", "lat": 43.64, "lng": -79.38},
        dropoff={"formatted": "100 Queen St W, Toronto", "lat": 43.65, "lng": -79.38},
        scheduled_at=datetime.now(UTC),
    )
    db.add(order)
    db.commit()

    public = TrackingService().get_order_response_by_tracking(db, order.tracking_number)
    assert public is not None
    assert public.logo_url == "https://cdn.example.com/acme.png"
    assert public.company_name == ctx.merchant.company_name
    assert public.tracking_page_message == "Your order from Acme"


def test_branding_save_rejects_javascript(db) -> None:
    ctx = _ctx(db, logo=None)
    with pytest.raises(ValueError, match="logo_url_invalid"):
        MerchantSettingsService().update_branding(
            db, ctx, {"logo_url": "javascript:alert(1)"}
        )
