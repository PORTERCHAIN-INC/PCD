"""Phase A Shopify upgrades: market-driven shipping, delivery promise, tracking sync, returns."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.dialects import postgresql

from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.admin_engine.settings_bindings import resolve_writable_config_key
from porterchain_api.admin_engine.settings_service import AdminSettingsService
from porterchain_api.admin_models import AdminUser
from porterchain_api.booking_models import Order
from porterchain_api.domain.admin_states import AdminRole
from porterchain_api.domain.pricing_version import SUPER_ADMIN_ONLY
from porterchain_api.domain.states import OrderSource, OrderState
from porterchain_api.merchant_engine import return_service as returns
from porterchain_api.merchant_engine import shopify_fulfillment_ops as ops
from porterchain_api.merchant_engine.booking_service import MerchantBookingService
from porterchain_api.merchant_engine.orders_service import MerchantOrdersService
from porterchain_api.merchant_engine.shopify_one_click import go_live_advisories
from porterchain_api.merchant_engine.shopify_urls import has_returns_scope, oauth_scopes
from porterchain_api.platform.delivery_promise import checkout_promise
from porterchain_api.schemas_merchant import AddressInput, MerchantBookDeliveryRequest

_PROMISE = {
    "enabled": True,
    "waves": [{"code": "pm", "cutoff": "11:00", "start": "14:00", "end": "21:00"}],
    "operating_weekdays": [0, 1, 2, 3, 4, 5],
}


def _settings(**extra):
    base = dict(
        shopify_api_scopes="read_orders,write_fulfillments,write_shipping,read_returns",
        shopify_api_version="2026-10",
        shopify_returns_scope_enabled=False,
        website_url="https://porterchain.com/",
    )
    base.update(extra)
    return SimpleNamespace(**base)


# ── A1: market-driven shipping / API 2026-10 / returns scope ──────────────


def test_default_api_version_is_2026_10() -> None:
    from porterchain_api.config import Settings

    # Field defaults (a local .env may still pin SHOPIFY_API_VERSION).
    assert Settings.model_fields["shopify_api_version"].default == "2026-10"
    assert Settings.model_fields["shopify_returns_scope_enabled"].default is False


def test_read_returns_requested_only_when_flag_on() -> None:
    assert "read_returns" not in oauth_scopes(_settings())
    assert oauth_scopes(_settings(shopify_returns_scope_enabled=True)).endswith(",read_returns")
    assert has_returns_scope("read_orders, read_returns")
    assert not has_returns_scope("read_orders")
    assert not has_returns_scope(None)


def test_go_live_advisories_never_block() -> None:
    checks = {"carrier_registered": True}
    assert go_live_advisories(_settings(), checks, []) == ["carrier_rates_enable_in_shipping"]
    assert go_live_advisories(_settings(shopify_api_version="2026-07"), checks, []) == []
    shops = [SimpleNamespace(scopes="read_orders")]
    out = go_live_advisories(_settings(shopify_returns_scope_enabled=True), {}, shops)
    assert out == ["returns_scope_reapprove"]
    granted = [SimpleNamespace(scopes="read_orders,read_returns")]
    assert go_live_advisories(_settings(shopify_returns_scope_enabled=True), {}, granted) == []


def _register(scopes: str):
    shop = SimpleNamespace(shop_domain="x.myshopify.com", scopes=scopes)
    helpers = SimpleNamespace(_admin_get=MagicMock(return_value={"webhooks": []}), _admin_post=MagicMock(return_value={}))
    with (
        patch.object(ops, "access_token_for", return_value="tok"),
        patch.object(ops, "_helpers", return_value=helpers),
        patch.object(ops, "webhook_url", return_value="https://api/x"),
        patch("porterchain_api.merchant_engine.shopify_admin_graphql.webhook_subscriptions_ensure") as ensure,
    ):
        ops._register_webhooks(shop, SimpleNamespace(shopify_fulfillment_service_enabled=False))
    topics = [c.args[4]["webhook"]["topic"] for c in helpers._admin_post.call_args_list]
    return topics, ensure


def test_returns_webhooks_use_graphql_and_need_scope() -> None:
    topics, ensure = _register("read_orders")
    assert not any(t.startswith("returns/") for t in topics)
    ensure.assert_not_called()
    topics, ensure = _register("read_orders,read_returns")
    assert not any(t.startswith("returns/") for t in topics)
    assert ensure.call_args.kwargs["topics"] == ["RETURNS_APPROVE", "RETURNS_CANCEL"]


def test_webhook_subscriptions_ensure_creates_only_missing() -> None:
    from porterchain_api.merchant_engine import shopify_admin_graphql as gql

    calls = []

    def fake(shop, token, settings, query, variables=None):
        calls.append(variables)
        if "webhookSubscriptions(" in query:
            return {"webhookSubscriptions": {"nodes": [{"topic": "RETURNS_APPROVE", "uri": "https://api/x"}]}}
        return {"webhookSubscriptionCreate": {"webhookSubscription": {"id": "gid://1"}, "userErrors": []}}

    with patch.object(gql, "admin_graphql", side_effect=fake):
        created = gql.webhook_subscriptions_ensure(
            "x", "t", None, topics=["RETURNS_APPROVE", "RETURNS_CANCEL"], uri="https://api/x"
        )
    assert created == ["RETURNS_CANCEL"]
    assert calls[-1]["sub"] == {"uri": "https://api/x", "format": "JSON"}


# ── A2: delivery promise (settings + checkout) ────────────────────────────


@pytest.fixture(autouse=True)
def _no_saved_promise(db):
    """set_config commits; keep the promise row from leaking into other tests."""
    from porterchain_api.admin_models import SystemConfig

    def _wipe():
        db.rollback()
        db.query(SystemConfig).filter(SystemConfig.key == "delivery_promise").delete()
        db.commit()

    _wipe()
    yield
    _wipe()


def _admin(db, role: AdminRole) -> AdminContext:
    suffix = uuid4().hex[:8]
    user = AdminUser(
        clerk_user_id=f"clerk_{role.value}_{suffix}",
        email=f"{role.value}-{suffix}@svc.test".lower(),
        name="Promise test",
        role=role.value,
        is_active=True,
    )
    db.add(user)
    db.flush()
    return AdminContext(user=user, role=role)


def test_delivery_promise_setting_is_super_admin_only_and_off_by_default(db, admin_ctx) -> None:
    svc = AdminSettingsService()
    assert resolve_writable_config_key("delivery_promise", reason="x") == "delivery_promise"
    assert svc.get_config_value(db, "delivery_promise")["enabled"] is False
    with pytest.raises(PermissionError, match=SUPER_ADMIN_ONLY):
        svc.set_config(db, _admin(db, AdminRole.ADMIN), "delivery_promise", _PROMISE, reason="nope")
    with pytest.raises(ValueError):
        svc.set_config(db, admin_ctx, "delivery_promise", {"enabled": True, "waves": [{"cutoff": "25:00"}]}, reason="bad")
    saved = svc.set_config(db, admin_ctx, "delivery_promise", _PROMISE, reason="promise on")
    assert saved.value["enabled"] is True
    assert saved.value["timezone"] == "America/Toronto"


def test_checkout_promise_reads_setting(db, admin_ctx) -> None:
    assert checkout_promise(db, dest_fsa="M5V") is None  # absent -> caller keeps old window
    AdminSettingsService().set_config(db, admin_ctx, "delivery_promise", _PROMISE, reason="on")
    db.flush()
    # Tue 2026-10-06 10:00 Toronto: before the 11:00 cut-off.
    morning = datetime(2026, 10, 6, 14, 0, tzinfo=UTC)
    p = checkout_promise(db, dest_fsa="M5V", now=morning)
    assert p.service_code == "porterchain_same_day"
    late = morning + timedelta(hours=4)
    assert checkout_promise(db, dest_fsa="M5V", now=late).service_code == "porterchain_next_day"


def test_checkout_promise_never_raises() -> None:
    db = MagicMock()
    db.query.side_effect = RuntimeError("db down")
    assert checkout_promise(db, dest_fsa="M5V") is None


def _carrier_call(promise):
    from porterchain_api.integrations import shopify_carrier_rates as mod
    from porterchain_api.domain.merchant_states import MerchantStatus

    import base64, hashlib, hmac, json

    db = MagicMock()
    db.get.return_value = SimpleNamespace(id="m1", status=MerchantStatus.ACTIVE.value)
    shop = SimpleNamespace(id="s1", merchant_id="m1", shop_domain="x.myshopify.com", encrypted_webhook_secret=None)
    pickup = SimpleNamespace(formatted="100 King St W, Toronto", postal="M5X1A9", lat=43.648, lng=-79.381)
    payload = {
        "rate": {
            "currency": "USD",
            "destination": {"postal_code": "M5V 1A1", "country": "CA", "province": "ON", "city": "Toronto", "address1": "1 Queen St W"},
            "items": [{"grams": 1000, "quantity": 1}],
        }
    }
    body = json.dumps(payload).encode()
    sig = base64.b64encode(hmac.new(b"shpss", body, hashlib.sha256).digest()).decode()
    persist = MagicMock(return_value=SimpleNamespace(id="q1"))
    with (
        patch.object(mod, "_active_shop", return_value=shop),
        patch.object(mod, "default_pickup_address", return_value=pickup),
        patch.object(mod, "address_from_saved", side_effect=lambda r: r),
        patch.object(mod, "ensure_shop_pickup_bound", side_effect=lambda db, s, address: s),
        patch.object(mod, "_ensure_geo", side_effect=lambda a: a),
        patch.object(mod, "quote_merchant_rate", return_value=(5200, {"final_cents": 5200})),
        patch.object(mod, "persist_rate_quote", persist),
        patch.object(mod, "_checkout_promise", return_value=promise),
    ):
        out = mod.carrier_service_rates(
            db, SimpleNamespace(shopify_api_secret="shpss", jwt_secret="x" * 32),
            raw_body=body, hmac_header=sig, shop_domain="x.myshopify.com", payload=payload,
        )
    return out, persist


def test_carrier_rate_always_cad_and_keeps_old_window_without_promise() -> None:
    out, persist = _carrier_call(None)
    rate = out["rates"][0]
    assert rate["currency"] == "CAD"
    assert rate["service_code"] == "porterchain_same_day"
    assert persist.call_args.kwargs["breakdown"]["request_currency"] == "USD"
    assert "promise" not in persist.call_args.kwargs["breakdown"]


def test_carrier_rate_uses_promise_when_enabled() -> None:
    from porterchain_pricing.delivery_promise import compute_delivery_promise

    promise = compute_delivery_promise(_PROMISE, now=datetime(2026, 10, 6, 18, 0, tzinfo=UTC))
    out, persist = _carrier_call(promise)
    rate = out["rates"][0]
    assert rate["service_code"] == "porterchain_next_day"
    assert rate["service_name"] == "PorterChain Next Day"
    assert rate["min_delivery_date"].startswith("2026-10-07 14:00:00")
    assert rate["max_delivery_date"].startswith("2026-10-07 21:00:00")
    assert persist.call_args.kwargs["breakdown"]["promise"]["kind"] == "next_day"


# ── A3: tracking sync ─────────────────────────────────────────────────────


def test_last_mile_states_map_to_out_for_delivery() -> None:
    assert ops.fulfillment_event_status("IN_TRANSIT") == "OUT_FOR_DELIVERY"
    assert ops.fulfillment_event_status("FAILED", "order.delivery_failed") == "FAILURE"
    assert ops.fulfillment_event_status("PICKED_UP") == "CARRIER_PICKED_UP"


def test_tracking_url_points_at_pcd_tracking_page() -> None:
    assert ops.public_tracking_url(_settings(), "PC123") == "https://porterchain.com/track/PC123"


def test_retry_backoff_and_give_up() -> None:
    now = datetime(2026, 10, 9, 12, 0, tzinfo=UTC)
    meta: dict = {}
    ops.schedule_sync_retry(meta, "update_tracking_failed", "order.delivered", now=now)
    assert meta["sync_retry"]["attempts"] == 1
    assert meta["sync_retry"]["due_at"] == (now + timedelta(seconds=60)).isoformat()
    for _ in range(len(ops.SYNC_RETRY_BACKOFF_SECONDS) - 1):
        ops.schedule_sync_retry(meta, "update_tracking_failed", None, now=now)
    assert meta["sync_retry"]["attempts"] == len(ops.SYNC_RETRY_BACKOFF_SECONDS)
    assert meta["sync_retry"]["event_type"] == "order.delivered"
    ops.schedule_sync_retry(meta, "update_tracking_failed", None, now=now)
    assert "sync_retry" not in meta and meta["sync_gave_up_at"]
    ops.schedule_sync_retry(meta, "missing_shopify_ids", None, now=now)
    assert "sync_retry" not in meta  # not retryable


def _shopify_order(**meta) -> SimpleNamespace:
    return SimpleNamespace(
        id="o1",
        state=OrderState.DELIVERED.value,
        order_source=OrderSource.SHOPIFY.value,
        tracking_number="PC1",
        purchase_order_number="555",
        dropoff={"lat": 43.6, "lng": -79.4},
        compliance_metadata={"shopify": {"shop_domain": "x.myshopify.com", "order_id": "555", **meta}},
    )


def test_event_push_is_idempotent_and_failures_schedule_retry() -> None:
    order = _shopify_order(fulfillment_id="gid://F/1")
    shop = SimpleNamespace(shop_domain="x.myshopify.com")
    with (
        patch("porterchain_api.merchant_engine.shopify_admin_graphql.fulfillment_event_create") as create,
        patch("sqlalchemy.orm.object_session", return_value=None),
    ):
        ops._emit_fulfillment_event(None, _settings(), order, shop, "t", event_type="order.delivered")
        ops._emit_fulfillment_event(None, _settings(), order, shop, "t", event_type="order.delivered")
    assert create.call_count == 1
    assert order.compliance_metadata["shopify"]["pushed_event_statuses"] == ["DELIVERED"]

    order2 = _shopify_order(fulfillment_id="gid://F/2")
    with (
        patch(
            "porterchain_api.merchant_engine.shopify_admin_graphql.fulfillment_event_create",
            side_effect=RuntimeError("boom"),
        ),
        patch("sqlalchemy.orm.object_session", return_value=None),
    ):
        ops._emit_fulfillment_event(None, _settings(), order2, shop, "t", event_type="order.delivered")
    retry = order2.compliance_metadata["shopify"]["sync_retry"]
    assert retry["code"] == "event_push_failed" and retry["event_type"] == "order.delivered"


def test_tracking_update_failure_schedules_retry_then_success_clears() -> None:
    order = _shopify_order(fulfillment_id="gid://F/3")
    db = MagicMock()
    helpers = SimpleNamespace(_active_shop=MagicMock(return_value=SimpleNamespace(shop_domain="x.myshopify.com")))
    with (
        patch.object(ops, "_helpers", return_value=helpers),
        patch.object(ops, "access_token_for", return_value="tok"),
        patch.object(ops, "_push_tracking", return_value=False),
    ):
        ops.push_fulfillment(db, _settings(), order, event_type="order.delivered")
    assert order.compliance_metadata["shopify"]["sync_retry"]["attempts"] == 1
    with (
        patch.object(ops, "_helpers", return_value=helpers),
        patch.object(ops, "access_token_for", return_value="tok"),
        patch.object(ops, "_push_tracking", return_value=True),
        patch.object(ops, "_emit_fulfillment_event"),
        patch.object(ops, "_push_reverse_tracking"),
    ):
        ops.push_fulfillment(db, _settings(), order, event_type="order.delivered")
    assert "sync_retry" not in order.compliance_metadata["shopify"]


def test_retry_sweep_query_compiles_and_only_pushes_due(db) -> None:
    now = datetime(2026, 10, 9, 12, 0, tzinfo=UTC)
    due = _shopify_order(sync_retry={"due_at": (now - timedelta(seconds=1)).isoformat(), "event_type": "order.delivered"})
    later = _shopify_order(sync_retry={"due_at": (now + timedelta(hours=1)).isoformat()})
    fake = MagicMock()
    fake.query.return_value.filter.return_value.filter.return_value.limit.return_value.all.return_value = [due, later]
    with patch.object(ops, "push_fulfillment") as push:
        out = ops.sweep_fulfillment_retries(fake, _settings(), now=now)
    assert out == {"due": 1, "retried": 1}
    assert push.call_args.kwargs["event_type"] == "order.delivered"
    # Real query against Postgres: no rows, but the JSON path filter must be valid SQL.
    assert ops.sweep_fulfillment_retries(db, _settings(), now=now) == {"due": 0, "retried": 0}
    expr = Order.compliance_metadata["shopify"]["sync_retry"].isnot(None)
    assert "IS NOT NULL" in str(expr.compile(dialect=postgresql.dialect()))


def test_failed_delivery_events_reach_shopify_handler() -> None:
    from porterchain_event_bus import handlers
    from porterchain_event_bus.registry import HandlerRegistry

    registry = HandlerRegistry()
    with (
        patch.object(handlers, "get_handler_registry", return_value=registry),
        patch.object(handlers, "_default_handlers_registered", False),
    ):
        handlers.register_default_handlers()
    _handle_shopify_fulfillment = handlers._handle_shopify_fulfillment
    for event in ("order.failed", "order.delivery_failed", "order.in_transit"):
        assert _handle_shopify_fulfillment in registry.handlers_for(event)


# ── A4: returns ───────────────────────────────────────────────────────────


def _body() -> MerchantBookDeliveryRequest:
    return MerchantBookDeliveryRequest(
        pickup=AddressInput(formatted="100 King St W, Toronto", postal="M5X 1A1", lat=43.65, lng=-79.38),
        dropoff=AddressInput(formatted="200 Bay St, Toronto", postal="M5J 2J2", lat=43.65, lng=-79.38),
        scheduled_at=datetime.now(UTC),
        vehicle_class="cargo_van",
    )


@pytest.fixture
def delivered(db, settings, merchant_ctx, monkeypatch) -> Order:
    merchant_ctx.merchant.payment_terms = "NET_30"
    db.commit()
    monkeypatch.setattr(
        "porterchain_api.merchant_engine.booking_service.transition_to_dispatch_ready",
        lambda *_a, **_k: None,
    )
    order = MerchantBookingService().create_shipment(db, settings, merchant_ctx, _body(), sandbox=True)
    order.state = OrderState.DELIVERED.value
    db.commit()
    return order


def test_return_body_swaps_addresses(delivered) -> None:
    body = returns.return_body(delivered)
    assert body.pickup.formatted.startswith("200 Bay St")
    assert body.dropoff.formatted.startswith("100 King St W")
    assert body.internal_reference.startswith("return-")


def test_portal_return_books_priced_linked_order(db, settings, merchant_ctx, delivered) -> None:
    svc = MerchantOrdersService()
    row = svc.create_return_owned(db, settings, merchant_ctx, delivered.id)
    ret = db.get(Order, row["order_id"])
    assert ret.pickup["formatted"].startswith("200 Bay St")
    assert ret.amount_cents and ret.amount_cents > 0  # same pricing engine
    assert ret.is_sandbox is True  # inherits env
    assert ret.compliance_metadata["return"]["of"] == delivered.id
    assert row["source"] == "portal" and row["pricing_note"] is None
    db.refresh(delivered)
    listed = svc.returns_owned(db, merchant_ctx, delivered.id)
    assert [r["order_id"] for r in listed] == [ret.id]
    with pytest.raises(ValueError, match="return_already_open"):
        svc.create_return_owned(db, settings, merchant_ctx, delivered.id)
    with pytest.raises(ValueError, match="return_of_return"):
        svc.create_return_owned(db, settings, merchant_ctx, ret.id)


def test_return_needs_delivered_order(db, settings, merchant_ctx, delivered) -> None:
    delivered.state = OrderState.IN_TRANSIT.value
    db.commit()
    with pytest.raises(ValueError, match="return_not_delivered"):
        MerchantOrdersService().create_return_owned(db, settings, merchant_ctx, delivered.id)
    assert returns.return_error_message("return_not_delivered").startswith("A return")


def test_contract_merchant_return_is_flagged_not_repriced(db, settings, merchant_ctx) -> None:
    merchant_ctx.merchant.pricing_config = {"schedule": {"contract_schedule": "kaylulu-2026-09"}}
    assert returns.has_contract_schedule(merchant_ctx.merchant)
    merchant_ctx.merchant.pricing_config = {}
    assert not returns.has_contract_schedule(merchant_ctx.merchant)
    original = SimpleNamespace(
        id="orig", tracking_number="PC9", is_sandbox=True, compliance_metadata={},
        pickup={"formatted": "100 King St W, Toronto", "postal": "M5X 1A1"},
        dropoff={"formatted": "200 Bay St, Toronto", "postal": "M5J 2J2"},
        purchase_order_number=None,
    )
    merchant_ctx.merchant.pricing_config = {"schedule": {"contract_schedule": "kaylulu-2026-09"}}
    booked = SimpleNamespace(id="ret", tracking_number="PC10", compliance_metadata={})
    booking = MagicMock()
    booking.create_shipment.return_value = booked
    with (
        patch.object(returns, "flag_modified"),
        patch("porterchain_api.merchant_engine.service_area.assert_ontario_booking"),
        patch("porterchain_api.merchant_engine.service_area.merchant_coverage_fsas", return_value=frozenset()),
    ):
        out = returns.create_return_order(
            MagicMock(), settings, merchant_ctx, original, source="shopify",
            idempotency_key="k", booking=booking, extra={"shopify_return_id": "r1"},
        )
    assert out.compliance_metadata["return"]["pricing_note"] == returns.CONTRACT_RETURN_NOTE
    assert out.compliance_metadata["return"]["shopify_return_id"] == "r1"
    assert original.compliance_metadata["returns"][0]["order_id"] == "ret"
    assert booking.create_shipment.call_args.kwargs["idempotency_key"] == "k"


def test_return_routes_are_mounted() -> None:
    from porterchain_api.routers.merchant import router

    routes = {(r.path, m) for r in router.routes for m in getattr(r, "methods", set()) or set()}
    assert any(p.endswith("/orders/{order_id}/returns") and m == "POST" for p, m in routes)
    assert any(p.endswith("/orders/{order_id}/returns") and m == "GET" for p, m in routes)


def test_worker_sweeps_shopify_retries_once_a_minute(monkeypatch) -> None:
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parents[4] / "apps" / "worker" / "run.py"
    spec = importlib.util.spec_from_file_location("pcd_worker_run", path)
    worker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(worker)

    calls = []
    monkeypatch.setattr(worker, "_last_shopify_sync_retry_at", 0.0)
    monkeypatch.setattr(
        "porterchain_api.merchant_engine.shopify_fulfillment_ops.sweep_fulfillment_retries",
        lambda db, settings: calls.append(1) or {"due": 2, "retried": 2},
    )
    assert worker._drain_shopify_fulfillment_retries() == 2
    assert worker._drain_shopify_fulfillment_retries() == 0  # throttled
    assert len(calls) == 1
