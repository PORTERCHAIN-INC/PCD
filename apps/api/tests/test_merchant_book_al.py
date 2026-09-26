"""AL — pickup window and parcel lines on a single book."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import pytest

from porterchain_api.admin_engine.scheduled_batches_service import _pickup_window
from porterchain_api.domain.merchant_states import MerchantRole, MerchantStatus
from porterchain_api.fleetbase_engine.merchant_sync_service import BookingValidationError
from porterchain_api.merchant_engine.booking_flow_service import MerchantBookingFlowService
from porterchain_api.merchant_engine.booking_service import (
    MerchantBookingService,
    assert_pickup_window,
)
from porterchain_api.merchant_engine.parcel_amend_service import commercial_stops, packages_from_order
from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_api.merchant_models import Merchant, MerchantUser
from porterchain_api.schemas_merchant import AddressInput, MerchantBookDeliveryRequest, RouteImportPackageInput


def _ctx(db) -> MerchantContext:
    suffix = uuid4().hex[:8]
    merchant = Merchant(
        company_name=f"AL Co {suffix}",
        email=f"al-{suffix}@test.local",
        status=MerchantStatus.ACTIVE.value,
        profile={},
    )
    db.add(merchant)
    db.flush()
    user = MerchantUser(
        merchant_id=merchant.id,
        clerk_user_id=f"clerk_{suffix}",
        email=f"owner-{suffix}@test.local",
        role=MerchantRole.OWNER.value,
    )
    db.add(user)
    db.flush()
    return MerchantContext(merchant=merchant, user=user, role=MerchantRole.OWNER)


def _body(**extra: object) -> MerchantBookDeliveryRequest:
    payload = dict(
        pickup=AddressInput(formatted="100 King St W, Toronto", postal="M5X 1A1", lat=43.65, lng=-79.38),
        dropoff=AddressInput(formatted="200 Bay St, Toronto", postal="M5J 2J2", lat=43.65, lng=-79.38),
        scheduled_at=datetime(2026, 9, 10, 12, 0, tzinfo=UTC),
        vehicle_class="cargo_van",
        package_type="looseParcel",
    )
    payload.update(extra)
    return MerchantBookDeliveryRequest(**payload)


def test_pickup_window_requires_ready_from() -> None:
    with pytest.raises(BookingValidationError) as exc:
        assert_pickup_window(
            _body(pickup_window_end=datetime(2026, 9, 11, 16, 0, tzinfo=UTC))
        )
    assert "ready" in exc.value.message.lower()


def test_pickup_window_end_must_follow_start() -> None:
    with pytest.raises(BookingValidationError) as exc:
        assert_pickup_window(
            _body(
                pickup_window_start=datetime(2026, 9, 11, 16, 0, tzinfo=UTC),
                pickup_window_end=datetime(2026, 9, 11, 13, 0, tzinfo=UTC),
            )
        )
    assert "after ready from" in exc.value.message


def test_create_shipment_writes_stops_window_and_parcels(db, settings) -> None:
    ctx = _ctx(db)
    start = datetime(2026, 9, 11, 13, 0, tzinfo=UTC)
    end = datetime(2026, 9, 11, 16, 0, tzinfo=UTC)
    with patch(
        "porterchain_api.merchant_engine.booking_service.transition_to_dispatch_ready",
        side_effect=lambda db, order, **_k: order,
    ):
        order = MerchantBookingService().create_shipment(
            db,
            settings,
            ctx,
            _body(
                pickup_window_start=start,
                pickup_window_end=end,
                packages=[
                    RouteImportPackageInput(
                        name="Lab kit",
                        sku="KIT-1",
                        weight_kg=2.5,
                        length_cm=30,
                        width_cm=20,
                        height_cm=10,
                    )
                ],
            ),
        )
    meta = order.compliance_metadata or {}
    stops = meta.get("stops") or []
    assert len(stops) == 2
    pickup = stops[0]
    assert pickup.get("type") == "pickup"
    assert pickup.get("time_window_start")
    assert pickup.get("time_window_end")
    assert pickup["packages"][0]["name"] == "Lab kit"
    assert pickup["packages"][0]["weight_kg"] == 2.5
    assert meta.get("weight_kg") == 2.5
    assert meta.get("schedule_mode") == "later"
    booked = order.scheduled_at
    expected = start.replace(tzinfo=None) if booked.tzinfo is None else start
    assert booked == expected

    cargo = commercial_stops(order)
    assert cargo[0]["stop_type"] == "pickup"
    assert cargo[0]["time_window_start"]
    assert cargo[0]["packages"][0]["sku"] == "KIT-1"
    pkgs = packages_from_order(order)
    assert len(pkgs) == 1
    win_start, win_end = _pickup_window(order)
    assert win_start
    assert win_end


def test_empty_default_parcel_is_not_persisted(db, settings) -> None:
    ctx = _ctx(db)
    with patch(
        "porterchain_api.merchant_engine.booking_service.transition_to_dispatch_ready",
        side_effect=lambda db, order, **_k: order,
    ):
        order = MerchantBookingService().create_shipment(
            db,
            settings,
            ctx,
            _body(packages=[RouteImportPackageInput(name="Parcel", quantity=1)]),
        )
    pickup = (order.compliance_metadata or {}).get("stops")[0]
    assert pickup["packages"] == []


def test_duplicate_restores_window_and_parcels(db, settings) -> None:
    ctx = _ctx(db)
    start = datetime(2026, 9, 12, 14, 0, tzinfo=UTC)
    end = datetime(2026, 9, 12, 17, 0, tzinfo=UTC)
    with patch(
        "porterchain_api.merchant_engine.booking_service.transition_to_dispatch_ready",
        side_effect=lambda db, order, **_k: order,
    ):
        original = MerchantBookingService().create_shipment(
            db,
            settings,
            ctx,
            _body(
                pickup_window_start=start,
                pickup_window_end=end,
                packages=[RouteImportPackageInput(name="Crate", weight_kg=8, sku="CR-8")],
            ),
        )
        copy = MerchantBookingService().duplicate_order(db, settings, ctx, original)
    assert copy.id != original.id
    pickup = (copy.compliance_metadata or {}).get("stops")[0]
    assert pickup["packages"][0]["sku"] == "CR-8"
    assert pickup.get("time_window_start")
    assert pickup.get("time_window_end")


def test_draft_to_request_restores_window_and_parcels() -> None:
    draft = SimpleNamespace(
        pickup={"formatted": "100 King St W, Toronto", "postal": "M5X 1A1", "lat": 43.65, "lng": -79.38},
        dropoff={"formatted": "200 Bay St, Toronto", "postal": "M5J 2J2", "lat": 43.65, "lng": -79.38},
        additional_stops=[],
        vehicle_class="cargo_van",
        package_type="looseParcel",
        weight_kg=4.5,
        dimensions="1x [parcel]",
        special_instructions=None,
        schedule_mode="later",
    )
    meta = {
        "scheduled_at": "2026-09-11T13:00:00+00:00",
        "pickup_window_start": "2026-09-11T13:00:00+00:00",
        "pickup_window_end": "2026-09-11T16:00:00+00:00",
        "packages": [{"name": "Box", "weight_kg": 4.5, "quantity": 1, "sku": "BOX-1"}],
    }
    req = MerchantBookingFlowService().draft_to_request(draft, meta)
    assert req.pickup_window_start is not None
    assert req.pickup_window_end is not None
    assert req.packages
    assert req.packages[0].sku == "BOX-1"
    assert req.packages[0].weight_kg == 4.5
