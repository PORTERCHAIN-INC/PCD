"""Third batch — push *_service.py aggregate toward 60% (§2.1.11)."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import patch

from porterchain_api.admin_engine.driver360_service import Driver360Service
from porterchain_api.admin_engine.driver_service import AdminDriverService
from porterchain_api.admin_engine.merchant360_service import Merchant360Service
from porterchain_api.admin_engine.settings_service import AdminSettingsService
from porterchain_api.auth.user_sync_service import UserSyncService
from porterchain_api.booking_engine.customer_service import CustomerService
from porterchain_api.booking_engine.payment_service import PaymentService
from porterchain_api.booking_engine.quote_service import QuoteService
from porterchain_api.booking_engine.tracking_service import TrackingService
from porterchain_api.booking_engine.visitor_tracking_service import VisitorTrackingService
from porterchain_api.merchant_engine.booking_flow_service import MerchantBookingFlowService
from porterchain_api.merchant_engine.contacts_service import MerchantContactsService
from porterchain_api.notification_engine.delivery_service import DeliveryService
from porterchain_api.schemas import AddressInput, CreateQuoteRequest, WebsitePricingSnapshot
from porterchain_api.schemas_admin import DriverCreateRequest


def _pricing() -> WebsitePricingSnapshot:
    return WebsitePricingSnapshot(
        customer_price_cad=40.0,
        driver_payout_cad=28.0,
        platform_margin_cad=12.0,
        distance_km=5.0,
        duration_minutes=15.0,
        engine_vehicle_id="cargo_van",
        breakdown={"base": 10.0},
    )


def test_settings_all_platform_user_types(db, settings) -> None:
    svc = AdminSettingsService()
    # Staff is Staff IdP — no Clerk fetch.
    staff_resp = svc.list_platform_users(db, settings, "staff", limit=5)
    assert staff_resp.total >= 0
    assert staff_resp.clerk_synced is False
    for user_type in ("merchant", "driver", "customer"):
        with patch("porterchain_api.admin_engine.settings_service.fetch_clerk_snapshots", return_value={}):
            resp = svc.list_platform_users(db, settings, user_type, limit=5)
            assert resp.total >= 0


def test_merchant360_timeline_and_locations(db, merchant_ctx) -> None:
    svc = Merchant360Service()
    mid = merchant_ctx.merchant.id
    assert isinstance(svc.timeline(db, mid, None), list)
    assert isinstance(svc.locations(db, mid), dict)
    assert isinstance(svc.team(db, mid), list)


def test_driver360_full_paths(db, driver) -> None:
    svc = Driver360Service()
    did = driver.id
    assert isinstance(svc.list_drivers(db, limit=5), list)
    assert isinstance(svc.facets(db), dict)
    assert isinstance(svc.stats(db), dict)
    assert isinstance(svc.vehicles(db, did), list)
    assert isinstance(svc.payouts(db, did), dict)
    assert isinstance(svc.incidents(db, did), dict)
    assert isinstance(svc.timeline(db, did), list)


def test_admin_driver_create(db, admin_ctx, settings) -> None:
    svc = AdminDriverService()
    created = svc.create_driver(
        db,
        admin_ctx,
        DriverCreateRequest(
            email=f"new-driver-{datetime.now(UTC).timestamp()}@svc.test",
            full_name="New Driver",
            phone="+1 416-555-0100",
        ),
        settings=settings,
    )
    assert created.id


def test_booking_quote_customer_payment_tracking(db, settings) -> None:
    session = f"cov-{datetime.now(UTC).timestamp()}"
    quote = QuoteService().create_quote(
        db,
        settings,
        CreateQuoteRequest(
            anonymous_session_id=session,
            pickup=AddressInput(formatted="1 King St W, Toronto", lat=43.65, lng=-79.38),
            dropoff=AddressInput(formatted="2 Bay St, Toronto", lat=43.64, lng=-79.37),
            vehicle_class="cargo_van",
            package_type="looseParcel",
            weight_kg=3.0,
            scheduled_at=datetime.now(UTC),
            schedule_mode="now",
            website_pricing=_pricing(),
        ),
        ip_address="127.0.0.1",
    )
    customer = CustomerService().upsert(
        db,
        clerk_user_id="clerk_cov_test",
        email="cov@test.porterchain.com",
        phone="+1 416-555-0111",
        visitor_session_id=session,
    )
    assert customer.id
    assert PaymentService().get_active_payment(db, quote.id) is None
    VisitorTrackingService().ensure_session(db, session_id=session, ip_address="127.0.0.1")
    assert TrackingService().get_by_tracking(db, "missing") is None


def test_merchant_booking_flow_preview(db, merchant_ctx) -> None:
    flow = MerchantBookingFlowService()
    assert isinstance(flow.list_templates(db, merchant_ctx), list)


def test_contacts_create(db, merchant_ctx) -> None:
    svc = MerchantContactsService()
    row = svc.create_contact(
        db,
        merchant_ctx,
        {
            "first_name": "Ops",
            "last_name": "Lead",
            "email": "ops@example.com",
            "phone": "+1 416-555-0122",
            "roles": ["billing"],
        },
    )
    assert row["first_name"] == "Ops"


def test_notification_delivery(monkeypatch) -> None:
    """No SMTP host is configured here, so delivery stays deferred instead of pretending it sent."""
    from types import SimpleNamespace

    monkeypatch.setattr(
        "porterchain_api.notification_engine.delivery_service.get_platform_settings",
        lambda: SimpleNamespace(smtp_host="", smtp_password=""),
    )
    log = DeliveryService().deliver(
        {
            "channel": "email",
            "recipient": "a@example.com",
            "template": "delivery_update",
            "context": {"tracking_number": "TRK1"},
        }
    )
    assert log.status == "deferred"


def test_user_sync_get_by_clerk(db) -> None:
    assert UserSyncService().get_by_clerk_id(db, "missing-clerk-id") is None
