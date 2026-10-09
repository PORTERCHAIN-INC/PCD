"""API-side regressions for the Oct 2026 pricing audit (bugs 3, 5, 8)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from porterchain_api.booking_engine.quote_service import QuoteService
from porterchain_api.domain.merchant_states import MerchantRole, MerchantStatus
from porterchain_api.merchant_engine.booking_flow_service import MerchantBookingFlowService
from porterchain_api.merchant_engine.booking_service import MerchantBookingService
from porterchain_api.merchant_engine.booking_validation import BookingValidationError
from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_api.merchant_models import Merchant, MerchantUser, SavedAddress, ShopifyRateQuote, ShopifyShop
from porterchain_api.schemas import AddressInput, CreateQuoteRequest
from porterchain_api.schemas_merchant import AddressInput as MerchantAddressInput
from porterchain_api.schemas_merchant import MerchantBookDeliveryRequest


def _merchant_ctx(db, *, pricing_model: str = "fsa") -> MerchantContext:
    suffix = uuid4().hex[:8]
    merchant = Merchant(
        company_name=f"Audit Co {suffix}",
        email=f"audit-{suffix}@test.local",
        status=MerchantStatus.ACTIVE.value,
        pricing_model=pricing_model,
    )
    db.add(merchant)
    db.flush()
    user = MerchantUser(
        merchant_id=merchant.id,
        clerk_user_id=f"clerk_{suffix}",
        email=f"user-{suffix}@test.local",
        role=MerchantRole.OWNER.value,
    )
    db.add(user)
    db.flush()
    return MerchantContext(merchant=merchant, user=user, role=MerchantRole.OWNER)


def _refused():
    return SimpleNamespace(
        final_cents=0,
        metadata={"fsa_refused": True, "pricing_model": "fsa_refused"},
        items=[],
    )


def _body() -> MerchantBookDeliveryRequest:
    return MerchantBookDeliveryRequest(
        pickup=MerchantAddressInput(
            formatted="100 King St W, Toronto, ON M5X 1A9",
            postal="M5X1A9",
            lat=43.648,
            lng=-79.381,
        ),
        dropoff=MerchantAddressInput(
            formatted="1 Wellington St, Ottawa, ON K1A 0A6",
            postal="K1A0A6",
            lat=45.42,
            lng=-75.70,
        ),
        vehicle_class="cargo_van",
        package_type="looseParcel",
        weight_kg=5.0,
        scheduled_at=datetime.now(UTC),
    )


def test_create_shipment_raises_fsa_refused(db, settings):
    ctx = _merchant_ctx(db)
    with (
        patch(
            "porterchain_api.merchant_engine.booking_service.get_pricing_service",
            return_value=SimpleNamespace(calculate_merchant=lambda *_a, **_k: _refused()),
        ),
        patch(
            "porterchain_api.merchant_engine.booking_service.assert_ontario_booking",
            lambda *_a, **_k: None,
        ),
        patch(
            "porterchain_api.merchant_engine.booking_service.assert_pickup_window",
            lambda *_a, **_k: None,
        ),
        patch(
            "porterchain_api.merchant_engine.booking_service._assert_credit_headroom",
            lambda *_a, **_k: None,
        ),
    ):
        with pytest.raises(BookingValidationError) as exc:
            MerchantBookingService().create_shipment(db, settings, ctx, _body())
    assert exc.value.code == "fsa_refused"


def test_preview_returns_fsa_refused(db, settings):
    ctx = _merchant_ctx(db)
    flow = MerchantBookingFlowService()
    with (
        patch.object(flow, "validate_addresses", return_value=[]),
        patch(
            "porterchain_api.merchant_engine.service_area.assert_ontario_booking",
            lambda *_a, **_k: None,
        ),
        patch(
            "porterchain_api.merchant_engine.booking_service.assert_pickup_window",
            lambda *_a, **_k: None,
        ),
        patch(
            "porterchain_api.merchant_engine.booking_service._assert_credit_headroom",
            lambda *_a, **_k: None,
        ),
        patch.object(
            flow._booking,
            "build_pricing_request",
            return_value=SimpleNamespace(),
        ),
        patch(
            "porterchain_api.merchant_engine.booking_flow_service.get_pricing_service",
            return_value=SimpleNamespace(calculate_merchant=lambda *_a, **_k: _refused()),
        ),
    ):
        out = flow.preview(db, settings, ctx, _body())
    assert out["valid"] is False
    assert out["error"] == "fsa_refused"
    assert "fall back to distance" in out["message"]


def test_admin_order_builder_raises_fsa_refused(db, settings):
    from porterchain_api.admin_engine.order_builder_service import OrderBuilderService
    from porterchain_api.schemas_admin import AdminCreateOrderRequest, AdminOrderStopInput

    ctx = _merchant_ctx(db)
    db.commit()
    body = AdminCreateOrderRequest(
        merchant_id=ctx.merchant.id,
        order_kind="single",
        stops=[
            AdminOrderStopInput(type="pickup", sequence=0, formatted="100 King St W, Toronto, ON M5X 1A9", lat=43.648, lng=-79.381),
            AdminOrderStopInput(type="dropoff", sequence=1, formatted="1 Wellington St, Ottawa, ON K1A 0A6", lat=45.42, lng=-75.70),
        ],
        scheduled_at=datetime.now(UTC),
    )
    with (
        patch(
            "porterchain_api.admin_engine.order_builder_service.resolve_route_distance",
            return_value=(10_000, 900, "haversine"),
        ),
        patch(
            "porterchain_api.admin_engine.order_builder_service.get_pricing_service",
            return_value=SimpleNamespace(calculate_merchant=lambda *_a, **_k: _refused()),
        ),
    ):
        with pytest.raises(ValueError, match="fsa_refused"):
            OrderBuilderService().create(db, settings, MagicMock(), body)


def test_retail_dropoff_outside_service_area(db, settings):
    body = CreateQuoteRequest(
        anonymous_session_id=f"sess-{uuid4().hex[:8]}",
        pickup=AddressInput(
            formatted="100 King St W, Toronto, ON M5X 1A9",
            postal="M5X1A9",
            lat=43.65,
            lng=-79.38,
        ),
        dropoff=AddressInput(
            formatted="1 Wellington St, Ottawa, ON K1A 0A6",
            postal="K1A0A6",
            lat=45.42,
            lng=-75.70,
        ),
        vehicle_class="cargo_van",
        package_type="looseParcel",
        weight_kg=4.0,
        scheduled_at=datetime.now(UTC),
        schedule_mode="now",
    )
    with patch(
        "porterchain_api.admin_engine.platform_settings.address_in_coverage",
        side_effect=lambda db, **kw: "M5X" in (kw.get("postal") or "").upper(),
    ):
        with pytest.raises(ValueError) as exc:
            QuoteService()._price_body(db, settings, body)
    assert str(exc.value) == "dropoff_outside_service_area"


def test_book_reuses_checkout_quote_pickup(db, settings, monkeypatch):
    from porterchain_api.merchant_engine import shopify_service as shopify

    ctx = _merchant_ctx(db, pricing_model="distance")
    shop = ShopifyShop(
        merchant_id=ctx.merchant.id,
        shop_domain=f"audit-{uuid4().hex[:8]}.myshopify.com",
        installed_at=datetime.now(UTC),
        encrypted_access_token="enc",
    )
    db.add(shop)
    db.flush()
    addr = SavedAddress(
        merchant_id=ctx.merchant.id,
        label="Warehouse",
        address_type="pickup",
        formatted="91 Breton Ave, Mississauga, ON L4Z 4K5",
        lat=43.6,
        lng=-79.6,
        postal="L4Z4K5",
        is_default=True,
    )
    db.add(addr)
    db.flush()
    shop.default_pickup_address_id = addr.id
    quote = ShopifyRateQuote(
        shop_id=shop.id,
        merchant_id=ctx.merchant.id,
        request_hash="abc",
        total_cents=5200,
        currency="CAD",
        breakdown={
            "pickup": {
                "formatted": "200 Mississauga Rd, Mississauga, ON L4W 1S9",
                "postal": "L4W1S9",
                "lat": 43.62,
                "lng": -79.65,
                "source": "shopify_origin",
            }
        },
        pickup_postal="L4W1S9",
        dropoff_postal="M5V2B2",
        weight_kg="5.0",
        expires_at=datetime.now(UTC) + timedelta(minutes=20),
    )
    db.add(quote)
    db.commit()

    captured: dict = {}

    def _create(*_a, **kwargs):
        body = _a[3] if len(_a) > 3 else kwargs.get("body")
        captured["pickup"] = body.pickup
        order = MagicMock()
        order.id = "order-1"
        order.compliance_metadata = {}
        return order

    monkeypatch.setattr(shopify, "_ensure_coords", lambda value: value)
    monkeypatch.setattr(
        "porterchain_api.merchant_engine.shopify_payload_ops.assert_ontario_booking",
        lambda *a, **k: None,
    )
    monkeypatch.setattr(shopify, "_actor", MagicMock(return_value=ctx.user))
    monkeypatch.setattr(shopify._booking, "find_by_idempotency_key", MagicMock(return_value=None))
    monkeypatch.setattr(shopify._booking, "create_shipment", _create)

    shopify._book_from_shopify_payload(
        db,
        settings,
        shop_domain=shop.shop_domain,
        payload={
            "id": 99001,
            "financial_status": "paid",
            "shipping_address": {
                "address1": "2 King",
                "city": "Toronto",
                "country": "Canada",
                "zip": "M5V2B2",
                "latitude": 43.65,
                "longitude": -79.38,
            },
            "note_attributes": [{"name": "porterchain_quote_id", "value": quote.id}],
        },
    )
    assert captured["pickup"].postal == "L4W1S9"
    assert "Mississauga Rd" in (captured["pickup"].formatted or "")
