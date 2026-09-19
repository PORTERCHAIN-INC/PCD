"""Spend attribution for merchant reports (channel + pricing model + bands)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from porterchain_api.booking_engine.numbers import generate_order_number, generate_tracking_number
from porterchain_api.domain.merchant_states import MerchantRole, MerchantStatus
from porterchain_api.domain.states import OrderSource, OrderState
from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_api.merchant_engine.reporting_metrics import (
    channel_for_order_source,
    spend_attribution,
    spend_by_channel,
    top_pricing_bands,
)
from porterchain_api.merchant_engine.reports_service import MerchantReportsService
from porterchain_api.merchant_models import Merchant, MerchantUser
from porterchain_api.booking_models import Order


def _addr(**extra) -> dict:
    base = {"formatted": "1 King St W, Toronto", "lat": 43.6488, "lng": -79.3817}
    base.update(extra)
    return base


def _merchant_ctx(db, *, pricing_model: str = "distance") -> MerchantContext:
    suffix = uuid4().hex[:8]
    merchant = Merchant(
        company_name=f"Attr Co {suffix}",
        email=f"attr-{suffix}@test.local",
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


def _order(
    db,
    merchant_id: str,
    *,
    source: str,
    amount: int,
    distance_meters: int | None = None,
    dropoff: dict | None = None,
) -> Order:
    compliance = None
    if distance_meters is not None:
        compliance = {"quote": {"distance_meters": distance_meters, "amount_cents": amount}}
    order = Order(
        order_number=generate_order_number(),
        tracking_number=generate_tracking_number(),
        state=OrderState.DELIVERED.value,
        merchant_id=merchant_id,
        amount_cents=amount,
        currency="cad",
        order_source=source,
        pickup=_addr(),
        dropoff=dropoff or _addr(postal_code="M5V1E3"),
        compliance_metadata=compliance,
        scheduled_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
    )
    db.add(order)
    db.flush()
    return order


def test_channel_mapping():
    assert channel_for_order_source("SHOPIFY") == "shopify"
    assert channel_for_order_source("API") == "api"
    assert channel_for_order_source("MERCHANT") == "portal"
    assert channel_for_order_source("CSV") == "portal"


def test_spend_by_channel_and_bands(db):
    ctx = _merchant_ctx(db, pricing_model="distance")
    _order(db, ctx.merchant.id, source=OrderSource.SHOPIFY.value, amount=5000, distance_meters=3000)
    _order(db, ctx.merchant.id, source=OrderSource.SHOPIFY.value, amount=2500, distance_meters=8000)
    _order(db, ctx.merchant.id, source=OrderSource.MERCHANT.value, amount=1000, distance_meters=12000)
    _order(db, ctx.merchant.id, source=OrderSource.API.value, amount=4000, distance_meters=25000)
    db.commit()

    channels = {r["channel"]: r for r in spend_by_channel(db, ctx.merchant.id)}
    assert channels["shopify"]["spend_cents"] == 7500
    assert channels["shopify"]["orders"] == 2
    assert channels["portal"]["spend_cents"] == 1000
    assert channels["api"]["spend_cents"] == 4000

    bands = {r["band"]: r for r in top_pricing_bands(db, ctx.merchant.id)}
    assert bands["0–5 km"]["spend_cents"] == 5000
    assert bands["5–10 km"]["spend_cents"] == 2500
    assert bands["10–20 km"]["spend_cents"] == 1000
    assert bands["20–40 km"]["spend_cents"] == 4000

    attr = spend_attribution(db, ctx.merchant.id)
    assert attr["by_pricing_model"][0]["pricing_model"] == "distance"
    assert attr["by_pricing_model"][0]["spend_cents"] == 12500

    overview = MerchantReportsService().invoice_reports(db, ctx)
    assert overview["spend_by_channel"]
    assert overview["top_pricing_bands"]


def test_fsa_bands_from_dropoff(db):
    ctx = _merchant_ctx(db, pricing_model="fsa")
    _order(
        db,
        ctx.merchant.id,
        source=OrderSource.SHOPIFY.value,
        amount=6100,
        dropoff=_addr(postal_code="M5V 1E3"),
    )
    _order(
        db,
        ctx.merchant.id,
        source=OrderSource.API.value,
        amount=2000,
        dropoff=_addr(postal_code="L5B2C9"),
    )
    db.commit()
    bands = top_pricing_bands(db, ctx.merchant.id)
    assert bands[0]["pricing_model"] == "fsa"
    by_band = {r["band"]: r["spend_cents"] for r in bands}
    assert by_band["M5V"] == 6100
    assert by_band["L5B"] == 2000
