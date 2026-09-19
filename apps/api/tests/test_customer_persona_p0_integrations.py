"""Customer persona P0 integrations — Stripe link, Valhalla/OSRM, Fleetbase, notif/Mailpit.

Companion to test_customer_persona_p0.py. Catalog:
docs/CUSTOMER_PERSONA_DEV_TEST_CASES.md (PAY-*, SPA-*, FB-*, NOTIF-*, C-UI book).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.customer_booking_admin_service import CustomerBookingAdminService
from porterchain_api.admin_engine.rbac import MODULE_PERMISSIONS, AdminContext, parse_admin_role
from porterchain_api.admin_models import AdminUser
from porterchain_api.auth.admin import get_admin_context
from porterchain_api.booking_engine.booking_service import BookingService
from porterchain_api.booking_engine.confirmation_service import BookingConfirmationService
from porterchain_api.booking_engine.fleetbase_sync_handler import sync_order_from_event
from porterchain_api.booking_engine.numbers import generate_order_number, generate_tracking_number
from porterchain_api.booking_engine.quote_service import QuoteService
from porterchain_api.booking_models import Customer, DomainEvent, Order, Stop
from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db
from porterchain_api.domain.states import OrderState
from porterchain_api.main import app
from porterchain_api.notification_engine.event_router import _specs_for_event
from porterchain_api.schemas import AddressInput, CreateQuoteRequest, WebsitePricingSnapshot
from porterchain_api.services.routing import resolve_route_distance
from porterchain_pricing import GeoPoint
from porterchain_services.maps.service import MapsService
from porterchain_shared.events.catalog import DomainEventType

REPO_ROOT = Path(__file__).resolve().parents[3]
CUSTOMER_SRC = REPO_ROOT / "apps" / "customer" / "src"
ADMIN_SRC = REPO_ROOT / "apps" / "admin" / "src"
API_SRC = REPO_ROOT / "apps" / "api" / "src" / "porterchain_api"
COMPOSE = REPO_ROOT / "infrastructure" / "docker" / "docker-compose.yml"


def _matrix_require_module(ctx: AdminContext, module: str) -> None:
    allowed = MODULE_PERMISSIONS.get(module, frozenset())
    if ctx.role not in allowed:
        raise PermissionError(f"admin_forbidden:{module}")


def _admin_ctx(role: str = "super_admin") -> AdminContext:
    return AdminContext(
        user=AdminUser(
            clerk_user_id=f"admin-int-{role}-{uuid4().hex[:6]}",
            email=f"{role}-int@porterchain.com",
            role=role,
        ),
        role=parse_admin_role(role),
    )


def _addr_dict() -> dict:
    return {"formatted": "1 King St W, Toronto", "lat": 43.6488, "lng": -79.3817}


def _addr() -> AddressInput:
    return AddressInput(formatted="100 King St W, Toronto ON M5X 1A9", lat=43.6488, lng=-79.3817)


def _dropoff() -> AddressInput:
    return AddressInput(formatted="200 Bay St, Toronto ON M5J 2J2", lat=43.6476, lng=-79.3797)


def _website_pricing() -> WebsitePricingSnapshot:
    return WebsitePricingSnapshot(
        customer_price_cad=48.0,
        driver_payout_cad=32.0,
        platform_margin_cad=16.0,
        distance_km=8.0,
        duration_minutes=24.0,
        engine_vehicle_id="cargo_van",
        breakdown={"base": 12.0, "distance": 36.0},
    )


def _stripe_settings() -> Settings:
    """Local + secret + stripe_mock=False → real checkout path (mocked SDK)."""
    return Settings(
        app_env="local",
        stripe_mock=False,
        stripe_secret="sk_test_customer_p0",
        jwt_secret="test-jwt-secret-local",
        spicedb_enabled=False,
        spicedb_use_memory=True,
        spicedb_required=False,
        customer_portal_url="http://localhost:3004",
        retail_checkout_success_url="http://localhost:3000/en/book/success",
        retail_checkout_cancel_url="http://localhost:3000/en/book/continue",
    )


def _make_customer(db: Session) -> Customer:
    tag = uuid4().hex[:10]
    row = Customer(
        clerk_user_id=f"user_int_{tag}",
        email=f"int-{tag}@p0.test",
        phone="+14165550111",
    )
    db.add(row)
    db.flush()
    return row


# ---------------------------------------------------------------------------
# Stripe payment link (API-A-008/009, PAY-001, A-UI-032 backend)
# ---------------------------------------------------------------------------


def test_pay_admin_customer_draft_payment_link_uses_customer_channel(db: Session) -> None:
    """API-A-008/009 + PAY-001: phone-book link lands on customer portal URLs."""
    settings = _stripe_settings()
    assert settings.allow_stripe_mock is False
    customer = _make_customer(db)
    db.commit()
    ctx = _admin_ctx()

    session = MagicMock()
    session.url = "https://checkout.stripe.test/cs_customer_p0"
    session.id = "cs_test_customer_p0"

    with patch("porterchain_services.stripe.sdk.create_checkout_session", return_value=session) as create:
        with patch("porterchain_services.stripe.sdk.configure"):
            with patch(
                "porterchain_api.services.stripe_service.ensure_stripe_customer",
                return_value="cus_test",
            ):
                out = CustomerBookingAdminService().create_for_customer(
                    db,
                    settings,
                    ctx,
                    customer.id,
                    pickup=_addr_dict(),
                    dropoff=_addr_dict(),
                    vehicle_class="cargo_van",
                    scheduled_at=datetime.now(UTC) + timedelta(hours=2),
                    schedule_mode="scheduled",
                    send_payment_link=True,
                )

    assert out["checkout_url"] == "https://checkout.stripe.test/cs_customer_p0"
    assert out["payment_id"]
    assert out["stripe_checkout_session_id"] == "cs_test_customer_p0"
    kwargs = create.call_args.kwargs
    assert kwargs["metadata"]["checkout_channel"] == "customer"
    assert kwargs["success_url"].startswith("http://localhost:3004/book/success")
    assert kwargs["cancel_url"].startswith("http://localhost:3004/book")


def test_pay_admin_send_payment_link_for_existing_draft(db: Session) -> None:
    """API-A-011 service: resend payment link for customer-owned draft."""
    settings = _stripe_settings()
    customer = _make_customer(db)
    db.commit()
    ctx = _admin_ctx()

    with patch.object(
        CustomerBookingAdminService,
        "_start_checkout",
        return_value={
            "checkout_url": "https://checkout.stripe.test/resend",
            "payment_id": "pay_1",
            "stripe_checkout_session_id": "cs_resend",
        },
    ):
        created = CustomerBookingAdminService().create_for_customer(
            db,
            settings,
            ctx,
            customer.id,
            pickup=_addr_dict(),
            dropoff=_addr_dict(),
            vehicle_class="cargo_van",
            scheduled_at=datetime.now(UTC) + timedelta(hours=2),
            schedule_mode="scheduled",
            send_payment_link=False,
        )
        resent = CustomerBookingAdminService().send_payment_link_for_customer(
            db,
            settings,
            ctx,
            customer_id=customer.id,
            draft_id=created["draft_id"],
        )
    assert resent["checkout_url"] == "https://checkout.stripe.test/resend"

    with pytest.raises(LookupError, match="draft_not_found"):
        CustomerBookingAdminService().send_payment_link_for_customer(
            db,
            settings,
            ctx,
            customer_id=customer.id,
            draft_id="missing-draft",
        )


@pytest.fixture
def admin_client(db: Session, monkeypatch: pytest.MonkeyPatch):
    holder: dict = {"ctx": _admin_ctx("super_admin"), "settings": _stripe_settings()}

    monkeypatch.setattr(
        "porterchain_api.routers.customers_admin.require_module",
        _matrix_require_module,
    )
    app.dependency_overrides[get_admin_context] = lambda: holder["ctx"]
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_settings] = lambda: holder["settings"]
    yield TestClient(app), holder
    app.dependency_overrides.clear()


def test_http_admin_create_draft_with_payment_link(admin_client, db: Session) -> None:
    """HTTP API-A-008/009 with Stripe SDK mocked."""
    client, holder = admin_client
    customer = _make_customer(db)
    db.commit()

    session = MagicMock()
    session.url = "https://checkout.stripe.test/http"
    session.id = "cs_http"

    with patch("porterchain_services.stripe.sdk.create_checkout_session", return_value=session):
        with patch("porterchain_services.stripe.sdk.configure"):
            with patch(
                "porterchain_api.services.stripe_service.ensure_stripe_customer",
                return_value="cus_http",
            ):
                resp = client.post(
                    f"/v1/admin/customers/{customer.id}/booking-drafts",
                    json={
                        "pickup": _addr_dict(),
                        "dropoff": _addr_dict(),
                        "vehicle_class": "cargo_van",
                        "scheduled_at": (datetime.now(UTC) + timedelta(hours=2)).isoformat(),
                        "schedule_mode": "scheduled",
                        "send_payment_link": True,
                    },
                )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["checkout_url"] == "https://checkout.stripe.test/http"
    assert body["draft_id"]

    # Resend
    with patch.object(
        CustomerBookingAdminService,
        "_start_checkout",
        return_value={
            "checkout_url": "https://checkout.stripe.test/http2",
            "payment_id": "pay_http2",
            "stripe_checkout_session_id": "cs_http2",
        },
    ):
        resend = client.post(
            f"/v1/admin/customers/{customer.id}/booking-drafts/{body['draft_id']}/send-payment-link"
        )
    assert resend.status_code == 200, resend.text
    assert resend.json()["checkout_url"] == "https://checkout.stripe.test/http2"


def test_ui_admin_add_order_modal_wires_payment_link() -> None:
    """A-UI-032: modal posts send_payment_link and surfaces checkout_url."""
    modal = (ADMIN_SRC / "components/customers/CustomerAddOrderModal.tsx").read_text(encoding="utf-8")
    lib = (ADMIN_SRC / "lib/customers.ts").read_text(encoding="utf-8")
    assert "send_payment_link" in modal or "sendPaymentLink" in modal or "send_payment_link" in lib
    assert "checkout_url" in modal
    assert "createBookingDraft" in lib
    assert "sendPaymentLink" in lib or "send-payment-link" in lib


def test_ui_customer_book_clerk_quote_mock_complete() -> None:
    """C-UI-010/042/043 contract: book flow uses Clerk + quotes + mock-complete."""
    book = (CUSTOMER_SRC / "components/booking/CustomerBookDelivery.tsx").read_text(encoding="utf-8")
    booking_lib = (CUSTOMER_SRC / "lib/booking.ts").read_text(encoding="utf-8")
    assert "createQuote" in book
    assert "mockCompleteCheckout" in book or "syncBookingCheckout" in book
    assert 'checkout_channel: "customer"' in booking_lib
    assert "/v1/quotes" in booking_lib
    assert "/v1/bookings" in booking_lib
    assert "isClerkConfigured" in book
    assert "CustomerBookDeliveryWithClerk" in book or "useAuth" in book or "useUser" in book


# ---------------------------------------------------------------------------
# Spatial — Valhalla primary / OSRM fallback (SPA-001/002)
# ---------------------------------------------------------------------------


def test_spa_valhalla_primary_for_route_distance() -> None:
    """SPA-001: MapsService labels Valhalla when primary succeeds."""
    svc = MapsService()
    svc.ctx = SimpleNamespace(
        settings=SimpleNamespace(
            routing_engine="valhalla",
            valhalla_url="http://valhalla.test",
            osrm_url="http://osrm.test",
            osrm_allow_public_demo=False,
        )
    )
    with (
        patch.object(svc, "_valhalla_route", return_value={"distance": 1200, "time": 180}),
        patch.object(svc, "_osrm_route", return_value=None) as osrm,
    ):
        leg, source = svc.route_with_source((43.65, -79.38), (43.66, -79.39))
    assert leg is not None
    assert source == "valhalla"
    osrm.assert_not_called()


def test_spa_osrm_fallback_when_valhalla_none() -> None:
    """SPA-002."""
    svc = MapsService()
    svc.ctx = SimpleNamespace(
        settings=SimpleNamespace(
            routing_engine="valhalla",
            valhalla_url="http://valhalla.test",
            osrm_url="http://osrm.test",
            osrm_allow_public_demo=False,
        )
    )
    with (
        patch.object(svc, "_valhalla_route", return_value=None),
        patch.object(svc, "_osrm_route", return_value={"distance": 900, "time": 100}),
    ):
        leg, source = svc.route_with_source((43.65, -79.38), (43.66, -79.39))
    assert source == "osrm"


def test_spa_resolve_route_distance_never_google() -> None:
    with patch("porterchain_api.services.routing.MapsService") as maps_cls:
        maps = MagicMock()
        maps.route_distance_meters.return_value = (1500, 200, "valhalla")
        maps_cls.return_value = maps
        _m, _s, source = resolve_route_distance(
            GeoPoint(lat=43.65, lng=-79.38),
            GeoPoint(lat=43.66, lng=-79.39),
        )
    assert source in {"valhalla", "osrm", "haversine"}
    assert "google" not in source.lower()


# ---------------------------------------------------------------------------
# Fleetbase handshake (FB-001)
# ---------------------------------------------------------------------------


def test_fb_confirmation_dual_writes_stops_and_order_created(db: Session, settings: Settings) -> None:
    """FB-001 precursor: paid order gets Stop rows + ORDER_CREATED domain event."""
    session_id = f"fb-p0-{uuid4().hex[:8]}"
    scheduled = datetime.now(UTC).replace(microsecond=0) + timedelta(hours=3)
    quote = QuoteService().create_quote(
        db,
        settings,
        CreateQuoteRequest(
            anonymous_session_id=session_id,
            pickup=_addr(),
            dropoff=_dropoff(),
            vehicle_class="cargo_van",
            package_type="looseParcel",
            weight_kg=5.0,
            scheduled_at=scheduled,
            schedule_mode="scheduled",
            website_pricing=_website_pricing(),
        ),
        ip_address="127.0.0.1",
    )
    quote, customer, _url = BookingService().start_booking(
        db,
        settings,
        quote_id=quote.id,
        email=f"fb-{uuid4().hex[:6]}@p0.test",
        phone="+14165550888",
        clerk_user_id=f"clerk_fb_{uuid4().hex[:8]}",
        anonymous_session_id=session_id,
        consent={
            "terms_accepted": True,
            "privacy_accepted": True,
            "dangerous_goods_confirmed": True,
            "consent_at": datetime.now(UTC).isoformat(),
        },
        checkout_channel="customer",
    )
    order = BookingConfirmationService().mock_complete_checkout(db, settings, quote.id)
    assert order.tracking_number
    stops = db.query(Stop).filter(Stop.order_id == order.id).all()
    assert len(stops) >= 2
    kinds = {s.kind for s in stops}
    assert "pickup" in kinds and ("drop" in kinds or "dropoff" in kinds)

    events = {
        row.event_type
        for row in db.query(DomainEvent)
        .filter(DomainEvent.aggregate_id.in_([order.id, quote.id, customer.id]))
        .all()
    }
    assert any("order" in e.lower() and "creat" in e.lower() for e in events) or (
        DomainEventType.ORDER_CREATED in events or "order.created" in events
    )


def test_fb_sync_handler_pushes_via_booking_sync_service(db: Session, settings: Settings) -> None:
    """FB-001: event handler calls Fleetbase BookingSyncService.push_order (adapter path)."""
    customer = _make_customer(db)
    order = Order(
        order_number=generate_order_number(),
        tracking_number=generate_tracking_number(),
        state=OrderState.DISPATCH_READY.value,
        customer_id=customer.id,
        amount_cents=2500,
        currency="cad",
        pickup=_addr_dict(),
        dropoff=_addr_dict(),
        scheduled_at=datetime.now(UTC),
    )
    db.add(order)
    db.commit()

    push = MagicMock()
    session = MagicMock()
    session.query.return_value.filter.return_value.first.return_value = order
    session.close = MagicMock()

    with patch(
        "porterchain_api.fleetbase_engine.booking_sync_service.BookingSyncService"
    ) as sync_cls:
        sync_cls.return_value.push_order = push
        with patch(
            "porterchain_api.config.get_settings",
            return_value=settings,
        ):
            with patch(
                "porterchain_api.db.SessionLocal",
                return_value=session,
            ):
                sync_order_from_event(
                    {
                        "aggregate_id": order.id,
                        "payload": {"order_id": order.id},
                        "event_type": "order.created",
                    }
                )
    push.assert_called_once()
    assert push.call_args.args[0] is session
    assert push.call_args.args[2] is order


# ---------------------------------------------------------------------------
# Notifications + Mailpit (NOTIF-001/002)
# ---------------------------------------------------------------------------


def test_notif_order_created_routes_customer_email_inbox() -> None:
    """NOTIF-001: ORDER_CREATED → customer in_app + email."""
    customer_id = f"cust-{uuid4().hex[:8]}"
    specs = _specs_for_event(
        DomainEventType.ORDER_CREATED,
        {
            "customer_id": customer_id,
            "email": "buyer@p0.test",
            "order_id": "ord-1",
            "tracking_number": "PCTEST",
            "order_number": "PC-1",
        },
    )
    channels = {(s["channel"], s["recipient_type"]) for s in specs if s["recipient_id"] == customer_id}
    assert ("in_app", "customer") in channels
    emails = [s for s in specs if s["channel"] == "email" and s.get("recipient_address") == "buyer@p0.test"]
    assert emails, "customer email channel missing for ORDER_CREATED"


def test_notif_booking_confirmed_routes_push_and_email() -> None:
    """NOTIF-001 push path via BOOKING_CONFIRMED fan-out."""
    customer_id = f"cust-{uuid4().hex[:8]}"
    specs = _specs_for_event(
        DomainEventType.BOOKING_CONFIRMED,
        {
            "customer_id": customer_id,
            "email": "buyer@p0.test",
            "order_id": "ord-2",
            "tracking_number": "PCTEST2",
        },
    )
    channels = {s["channel"] for s in specs if s["recipient_id"] == customer_id}
    assert "in_app" in channels
    assert "push" in channels
    assert "email" in channels


def test_notif_booking_confirmed_template_registered() -> None:
    from porterchain_api.notification_engine.templates import TEMPLATE_META, TEMPLATES

    assert "booking_confirmed" in TEMPLATE_META
    assert "booking_confirmed" in TEMPLATES


def test_notif_mailpit_local_delivery_and_compose() -> None:
    """NOTIF-002: local SMTP forced to Mailpit; compose pins mailpit (not Mailhog)."""
    delivery = (API_SRC / "notification_engine/delivery_service.py").read_text(encoding="utf-8")
    assert "Mailpit" in delivery or "mailpit" in delivery.lower()
    assert "app_env" in delivery
    compose = COMPOSE.read_text(encoding="utf-8")
    assert "mailpit" in compose.lower()
    assert "mailhog" not in compose.lower()
    assert "1025" in compose
    env_ex = (REPO_ROOT / "env" / "api.env.example").read_text(encoding="utf-8")
    assert "Mailpit" in env_ex or "mailpit" in env_ex.lower()
    assert "1025" in env_ex


def test_notif_fcm_in_delivery_stack() -> None:
    """NOTIF-004 arch: DeliveryService owns FCM path for customer push."""
    delivery = (API_SRC / "notification_engine/delivery_service.py").read_text(encoding="utf-8")
    assert "fcm" in delivery.lower() or "firebase" in delivery.lower()
    assert "push" in delivery.lower()
