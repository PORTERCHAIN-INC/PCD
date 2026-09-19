"""Rate card read, seats, sandbox dry-run, vehicle IDs, headroom, PO search."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from porterchain_api.booking_engine.numbers import generate_order_number, generate_tracking_number
from porterchain_api.domain.states import OrderState
from porterchain_api.merchant_engine.billing_service import MerchantBillingService
from porterchain_api.merchant_engine.booking_service import MerchantBookingService, _canonical_vehicle
from porterchain_api.merchant_engine.orders_service import MerchantOrderFilters, MerchantOrdersService
from porterchain_api.merchant_engine.rate_card_view import merchant_rate_card
from porterchain_api.merchant_engine.rbac import english_role, forbidden_message
from porterchain_api.merchant_engine.team_service import MerchantTeamService, seat_status, serialize_member
from porterchain_api.merchant_models import MerchantUser
from porterchain_api.booking_models import Order
from porterchain_api.schemas_merchant import AddressInput, MerchantBookDeliveryRequest


def _on_body(**extra: object) -> MerchantBookDeliveryRequest:
    payload = dict(
        pickup=AddressInput(formatted="100 King St W, Toronto", postal="M5X 1A1", lat=43.65, lng=-79.38),
        dropoff=AddressInput(formatted="200 Bay St, Toronto", postal="M5J 2J2", lat=43.65, lng=-79.38),
        scheduled_at=datetime.now(UTC),
        vehicle_class="cargoVan",
    )
    payload.update(extra)
    return MerchantBookDeliveryRequest(**payload)


def test_rate_card_hides_driver_payout(db, merchant_ctx) -> None:
    card = merchant_rate_card(db, merchant_ctx.merchant)
    blob = str(card)
    assert "driver_share" not in blob
    assert "platform_share" not in blob
    assert "driver_payout" not in blob
    assert card["pricing_model"] == "distance"
    assert card["what_wins"]
    assert card["vehicles"]
    assert card["currency"] == "cad"
    ids = {v["id"] for v in card["vehicles"]}
    assert "cargo_van" in ids


def test_canonical_vehicle_maps_catalog_camel_to_matrix(db, merchant_ctx) -> None:
    assert _canonical_vehicle("cargoVan") == "cargo_van"
    assert _canonical_vehicle("highRoof") == "sprinter_van"
    req = MerchantBookingService().build_pricing_request(merchant_ctx, _on_body())
    assert req.vehicle_class == "cargo_van"


def test_sandbox_booking_stays_booked(db, settings, merchant_ctx, monkeypatch) -> None:
    merchant_ctx.merchant.payment_terms = "NET_30"
    db.commit()
    calls: list[str] = []

    def _dispatch(*_a, **_k):
        calls.append("dispatch")
        raise AssertionError("sandbox bookings must not dispatch")

    monkeypatch.setattr(
        "porterchain_api.merchant_engine.booking_service.transition_to_dispatch_ready",
        _dispatch,
    )
    order = MerchantBookingService().create_shipment(
        db, settings, merchant_ctx, _on_body(), sandbox=True
    )
    assert order.state == OrderState.BOOKED.value
    assert order.is_sandbox is True
    # Order.is_sandbox is SoT — do not re-write compliance.sandbox on new books.
    assert (order.compliance_metadata or {}).get("sandbox") is not True
    assert calls == []


def test_sandbox_skips_credit_and_org_preference_no_longer_dry_runs(
    db, settings, merchant_ctx, monkeypatch
) -> None:
    """Org sandbox_mode must not force dry-run; only explicit sandbox= does."""
    from porterchain_api.gateway_engine.merchant_api import set_sandbox_mode

    merchant_ctx.merchant.payment_terms = "NET_30"
    merchant_ctx.merchant.credit_limit_cents = 1
    set_sandbox_mode(merchant_ctx.merchant, True)
    db.commit()

    dispatched: list[str] = []

    def _dispatch(*_a, **_k):
        dispatched.append("dispatch")

    monkeypatch.setattr(
        "porterchain_api.merchant_engine.booking_service.transition_to_dispatch_ready",
        _dispatch,
    )
    live = MerchantBookingService().create_shipment(
        db, settings, merchant_ctx, _on_body(), sandbox=False
    )
    assert live.is_sandbox is False
    assert dispatched == ["dispatch"]

    dispatched.clear()

    def _block(*_a, **_k):
        raise AssertionError("sandbox bookings must not dispatch")

    monkeypatch.setattr(
        "porterchain_api.merchant_engine.booking_service.transition_to_dispatch_ready",
        _block,
    )
    test = MerchantBookingService().create_shipment(
        db, settings, merchant_ctx, _on_body(), sandbox=True
    )
    assert test.is_sandbox is True
    assert dispatched == []


def test_duplicate_inherits_sandbox(db, settings, merchant_ctx, monkeypatch) -> None:
    merchant_ctx.merchant.payment_terms = "NET_30"
    db.commit()

    def _block(*_a, **_k):
        raise AssertionError("sandbox must not dispatch")

    monkeypatch.setattr(
        "porterchain_api.merchant_engine.booking_service.transition_to_dispatch_ready",
        _block,
    )
    original = MerchantBookingService().create_shipment(
        db, settings, merchant_ctx, _on_body(), sandbox=True
    )
    copy = MerchantBookingService().duplicate_order(db, settings, merchant_ctx, original)
    assert copy.is_sandbox is True
    assert copy.id != original.id


def test_seat_status_pending_active_off(db, merchant_ctx) -> None:
    pending = MerchantUser(
        merchant_id=merchant_ctx.merchant.id,
        clerk_user_id="pending:ops@example.com",
        email="ops@example.com",
        role="merchant_ops",
        is_active=True,
    )
    db.add(pending)
    db.flush()
    assert seat_status(pending) == "pending"
    assert serialize_member(pending)["role_label"] == "Dispatcher"

    merchant_ctx.user.is_active = False
    db.flush()
    assert seat_status(merchant_ctx.user) == "off"

    seats = MerchantTeamService().list_seats(db, merchant_ctx)
    statuses = {s.email: seat_status(s) for s in seats}
    assert "ops@example.com" in statuses
    assert statuses["ops@example.com"] == "pending"


def test_available_credit_headroom(db, merchant_ctx) -> None:
    merchant_ctx.merchant.credit_limit_cents = 50_000
    db.commit()
    overview = MerchantBillingService().overview(db, merchant_ctx)
    assert overview["credit_limit_cents"] == 50_000
    assert overview["available_credit_cents"] == max(
        0, 50_000 - int(overview["outstanding_balance_cents"])
    )
    assert overview["headroom_cents"] == overview["available_credit_cents"]


def test_orders_search_finds_po_and_cost_centre(db, merchant_ctx) -> None:
    order = Order(
        order_number=generate_order_number(),
        tracking_number=generate_tracking_number(),
        state=OrderState.BOOKED.value,
        merchant_id=merchant_ctx.merchant.id,
        amount_cents=1200,
        pickup={"formatted": "100 King St W"},
        dropoff={"formatted": "200 Bay St"},
        scheduled_at=datetime.now(UTC),
        purchase_order_number="PO-7788",
        cost_centre="CC-42",
        internal_reference="JOB-9",
    )
    db.add(order)
    db.commit()
    svc = MerchantOrdersService()
    by_po = svc.list_enriched(db, merchant_ctx, MerchantOrderFilters(search="PO-7788"))
    by_cc = svc.list_enriched(db, merchant_ctx, MerchantOrderFilters(search="CC-42"))
    assert any(r["order_id"] == order.id for r in by_po)
    assert any(r["purchase_order_number"] == "PO-7788" for r in by_po)
    assert any(r["cost_centre"] == "CC-42" for r in by_cc)


def test_english_role_and_forbidden_copy() -> None:
    assert english_role("merchant_ops") == "Dispatcher"
    assert english_role("merchant_finance") == "Accounting"
    assert forbidden_message("billing") == "Ask your owner for Accounting access."
    assert forbidden_message("users") == "Ask your owner for Manager access."
    assert "billing" not in forbidden_message("billing")
    assert "merchant_" not in forbidden_message("users")


def test_public_track_hides_sandbox(db, settings, merchant_ctx, monkeypatch) -> None:
    merchant_ctx.merchant.payment_terms = "NET_30"
    db.commit()
    monkeypatch.setattr(
        "porterchain_api.merchant_engine.booking_service.transition_to_dispatch_ready",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no dispatch")),
    )
    order = MerchantBookingService().create_shipment(
        db, settings, merchant_ctx, _on_body(), sandbox=True
    )
    from porterchain_api.booking_engine.tracking_service import TrackingService
    from porterchain_api.merchant_engine.tracking_views import public_track_url

    svc = TrackingService()
    assert svc.get_order_response_by_tracking(db, order.tracking_number) is None
    assert svc.get_order_tracking_response(db, settings, order.tracking_number) is None
    assert public_track_url(settings, order.tracking_number, is_sandbox=True) is None


def test_list_orders_excludes_sandbox_by_default(db, settings, merchant_ctx, monkeypatch) -> None:
    merchant_ctx.merchant.payment_terms = "NET_30"
    db.commit()

    def _ok(*_a, **_k):
        return None

    monkeypatch.setattr(
        "porterchain_api.merchant_engine.booking_service.transition_to_dispatch_ready",
        _ok,
    )
    live = MerchantBookingService().create_shipment(
        db, settings, merchant_ctx, _on_body(), sandbox=False
    )
    monkeypatch.setattr(
        "porterchain_api.merchant_engine.booking_service.transition_to_dispatch_ready",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no dispatch")),
    )
    sand = MerchantBookingService().create_shipment(
        db, settings, merchant_ctx, _on_body(), sandbox=True
    )
    svc = MerchantOrdersService()
    default = svc.list_enriched(db, merchant_ctx, MerchantOrderFilters(limit=100))
    ids = {r["order_id"] for r in default}
    assert live.id in ids
    assert sand.id not in ids
    assert all(not r.get("is_sandbox") for r in default)

    with_sand = svc.list_enriched(
        db, merchant_ctx, MerchantOrderFilters(limit=100, include_sandbox=True)
    )
    with_ids = {r["order_id"] for r in with_sand}
    assert live.id in with_ids
    assert sand.id in with_ids

    only_sand = svc.list_enriched(
        db, merchant_ctx, MerchantOrderFilters(limit=100, sandbox_only=True)
    )
    only_ids = {r["order_id"] for r in only_sand}
    assert sand.id in only_ids
    assert live.id not in only_ids


def test_sandbox_label_watermark_changes_pdf() -> None:
    from porterchain_api.reporting.thermal_pdf import render_thermal_labels

    base = {
        "route_hint": "A",
        "stop_sequence": 1,
        "from_line": "From",
        "to_line": "To",
        "order_number": "ORD-1",
        "tracking_base": "TRK-1",
        "cod_line": "—",
        "qr_payload": "LOGISTICSv1|o|p||||0",
        "tracking_suffix": "TRK-1-01",
        "parcel_index": 1,
        "total_parcels": 1,
    }
    live_pdf = render_thermal_labels([{**base, "is_sandbox": False}])
    sand_pdf = render_thermal_labels([{**base, "is_sandbox": True}])
    assert sand_pdf.startswith(b"%PDF")
    assert len(sand_pdf) > len(live_pdf)


def test_sandbox_simulator_advances_to_delivered(db, settings, merchant_ctx, monkeypatch) -> None:
    merchant_ctx.merchant.payment_terms = "NET_30"
    db.commit()
    monkeypatch.setattr(
        "porterchain_api.merchant_engine.booking_service.transition_to_dispatch_ready",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no dispatch")),
    )
    order = MerchantBookingService().create_shipment(
        db, settings, merchant_ctx, _on_body(), sandbox=True
    )
    from porterchain_api.merchant_engine.sandbox_simulator import simulate_sandbox_lifecycle

    result = simulate_sandbox_lifecycle(
        db,
        settings,
        merchant_ctx,
        order.id,
        deliver_webhooks=False,
        until_state="DELIVERED",
    )
    assert result["final_state"] == OrderState.DELIVERED.value
    assert len(result["steps"]) >= 5
    assert all(s["event_type"].startswith("order.") for s in result["steps"])
    db.refresh(order)
    assert order.state == OrderState.DELIVERED.value
    assert order.is_sandbox is True


def test_owner_required_to_disable_sandbox_preference(db, merchant_ctx) -> None:
    from porterchain_api.domain.merchant_states import MerchantRole
    from porterchain_api.merchant_engine.integrations_service import MerchantIntegrationsService
    from porterchain_api.merchant_engine.rbac import MerchantContext

    svc = MerchantIntegrationsService()
    # OPS may turn preference on
    svc.set_sandbox_mode(db, merchant_ctx, True)
    assert svc.sandbox_status(merchant_ctx)["sandbox_mode"] is True
    with pytest.raises(PermissionError, match="owner_only"):
        svc.set_sandbox_mode(db, merchant_ctx, False)

    owner_ctx = MerchantContext(
        merchant=merchant_ctx.merchant,
        user=merchant_ctx.user,
        role=MerchantRole.OWNER,
    )
    out = svc.set_sandbox_mode(db, owner_ctx, False)
    assert out["sandbox_mode"] is False


def test_production_key_requires_owner(db, merchant_ctx) -> None:
    from porterchain_api.domain.merchant_states import MerchantRole
    from porterchain_api.merchant_engine.api_key_service import MerchantApiKeyService
    from porterchain_api.merchant_engine.rbac import MerchantContext

    svc = MerchantApiKeyService()
    with pytest.raises(PermissionError, match="owner_only"):
        svc.create_key(
            db, merchant_ctx, name="prod", scopes=["shipments:read"], environment="production"
        )
    owner_ctx = MerchantContext(
        merchant=merchant_ctx.merchant,
        user=merchant_ctx.user,
        role=MerchantRole.OWNER,
    )
    record, raw = svc.create_key(
        db, owner_ctx, name="prod", scopes=["shipments:read"], environment="production"
    )
    assert raw.startswith("pk_production_")
    assert record.environment == "production"


def test_privacy_export_labels_sandbox_orders(db, settings, merchant_ctx, monkeypatch) -> None:
    merchant_ctx.merchant.payment_terms = "NET_30"
    db.commit()

    def _ok(*_a, **_k):
        return None

    monkeypatch.setattr(
        "porterchain_api.merchant_engine.booking_service.transition_to_dispatch_ready",
        _ok,
    )
    live = MerchantBookingService().create_shipment(
        db, settings, merchant_ctx, _on_body(), sandbox=False
    )
    monkeypatch.setattr(
        "porterchain_api.merchant_engine.booking_service.transition_to_dispatch_ready",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no dispatch")),
    )
    sand = MerchantBookingService().create_shipment(
        db, settings, merchant_ctx, _on_body(), sandbox=True
    )
    from porterchain_api.merchant_engine.privacy import MerchantPrivacyService

    export = MerchantPrivacyService().export_merchant(
        db, merchant_ctx.merchant, actor_user_id=merchant_ctx.user.id
    )
    by_id = {row["order_id"]: row for row in export["orders_summary"]}
    assert by_id[live.id]["is_sandbox"] is False
    assert by_id[sand.id]["is_sandbox"] is True
    assert export["orders_env_counts"]["sandbox"] >= 1
    assert export["orders_env_counts"]["live"] >= 1
    assert "is_sandbox" in export["retention_note"]


def test_operational_count_ignores_sandbox(db, settings, merchant_ctx, monkeypatch) -> None:
    merchant_ctx.merchant.payment_terms = "NET_30"
    db.commit()
    monkeypatch.setattr(
        "porterchain_api.merchant_engine.booking_service.transition_to_dispatch_ready",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no dispatch")),
    )
    sand = MerchantBookingService().create_shipment(
        db, settings, merchant_ctx, _on_body(), sandbox=True
    )
    from porterchain_api.domain.states import OrderState
    from porterchain_api.merchant_engine.offboard import operational_order_count

    sand.state = OrderState.IN_TRANSIT.value
    db.commit()
    assert operational_order_count(db, merchant_ctx.merchant.id) == 0
