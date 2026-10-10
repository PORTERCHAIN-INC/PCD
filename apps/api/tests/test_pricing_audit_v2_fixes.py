"""Pricing audit v2 — Shopify pickup trust, order reprice, payment revalidate."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from porterchain_api.booking_engine.quote_service import revalidate_quote_for_payment
from porterchain_api.domain.states import OrderState, QuoteState
from porterchain_api.integrations.shopify_carrier_rates import (
    _request_hash,
    find_quote_for_book,
    pickup_from_rate_quote,
    quote_usable_for_order,
)
from porterchain_api.pricing_engine.quote_bridge import revalidate_retail_quote
from porterchain_api.schemas_merchant import AddressInput


def test_request_hash_is_shop_and_destination_only():
    a = _request_hash(shop_id="s1", merchant_id="m1", dropoff_postal="M5V1A1", weight_kg=1.0)
    b = _request_hash(shop_id="s1", merchant_id="m1", dropoff_postal="M5V 1A1", weight_kg=1.0)
    assert a == b
    other = _request_hash(shop_id="s1", merchant_id="m1", dropoff_postal="L4W1A1", weight_kg=1.0)
    assert a != other


def test_find_quote_for_book_never_returns_unrelated_destination():
    now = datetime.now(UTC)
    wrong = SimpleNamespace(
        id="q-wrong",
        shop_id="s1",
        dropoff_postal="L4W1A1",
        weight_kg="1.0",
        expires_at=now + timedelta(minutes=10),
        created_at=now,
    )
    db = MagicMock()
    q = MagicMock()
    db.query.return_value = q
    q.filter.return_value = q
    q.order_by.return_value = q
    q.limit.return_value = q
    q.all.return_value = [wrong]
    assert find_quote_for_book(db, shop_id="s1", dropoff_postal="M5V1A1", weight_kg=1.0) is None


def test_find_quote_for_book_matches_dest_fsa():
    now = datetime.now(UTC)
    right = SimpleNamespace(
        id="q-right",
        shop_id="s1",
        dropoff_postal="M5V2T6",
        weight_kg="1.0",
        expires_at=now + timedelta(minutes=10),
        created_at=now,
    )
    db = MagicMock()
    q = MagicMock()
    db.query.return_value = q
    q.filter.return_value = q
    q.order_by.return_value = q
    q.limit.return_value = q
    q.all.return_value = [right]
    assert find_quote_for_book(db, shop_id="s1", dropoff_postal="M5V1A1", weight_kg=1.0) is right


def test_quote_usable_for_order_rejects_dest_mismatch_and_expiry():
    now = datetime.now(UTC)
    live = SimpleNamespace(
        shop_id="s1",
        dropoff_postal="M5V1A1",
        expires_at=now + timedelta(minutes=5),
    )
    assert quote_usable_for_order(live, shop_id="s1", dropoff_postal="M5V9Z9")
    assert not quote_usable_for_order(live, shop_id="s1", dropoff_postal="L4W1A1")
    expired = SimpleNamespace(
        shop_id="s1",
        dropoff_postal="M5V1A1",
        expires_at=now - timedelta(minutes=1),
    )
    assert not quote_usable_for_order(expired, shop_id="s1", dropoff_postal="M5V1A1")


def test_pickup_from_rate_quote_requires_in_area_snapshot():
    now = datetime.now(UTC)
    quote = SimpleNamespace(
        expires_at=now + timedelta(minutes=10),
        breakdown={
            "pickup": {
                "formatted": "100 King St W, Toronto",
                "postal": "M5X1A9",
                "lat": 43.648,
                "lng": -79.381,
                "source": "shopify_origin",
            }
        },
    )
    with patch(
        "porterchain_api.integrations.shopify_carrier_rates.service_area_error",
        return_value=None,
    ):
        got = pickup_from_rate_quote(quote)
    assert got is not None
    addr, source = got
    assert isinstance(addr, AddressInput)
    assert source == "shopify_origin"
    assert addr.postal == "M5X1A9"


def test_update_from_shopify_payload_reprices_pre_pickup(monkeypatch):
    from porterchain_api.merchant_engine import shopify_payload_ops as ops

    shop = SimpleNamespace(id="s1", merchant_id="m1", shop_domain="x.myshopify.com", auto_dispatch=True)
    merchant = SimpleNamespace(id="m1", status="ACTIVE")
    order = SimpleNamespace(
        id="o1",
        state=OrderState.BOOKED.value,
        amount_cents=5000,
        dropoff={"formatted": "old", "postal": "M5V1A1", "lat": 43.64, "lng": -79.39},
        pickup={"formatted": "100 King St W", "postal": "M5X1A9", "lat": 43.648, "lng": -79.381},
        weight_kg=1.0,
        compliance_metadata={},
    )
    pickup_row = SimpleNamespace(
        formatted="100 King St W", postal="M5X1A9", lat=43.648, lng=-79.381
    )
    body = SimpleNamespace(
        pickup=AddressInput(formatted="100 King St W", postal="M5X1A9", lat=43.648, lng=-79.381),
        dropoff=AddressInput(formatted="new", postal="M5V2T6", lat=43.64, lng=-79.39),
        weight_kg=2.0,
        vehicle_class="cargo_van",
    )

    db = MagicMock()

    def _query(model):
        m = MagicMock()
        m.filter.return_value = m
        name = getattr(model, "__name__", str(model))
        if name == "Merchant":
            m.first.return_value = merchant
        else:
            m.first.return_value = None  # Invoice lookup
        return m

    db.query.side_effect = _query

    monkeypatch.setattr(ops.shopify, "_active_shop", lambda *a, **k: shop)
    monkeypatch.setattr(ops, "porterchain_shipping_selected", lambda p: True)
    monkeypatch.setattr(ops, "order_ids", lambda p: ("99", "#99"))
    monkeypatch.setattr(ops, "_order_for_shopify", lambda *a, **k: order)
    monkeypatch.setattr(ops.shopify, "default_pickup_address", lambda *a, **k: pickup_row)
    monkeypatch.setattr(
        "porterchain_api.merchant_engine.shopify_one_click.ensure_shop_pickup_bound",
        lambda *a, **k: shop,
    )
    monkeypatch.setattr(ops.shopify, "_ensure_coords", lambda a: a)
    monkeypatch.setattr(ops.shopify, "address_from_saved", lambda r: body.pickup)
    monkeypatch.setattr(ops, "map_shopify_order", lambda payload, pickup: body)
    monkeypatch.setattr(
        "porterchain_api.integrations.shopify_carrier_rates.apply_shopify_book_vehicle",
        lambda m, b, p: b,
    )
    monkeypatch.setattr(ops, "assert_ontario_booking", lambda b, **_: None)
    monkeypatch.setattr(
        "porterchain_api.integrations.shopify_carrier_rates.quote_merchant_rate",
        lambda *a, **k: (6200, {"final_cents": 6200, "metadata": {}}),
    )
    monkeypatch.setattr(ops, "customer_slice", lambda *a, **k: {})
    monkeypatch.setattr(ops, "line_item_slice", lambda *a, **k: [])

    out = ops._update_from_shopify_payload(
        db, SimpleNamespace(), shop_domain="x.myshopify.com", payload={"line_items": []}
    )
    assert out["updated"] is True
    assert out["repriced"] is True
    assert order.amount_cents == 6200
    assert order.compliance_metadata["shopify"]["reprice"]["to_cents"] == 6200


def test_update_from_shopify_payload_locks_price_when_invoiced(monkeypatch):
    from porterchain_api.merchant_engine import shopify_payload_ops as ops

    shop = SimpleNamespace(id="s1", merchant_id="m1", shop_domain="x.myshopify.com")
    merchant = SimpleNamespace(id="m1", status="ACTIVE")
    order = SimpleNamespace(
        id="o1",
        state=OrderState.BOOKED.value,
        amount_cents=5000,
        dropoff={"formatted": "old", "postal": "M5V1A1", "lat": 43.64, "lng": -79.39},
        pickup={"formatted": "100 King St W", "postal": "M5X1A9", "lat": 43.648, "lng": -79.381},
        weight_kg=1.0,
        compliance_metadata={"shopify": {"fo_events": []}},
    )
    pickup_row = SimpleNamespace(
        formatted="100 King St W", postal="M5X1A9", lat=43.648, lng=-79.381
    )
    body = SimpleNamespace(
        pickup=AddressInput(formatted="100 King St W", postal="M5X1A9", lat=43.648, lng=-79.381),
        dropoff=AddressInput(formatted="new", postal="M5V2T6", lat=43.64, lng=-79.39),
        weight_kg=2.0,
        vehicle_class="cargo_van",
    )
    db = MagicMock()

    def _query(model):
        m = MagicMock()
        m.filter.return_value = m
        name = getattr(model, "__name__", str(model))
        if name == "Merchant":
            m.first.return_value = merchant
        else:
            m.first.return_value = ("inv1",)  # has invoice
        return m

    db.query.side_effect = _query

    monkeypatch.setattr(ops.shopify, "_active_shop", lambda *a, **k: shop)
    monkeypatch.setattr(ops, "porterchain_shipping_selected", lambda p: True)
    monkeypatch.setattr(ops, "order_ids", lambda p: ("99", "#99"))
    monkeypatch.setattr(ops, "_order_for_shopify", lambda *a, **k: order)
    monkeypatch.setattr(ops.shopify, "default_pickup_address", lambda *a, **k: pickup_row)
    monkeypatch.setattr(
        "porterchain_api.merchant_engine.shopify_one_click.ensure_shop_pickup_bound",
        lambda *a, **k: shop,
    )
    monkeypatch.setattr(ops.shopify, "_ensure_coords", lambda a: a)
    monkeypatch.setattr(ops.shopify, "address_from_saved", lambda r: body.pickup)
    monkeypatch.setattr(ops, "map_shopify_order", lambda payload, pickup: body)
    monkeypatch.setattr(
        "porterchain_api.integrations.shopify_carrier_rates.apply_shopify_book_vehicle",
        lambda m, b, p: b,
    )
    monkeypatch.setattr(ops, "assert_ontario_booking", lambda b, **_: None)
    monkeypatch.setattr(ops, "customer_slice", lambda *a, **k: {})
    monkeypatch.setattr(ops, "line_item_slice", lambda *a, **k: [])

    out = ops._update_from_shopify_payload(
        db, SimpleNamespace(), shop_domain="x.myshopify.com", payload={"line_items": []}
    )
    assert out["updated"] is True
    assert out["repriced"] is False
    assert order.amount_cents == 5000
    assert order.compliance_metadata["shopify"]["price_locked"] is True


def test_revalidate_retail_quote_rejects_price_change():
    quote = SimpleNamespace(
        id="q1",
        state=QuoteState.QUOTE.value,
        expires_at=datetime.now(UTC) + timedelta(minutes=10),
        amount_cents=5000,
        pickup={"formatted": "A", "postal": "M5V1A1", "lat": 43.64, "lng": -79.39},
        dropoff={"formatted": "B", "postal": "L4W1A1", "lat": 43.58, "lng": -79.64},
        vehicle_class="cargo_van",
        package_type="looseParcel",
        weight_kg=1.0,
        dimensions=None,
        declared_value_cents=None,
        additional_stops=[],
        scheduled_at=datetime.now(UTC),
        schedule_mode="now",
        parcels={"booking_mode": "parcels", "items": []},
        pricing_breakdown={"items": [], "summary": {}},
        distance_meters=1000,
    )
    db = MagicMock()
    breakdown = SimpleNamespace(
        final_cents=5600,
        items=[],
        metadata={"distance_meters": 1200},
    )
    service = MagicMock()
    service.calculate_retail.return_value = breakdown
    service.to_api_breakdown.return_value = {"final_cents": 5600}

    with (
        patch(
            "porterchain_api.pricing_engine.quote_bridge.expire_quote_if_needed",
            return_value=quote,
        ),
        patch(
            "porterchain_api.pricing_engine.quote_bridge.get_pricing_service",
            return_value=service,
        ),
        patch(
            "porterchain_api.pricing_engine.quote_bridge._request_from_quote",
            return_value=SimpleNamespace(routing_source="valhalla"),
        ),pytest.raises(ValueError) as exc
    ):
        revalidate_retail_quote(db, quote)
    assert str(exc.value) == "quote_price_changed:5600"
    assert quote.amount_cents == 5600


def test_revalidate_quote_for_payment_checks_coverage():
    quote = SimpleNamespace(
        id="q1",
        state=QuoteState.QUOTE.value,
        expires_at=datetime.now(UTC) + timedelta(minutes=10),
        amount_cents=5000,
        pickup={"formatted": "A", "postal": "V6B1A1"},
        dropoff={"formatted": "B", "postal": "M5V1A1"},
        parcels={},
        pricing_breakdown={},
    )
    db = MagicMock()
    with (
        patch(
            "porterchain_api.booking_engine.quote_service.expire_quote_if_needed",
            return_value=quote,
        ),
        patch(
            "porterchain_api.admin_engine.platform_settings.address_in_coverage",
            side_effect=lambda db, formatted=None, postal=None, city=None: (postal or "").startswith("M"),
        ),
        patch("porterchain_api.booking_engine.quote_service.revalidate_retail_quote") as price_check,
    ):
        with pytest.raises(ValueError) as exc:
            revalidate_quote_for_payment(db, quote)
    assert str(exc.value) == "pickup_outside_service_area"
    price_check.assert_not_called()


def _repo_root():
    from pathlib import Path

    return Path(__file__).resolve().parents[3]


def test_ts_compact_defaults_match_python_policy():
    import re

    from porterchain_pricing.policy import CompactSchedule

    text = (_repo_root() / "packages/types/src/pricing.ts").read_text(encoding="utf-8")
    c = CompactSchedule()
    assert re.search(rf"parcels_per_stop:\s*{c.parcels_per_stop}\b", text)
    assert re.search(rf"route_minimum_cents:\s*{c.route_minimum_cents}\b", text)
    for band in c.stop_rates:
        stops = "null" if band.max_stops is None else str(band.max_stops)
        assert re.search(rf"max_stops:\s*{stops},\s*cents:\s*{band.cents}\b", text)


def test_ts_default_downtown_fee_matches_engine():
    import re

    from porterchain_pricing.gta_rate import DEFAULT_DOWNTOWN_FEE_CAD

    text = (_repo_root() / "packages/types/src/pricing.ts").read_text(encoding="utf-8")
    m = re.search(r"DEFAULT_DOWNTOWN_FEE_CAD\s*=\s*([\d.]+)", text)
    assert m and float(m.group(1)) == float(DEFAULT_DOWNTOWN_FEE_CAD)


def test_website_fsa_list_matches_engine_including_hub_overrides():
    import re

    from porterchain_pricing.gta150_fsa import gta150_fsa_codes

    text = (_repo_root() / "website/src/lib/seo/gta150FsaCodes.ts").read_text(encoding="utf-8")
    assert "Auto-synced" not in text
    block = re.search(r"GTA150_FSA_CODES\s*=\s*new Set<string>\(\[(.*?)\]\)", text, re.DOTALL)
    assert block
    got = set(re.findall(r'"([A-Z]\d[A-Z])"', block.group(1)))
    assert got == set(gta150_fsa_codes())
    for hub in ("M5D", "M5K", "M5L", "M5W", "M5X"):
        assert hub in got


def test_service_registry_has_no_pricing_and_shim_is_gone():
    from porterchain_services.gateway.registry import ServiceRegistry

    assert not hasattr(ServiceRegistry, "pricing")
    assert not (_repo_root() / "apps/api/src/porterchain_api/services/pricing.py").exists()
