"""P0 golden money path: preview routing_source + live confirm → FleetbaseSyncJob.

Complements HS-FB-001 (isolated push_order). This pack goes through create_shipment
then BookingSyncService.push_order (same enqueue as the event-bus handler).
"""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from porterchain_api.config import Settings
from porterchain_api.domain.states import OrderState
from porterchain_api.fleetbase_engine.booking_sync_service import BookingSyncService
from porterchain_api.fleetbase_models import FleetbaseSyncJob
from porterchain_api.merchant_engine.booking_flow_service import MerchantBookingFlowService
from porterchain_api.merchant_engine.booking_service import MerchantBookingService
from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_api.schemas_merchant import (
    AddressInput,
    MerchantBookDeliveryRequest,
    MerchantBookingPreviewResponse,
)


def _settings(**overrides) -> Settings:
    base = dict(
        _env_file=None,
        app_env="local",
        stripe_mock=True,
        jwt_secret="a" * 32,
        fleetbase_dispatch_bridge=True,
        spicedb_enabled=False,
        spicedb_required=False,
    )
    base.update(overrides)
    return Settings(**base)


def _body(**extra: object) -> MerchantBookDeliveryRequest:
    payload = dict(
        pickup=AddressInput(formatted="100 King St W, Toronto, ON", postal="M5X 1A1", lat=43.65, lng=-79.38),
        dropoff=AddressInput(formatted="200 Bay St, Toronto, ON", postal="M5J 2J2", lat=43.66, lng=-79.39),
        scheduled_at=datetime.now(UTC),
        vehicle_class="cargo_van",
        package_type="looseParcel",
    )
    payload.update(extra)
    return MerchantBookDeliveryRequest(**payload)


def _prepare_merchant(db: Session, merchant_ctx: MerchantContext) -> None:
    merchant_ctx.merchant.payment_terms = "NET_30"
    merchant_ctx.merchant.credit_limit_cents = 10_000_000
    db.flush()


def _pricing_stub(*, routing_source: str = "valhalla") -> MagicMock:
    breakdown = SimpleNamespace(
        final_cents=4200,
        metadata={
            "distance_meters": 5400,
            "estimated_duration_minutes": 18,
            "routing_source": routing_source,
        },
    )
    pricing = MagicMock()
    pricing.calculate_merchant.return_value = breakdown
    pricing.to_api_breakdown.return_value = {
        "final_cents": 4200,
        "subtotal_cents": 3700,
        "tax_cents": 500,
        "currency": "cad",
        "items": [],
        "distance_meters": 5400,
    }
    return pricing


@pytest.mark.merchant_p0
@pytest.mark.tc_id("MP-BOOK-002")
def test_preview_exposes_routing_source_never_google(db: Session, merchant_ctx: MerchantContext) -> None:
    """Preview contract: top-level routing_source from MapsService (not Google)."""
    _prepare_merchant(db, merchant_ctx)
    settings = _settings()
    flow = MerchantBookingFlowService()
    pricing = _pricing_stub(routing_source="valhalla")
    validated = SimpleNamespace(contract_id=None, payment_terms="NET_30", warnings=[])

    with (
        patch(
            "porterchain_api.merchant_engine.booking_flow_service.get_pricing_service",
            return_value=pricing,
        ),
        patch.object(flow._booking, "build_pricing_request", return_value=MagicMock()),
        patch.object(flow._sync, "validate_booking", return_value=validated),
        patch.object(
            flow,
            "recommend_vehicle",
            return_value={
                "recommended_vehicle": "cargo_van",
                "preferred_vehicles": [],
                "alternatives": [],
            },
        ),
        patch.object(flow, "validate_addresses", return_value=[]),
    ):
        out = flow.preview(db, settings, merchant_ctx, _body())

    assert out["valid"] is True
    assert out["routing_source"] == "valhalla"
    assert "google" not in (out.get("routing_source") or "").lower()
    assert "routing_source" not in (out.get("pricing_breakdown") or {})
    schema = MerchantBookingPreviewResponse(**out)
    assert schema.routing_source == "valhalla"
    assert "routing_source" in MerchantBookingPreviewResponse.model_fields


@pytest.mark.merchant_p0
@pytest.mark.tc_id("MP-BOOK-004")
def test_live_confirm_path_enqueues_fleetbase_via_event_handler(
    db: Session, merchant_ctx: MerchantContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Live (non-sandbox) create_shipment → event handler → FleetbaseSyncJob pending."""
    _prepare_merchant(db, merchant_ctx)
    settings = _settings()
    pricing = _pricing_stub(routing_source="osrm")
    validated = SimpleNamespace(contract_id=None, payment_terms="NET_30", warnings=[])

    monkeypatch.setattr(
        "porterchain_api.merchant_engine.booking_service.transition_to_dispatch_ready",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr(
        "porterchain_api.merchant_engine.booking_service.get_pricing_service",
        lambda _db: pricing,
    )
    monkeypatch.setattr(
        "porterchain_api.merchant_engine.booking_service.resolve_route_distance",
        lambda *_a, **_k: (1200, 180, "osrm"),
    )
    monkeypatch.setattr(
        "porterchain_api.merchant_engine.booking_service.MerchantSyncService.validate_booking",
        lambda *_a, **_k: validated,
    )

    order = MerchantBookingService().create_shipment(
        db, settings, merchant_ctx, _body(), sandbox=False
    )
    assert order.is_sandbox is False
    assert order.state == OrderState.BOOKED.value

    # push_order is enqueue-only; no adapter HTTP / _bridge needed on this path.
    BookingSyncService().push_order(db, settings, order, commit=False)

    jobs = (
        db.query(FleetbaseSyncJob)
        .filter(FleetbaseSyncJob.idempotency_key == f"order:{order.id}")
        .all()
    )
    assert len(jobs) == 1
    assert jobs[0].status == "pending"
    db.rollback()


@pytest.mark.merchant_p0
@pytest.mark.tc_id("MP-BOOK-004-SANDBOX")
def test_sandbox_confirm_does_not_enqueue_fleetbase(
    db: Session, merchant_ctx: MerchantContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    _prepare_merchant(db, merchant_ctx)
    settings = _settings()
    pricing = _pricing_stub()
    validated = SimpleNamespace(contract_id=None, payment_terms="NET_30", warnings=[])

    def _block(*_a, **_k):
        raise AssertionError("sandbox must not dispatch")

    monkeypatch.setattr(
        "porterchain_api.merchant_engine.booking_service.transition_to_dispatch_ready",
        _block,
    )
    monkeypatch.setattr(
        "porterchain_api.merchant_engine.booking_service.get_pricing_service",
        lambda _db: pricing,
    )
    monkeypatch.setattr(
        "porterchain_api.merchant_engine.booking_service.resolve_route_distance",
        lambda *_a, **_k: (900, 120, "valhalla"),
    )
    monkeypatch.setattr(
        "porterchain_api.merchant_engine.booking_service.MerchantSyncService.validate_booking",
        lambda *_a, **_k: validated,
    )

    order = MerchantBookingService().create_shipment(
        db, settings, merchant_ctx, _body(), sandbox=True
    )
    assert order.is_sandbox is True

    jobs = (
        db.query(FleetbaseSyncJob)
        .filter(FleetbaseSyncJob.idempotency_key == f"order:{order.id}")
        .all()
    )
    assert jobs == []
    db.rollback()
