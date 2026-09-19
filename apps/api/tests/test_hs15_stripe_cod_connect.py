"""HS-15 — Stripe COD Connect is additive; retail Checkout settle stays unbroken."""

from __future__ import annotations

import inspect
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from porterchain_api.billing_engine.stripe_cod_service import StripeCodService
from porterchain_api.booking_engine.booking_service import BookingService
from porterchain_api.booking_engine.quote_service import QuoteService
from porterchain_api.booking_engine.stripe_webhook_service import StripeWebhookService
from porterchain_api.booking_models import Order, Payment
from porterchain_api.config import Settings
from porterchain_api.domain.states import CodStatus, OrderState
from porterchain_api.domain.merchant_states import MerchantStatus
from porterchain_api.merchant_models import Merchant
from porterchain_api.schemas import AddressInput, CreateQuoteRequest, WebsitePricingSnapshot
from porterchain_api.services import stripe_service as stripe_svc


def _quote_book(db: Session, settings: Settings, *, email: str, clerk: str):
    sid = f"hs15-{uuid4().hex[:10]}"
    quote = QuoteService().create_quote(
        db,
        settings,
        CreateQuoteRequest(
            anonymous_session_id=sid,
            pickup=AddressInput(formatted="1 King St W, Toronto", lat=43.6488, lng=-79.3817),
            dropoff=AddressInput(formatted="2 Bay St, Toronto", lat=43.6476, lng=-79.3797),
            vehicle_class="cargo_van",
            package_type="looseParcel",
            weight_kg=4.0,
            scheduled_at=datetime.now(UTC).replace(microsecond=0),
            schedule_mode="now",
            website_pricing=WebsitePricingSnapshot(
                customer_price_cad=45.0,
                driver_payout_cad=30.0,
                platform_margin_cad=15.0,
                distance_km=6.0,
                duration_minutes=18.0,
                engine_vehicle_id="cargo_van",
                breakdown={"base": 10.0, "distance": 35.0},
            ),
        ),
        ip_address="127.0.0.1",
    )
    quote, customer, checkout_url = BookingService().start_booking(
        db,
        settings,
        quote_id=quote.id,
        email=email,
        phone="+1 416-555-1515",
        clerk_user_id=clerk,
        anonymous_session_id=sid,
        consent={
            "terms_accepted": True,
            "privacy_accepted": True,
            "dangerous_goods_confirmed": True,
        },
    )
    payment = db.query(Payment).filter(Payment.quote_id == quote.id).one()
    return quote, customer, payment, checkout_url


def test_hs15_cod_session_uses_connect_transfer_not_retail_checkout() -> None:
    cod_src = inspect.getsource(stripe_svc.create_cod_checkout_session)
    retail_src = inspect.getsource(stripe_svc.create_checkout_session)
    assert "transfer_data" in cod_src
    assert "application_fee_amount" in cod_src
    assert "purpose" not in retail_src or '"purpose"' not in retail_src
    assert "transfer_data" not in retail_src
    assert "destination_account_id" in cod_src


def test_hs15_cod_webhook_collects_without_creating_retail_order(
    db: Session, settings: Settings, monkeypatch
) -> None:
    settings = settings.model_copy(update={"stripe_mock": True})
    mid = str(uuid4())
    oid = str(uuid4())
    merchant = Merchant(
        id=mid,
        company_name=f"HS15 COD {mid[:8]}",
        email=f"hs15-cod-{mid[:8]}@test.porterchain.com",
        status=MerchantStatus.ACTIVE.value,
        cod_enabled=True,
        stripe_connect_account_id="acct_mock_hs15",
    )
    db.add(merchant)
    db.flush()
    order = Order(
        id=oid,
        order_number=f"HS15{oid[:8].upper()}",
        tracking_number=f"PCHS15{oid[:8].upper()}",
        state=OrderState.AT_DESTINATION.value,
        merchant_id=mid,
        amount_cents=45000,
        currency="cad",
        pickup={"formatted": "1 King St W"},
        dropoff={"formatted": "2 Bay St"},
        scheduled_at=datetime.now(UTC).replace(microsecond=0),
        cod_amount_cents=45000,
        cod_status=CodStatus.PENDING_COLLECTION.value,
        compliance_metadata={},
    )
    db.add(order)
    db.commit()

    monkeypatch.setattr(
        "porterchain_api.merchant_engine.scan_gate_service.ScanGateService.assert_cod_scans",
        lambda self, db, order: None,
    )
    monkeypatch.setattr(
        "porterchain_api.merchant_engine.shopify_service.capture_cod_transaction",
        lambda *a, **k: None,
    )

    issued = StripeCodService().issue_cod_checkout(db, settings, order, merchant)
    assert issued["mock"] is True
    assert issued["checkout_url"]
    db.refresh(order)
    assert order.cod_status == CodStatus.LINK_ISSUED.value
    session_id = order.cod_stripe_session_id
    assert session_id

    orders_before = db.query(Order).count()
    event_id = f"evt_hs15_cod_{uuid4().hex}_{uuid4().hex[:8]}"
    result = StripeWebhookService().handle(
        db,
        settings,
        {
            "id": event_id,
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": session_id,
                    "metadata": {
                        "purpose": "cod",
                        "order_id": order.id,
                        "merchant_id": merchant.id,
                        "cod_amount_cents": "45000",
                    },
                    "payment_intent": "pi_hs15_cod",
                    "payment_method_types": ["card"],
                    "amount_total": 45000,
                    "currency": "cad",
                }
            },
        },
    )
    assert result == {"status": "ok"}
    db.refresh(order)
    assert order.cod_status == CodStatus.COLLECTED.value
    assert (order.compliance_metadata or {}).get("cod", {}).get("payment_intent_id") == "pi_hs15_cod"
    assert db.query(Order).count() == orders_before  # no extra retail order

    dup = StripeWebhookService().handle(
        db,
        settings,
        {
            "id": event_id,
            "type": "checkout.session.completed",
            "data": {"object": {"metadata": {"purpose": "cod", "order_id": order.id}}},
        },
    )
    assert dup == {"status": "duplicate"}


def test_hs15_retail_checkout_settle_unbroken(db: Session, settings: Settings) -> None:
    settings = settings.model_copy(update={"stripe_mock": True})
    quote, customer, payment, checkout_url = _quote_book(
        db,
        settings,
        email=f"hs15.retail.{uuid4().hex[:8]}@test.porterchain.com",
        clerk=f"clerk_hs15_retail_{uuid4().hex[:8]}",
    )
    # Mock path intentionally returns no Stripe-hosted URL.
    assert checkout_url is None

    event_id = f"evt_hs15_retail_{uuid4().hex}_{uuid4().hex[:8]}"
    first = StripeWebhookService().handle(
        db,
        settings,
        {
            "id": event_id,
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "metadata": {
                        "quote_id": quote.id,
                        "customer_id": customer.id,
                        "payment_id": payment.id,
                        # no purpose=cod — retail prepaid path
                    },
                    "payment_intent": "pi_hs15_retail",
                    "payment_method_types": ["card"],
                    "amount_total": 4500,
                    "currency": "cad",
                }
            },
        },
    )
    assert first == {"status": "ok"}
    assert db.query(Order).filter(Order.quote_id == quote.id).count() == 1
