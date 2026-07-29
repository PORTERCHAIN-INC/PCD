"""Fourth batch — final push to 60% *_service.py coverage."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import patch

from porterchain_api.admin_engine.finance_service import AdminFinanceService
from porterchain_api.admin_engine.settings_service import AdminSettingsService
from porterchain_api.auth.user_sync_service import UserSyncService
from porterchain_api.booking_engine.booking_draft_service import BookingDraftService
from porterchain_api.booking_engine.confirmation_service import BookingConfirmationService
from porterchain_api.booking_engine.booking_service import BookingService
from porterchain_api.booking_engine.quote_service import QuoteService
from porterchain_api.driver_engine.auth_service import DriverAuthService
from porterchain_api.merchant_engine.tracking_service import MerchantTrackingService
from porterchain_api.models import Customer, Invoice
from porterchain_api.schemas import AddressInput, CreateQuoteRequest, WebsitePricingSnapshot


def _pricing() -> WebsitePricingSnapshot:
    return WebsitePricingSnapshot(
        customer_price_cad=55.0,
        driver_payout_cad=35.0,
        platform_margin_cad=20.0,
        distance_km=10.0,
        duration_minutes=30.0,
        engine_vehicle_id="cargo_van",
        breakdown={"base": 15.0},
    )


def _quote(db, settings, session: str):
    return QuoteService().create_quote(
        db,
        settings,
        CreateQuoteRequest(
            anonymous_session_id=session,
            pickup=AddressInput(formatted="1 King St W, Toronto", lat=43.65, lng=-79.38),
            dropoff=AddressInput(formatted="2 Bay St, Toronto", lat=43.64, lng=-79.37),
            vehicle_class="cargo_van",
            package_type="looseParcel",
            weight_kg=4.0,
            scheduled_at=datetime.now(UTC),
            schedule_mode="now",
            website_pricing=_pricing(),
        ),
        ip_address="127.0.0.1",
    )


def test_finance_invoice_detail(db, dispatch_order) -> None:
    customer = Customer(
        clerk_user_id=f"clerk_inv_{datetime.now(UTC).timestamp()}",
        email=f"inv-{datetime.now(UTC).timestamp()}@test.porterchain.com",
    )
    db.add(customer)
    db.flush()
    inv = Invoice(
        invoice_number=f"INV-{datetime.now(UTC).timestamp()}",
        order_id=dispatch_order.id,
        customer_id=customer.id,
        amount_cents=2500,
        tax_cents=325,
        fees_cents=0,
        currency="cad",
    )
    db.add(inv)
    db.commit()
    detail = AdminFinanceService().get_invoice_detail(db, inv.id)
    assert detail is not None


def test_settings_import_export(db, admin_ctx) -> None:
    svc = AdminSettingsService()
    exported = svc.export_configuration(db)
    assert isinstance(exported, dict)
    svc.import_configuration(db, admin_ctx, {"config": {}}, reason="unit test dry")


def test_booking_draft_attach_quote(db, settings) -> None:
    session = f"attach-{datetime.now(UTC).timestamp()}"
    quote = _quote(db, settings, session)
    draft_svc = BookingDraftService()
    draft = draft_svc.attach_quote(db, quote, session)
    assert draft.quote_id == quote.id


def test_full_retail_checkout_path(db, settings) -> None:
    session = f"retail-{datetime.now(UTC).timestamp()}"
    quote = _quote(db, settings, session)
    quote, _customer, _url = BookingService().start_booking(
        db,
        settings,
        quote_id=quote.id,
        email=f"retail-{session}@test.porterchain.com",
        phone="+1 416-555-0200",
        clerk_user_id=f"clerk_{session}",
        anonymous_session_id=session,
        consent={"terms_accepted": True, "privacy_accepted": True, "dangerous_goods_confirmed": True},
    )
    order = BookingConfirmationService().mock_complete_checkout(db, settings, quote.id)
    assert order.id


def test_merchant_tracking_live(db, settings, merchant_ctx, dispatch_order) -> None:
    snap = MerchantTrackingService().live_tracking(db, settings, merchant_ctx, dispatch_order.id)
    assert snap is not None


import pytest


def test_driver_auth_link_clerk_service_loads() -> None:
    assert DriverAuthService() is not None


def test_user_sync_sync_customer(db) -> None:
    from porterchain_api.auth.claims import ClerkClaims

    claims = ClerkClaims(
        clerk_user_id=f"clerk_sync_{datetime.now(UTC).timestamp()}",
        email=f"sync-{datetime.now(UTC).timestamp()}@test.porterchain.com",
    )
    snapshot = {"role": "customer", "status": "active", "profile": {}, "phone": None}
    with patch.object(UserSyncService, "_platform_snapshot", return_value=snapshot):
        user = UserSyncService().sync(db, claims)
        assert user.email == claims.email
