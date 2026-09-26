"""Parcel amend — BOOKED/DISPATCH_READY only, no driver; re-quote; preview stop PATCH locked after confirm."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from porterchain_api.booking_engine.numbers import generate_order_number, generate_tracking_number
from porterchain_api.domain.merchant_states import BulkImportStatus
from porterchain_api.domain.states import OrderState
from porterchain_api.merchant_engine.parcel_amend_service import (
    PARCEL_AMEND_LOCKED,
    ParcelAmendError,
    ParcelAmendService,
    assert_parcel_amendable,
    commercial_stops,
    parcel_amendable,
)
from porterchain_api.merchant_engine.route_import_service import MerchantRouteImportService
from porterchain_api.booking_models import Order


def _stop(seq: int, kind: str, formatted: str, lat: float, lng: float, *, weight: float = 2) -> dict:
    return {
        "sequence": seq,
        "stop_type": kind,
        "address": formatted,
        "formatted": formatted,
        "lat": lat,
        "lng": lng,
        "postal": "M5V 2T6",
        "packages": [
            {
                "name": "Box",
                "weight_kg": weight,
                "length_cm": 30,
                "width_cm": 20,
                "height_cm": 10,
                "package_type": "looseParcel",
                "notes": "fragile",
            }
        ],
    }


def _order(db, merchant_id: str, *, state: str = OrderState.BOOKED.value, driver_id: str | None = None) -> Order:
    order = Order(
        order_number=generate_order_number(),
        tracking_number=generate_tracking_number(),
        state=state,
        merchant_id=merchant_id,
        amount_cents=4000,
        assigned_driver_id=driver_id,
        pickup={"formatted": "100 King St W, Toronto", "lat": 43.6488, "lng": -79.3817, "postal": "M5X 1A9"},
        dropoff={"formatted": "1 Dundas St E, Toronto", "lat": 43.6561, "lng": -79.3802, "postal": "M5B 2R8"},
        scheduled_at=datetime.now(UTC),
        compliance_metadata={
            "vehicle_class": "cargo_van",
            "stops": [
                {
                    "id": "s1",
                    "type": "pickup",
                    "sequence": 1,
                    "formatted": "100 King St W, Toronto",
                    "lat": 43.6488,
                    "lng": -79.3817,
                    "postal_code": "M5X 1A9",
                    "packages": [{"name": "Box", "weight_kg": 2}],
                },
                {
                    "id": "s2",
                    "type": "dropoff",
                    "sequence": 2,
                    "formatted": "1 Dundas St E, Toronto",
                    "lat": 43.6561,
                    "lng": -79.3802,
                    "postal_code": "M5B 2R8",
                    "packages": [{"name": "Crate", "weight_kg": 8}],
                },
            ],
        },
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


def test_parcel_amendable_booked_without_driver(db, merchant_ctx) -> None:
    order = _order(db, merchant_ctx.merchant.id)
    assert parcel_amendable(order) is True
    assert_parcel_amendable(order)
    cargo = commercial_stops(order)
    assert cargo[0]["stop_type"] == "pickup"
    assert cargo[1]["packages"][0]["name"] == "Crate"


def test_parcel_amend_locked_after_driver(db, merchant_ctx, driver) -> None:
    order = _order(db, merchant_ctx.merchant.id, driver_id=driver.id)
    assert parcel_amendable(order) is False
    with pytest.raises(ParcelAmendError, match=PARCEL_AMEND_LOCKED):
        assert_parcel_amendable(order)


def test_parcel_amend_locked_in_transit(db, merchant_ctx) -> None:
    order = _order(db, merchant_ctx.merchant.id, state=OrderState.IN_TRANSIT.value)
    with pytest.raises(ParcelAmendError, match=PARCEL_AMEND_LOCKED):
        ParcelAmendService().apply(
            db,
            order,
            [_stop(1, "pickup", "A", 43.65, -79.38), _stop(2, "drop", "B", 43.66, -79.39)],
            merchant_ctx.merchant,
            actor_type="merchant",
            actor_id=merchant_ctx.user.id,
        )


@patch("porterchain_api.merchant_engine.import_quote.MapsService")
@patch("porterchain_api.merchant_engine.import_quote.resolve_route_distance")
@patch("porterchain_api.merchant_engine.import_quote.get_pricing_service")
def test_amend_requotes_amount(mock_pricing, mock_dist, mock_maps, db, merchant_ctx) -> None:
    mock_dist.return_value = (18000, 2400, "valhalla")
    mock_maps.return_value.route_multi.side_effect = RuntimeError("no valhalla in tests")
    breakdown = MagicMock()
    breakdown.final_cents = 5500
    breakdown.subtotal_cents = 5500
    breakdown.tax_cents = 0
    breakdown.items = []
    mock_pricing.return_value.calculate_merchant.return_value = breakdown
    mock_pricing.return_value.to_api_breakdown.return_value = {
        "final_cents": 5500,
        "subtotal_cents": 5500,
        "tax_cents": 0,
        "currency": "cad",
        "items": [],
    }

    order = _order(db, merchant_ctx.merchant.id, state=OrderState.DISPATCH_READY.value)
    result = ParcelAmendService().apply(
        db,
        order,
        [
            _stop(1, "pickup", "100 King St W, Toronto, ON M5X 1A9", 43.6488, -79.3817, weight=4),
            _stop(2, "drop", "1 Dundas St E, Toronto, ON M5B 2R8", 43.6561, -79.3802, weight=12),
        ],
        merchant_ctx.merchant,
        actor_type="merchant",
        actor_id=merchant_ctx.user.id,
    )
    db.refresh(order)
    assert result["amount_cents"] == 5500
    assert order.amount_cents == 5500
    assert order.compliance_metadata["quote"]["amount_cents"] == 5500
    pkgs = [p for s in result["stops"] for p in s["packages"]]
    assert any(p.get("weight_kg") == 12 for p in pkgs)


def test_preview_stop_patch_refused_after_confirm(merchant_ctx) -> None:
    svc = MerchantRouteImportService()
    job = MagicMock()
    job.status = BulkImportStatus.CONFIRMED.value
    with patch.object(svc, "get_job", return_value=job):
        with pytest.raises(ValueError, match="route_import_already_confirmed"):
            svc.patch_stop(MagicMock(), merchant_ctx, "job1", 0, {"notes": "gate code"})
