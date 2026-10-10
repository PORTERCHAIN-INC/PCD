"""BH — portal book is idempotent like the partner API: a retry must not double-book."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from porterchain_api.booking_engine.numbers import (
    generate_order_number,
    generate_tracking_number,
)
from porterchain_api.booking_models import Order
from porterchain_api.merchant_engine.booking_flow_service import (
    MerchantBookingFlowService,
)
from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_api.routers.merchant.dashboard_booking import booking_multi
from porterchain_api.schemas_merchant import (
    AddressInput,
    MerchantBookDeliveryRequest,
    MerchantMultiParcelRequest,
)

PICKUP = {"formatted": "100 King St W, Toronto", "lat": 43.6488, "lng": -79.3817}
DROPS = (
    {"formatted": "200 Bay St, Toronto", "lat": 43.6470, "lng": -79.3800},
    {"formatted": "1 Dundas St E, Toronto", "lat": 43.6561, "lng": -79.3802},
)


def _parcel(dropoff: dict) -> MerchantBookDeliveryRequest:
    return MerchantBookDeliveryRequest(
        pickup=AddressInput(**PICKUP),
        dropoff=AddressInput(**dropoff),
        vehicle_class="cargo_van",
        package_type="looseParcel",
        weight_kg=5.0,
        scheduled_at=datetime.now(UTC),
    )


def _order(db: Session, ctx: MerchantContext, key: str | None, *, cents: int = 4200) -> Order:
    order = Order(
        order_number=generate_order_number(),
        tracking_number=generate_tracking_number(),
        merchant_id=ctx.merchant.id,
        idempotency_key=key,
        amount_cents=cents,
        currency="cad",
        pickup=PICKUP,
        dropoff=dict(DROPS[0]),
        scheduled_at=datetime.now(UTC),
    )
    db.add(order)
    db.flush()
    return order


def test_batch_key_becomes_one_key_per_parcel() -> None:
    """Parcels must not share a key, or the unique index books only the first."""
    key = MerchantBookingFlowService.parcel_idempotency_key
    assert key("batch-1", 1) == "batch-1:1"
    assert key("batch-1", 2) == "batch-1:2"
    assert key(None, 1) is None
    assert key("  ", 1) is None


def test_multi_parcel_retry_replays_instead_of_rebooking(
    db: Session, settings, merchant_ctx: MerchantContext
) -> None:
    batch = f"batch-{uuid4().hex[:8]}"
    booked = _order(db, merchant_ctx, f"{batch}:1")

    service = MerchantBookingFlowService()
    with patch.object(service._booking, "create_shipment") as create:
        create.side_effect = AssertionError("a replayed parcel must not book again")
        result = service.confirm_multi(
            db,
            settings,
            merchant_ctx,
            AddressInput(**PICKUP),
            [_parcel(DROPS[0])],
            idempotency_key=batch,
        )

    assert result["errors"] == []
    assert [row["order_id"] for row in result["orders"]] == [booked.id]
    assert result["orders"][0]["already_booked"] is True
    assert result["orders"][0]["tracking_number"] == booked.tracking_number
    assert result["total_amount_cents"] == booked.amount_cents


def test_multi_parcel_books_the_parcels_it_has_not_seen(
    db: Session, settings, merchant_ctx: MerchantContext
) -> None:
    """A retry after a partial failure finishes the batch without duplicating."""
    batch = f"batch-{uuid4().hex[:8]}"
    first = _order(db, merchant_ctx, f"{batch}:1", cents=4200)

    service = MerchantBookingFlowService()
    second = _order(db, merchant_ctx, None, cents=3100)

    with (
        patch.object(service, "preview", return_value={"valid": True, "amount_cents": 3100}),
        patch.object(service._booking, "create_shipment", return_value=second) as create,
    ):
        result = service.confirm_multi(
            db,
            settings,
            merchant_ctx,
            AddressInput(**PICKUP),
            [_parcel(DROPS[0]), _parcel(DROPS[1])],
            idempotency_key=batch,
        )

    assert create.call_count == 1
    assert create.call_args.kwargs["idempotency_key"] == f"{batch}:2"
    assert [row["parcel"] for row in result["orders"]] == [1, 2]
    assert [row["already_booked"] for row in result["orders"]] == [True, False]
    assert result["orders"][0]["order_id"] == first.id
    assert result["total_amount_cents"] == 4200 + 3100


def test_multi_parcel_without_a_key_still_books(
    db: Session, settings, merchant_ctx: MerchantContext
) -> None:
    """No key is legal — older portal builds and website orders send none."""
    service = MerchantBookingFlowService()
    made = _order(db, merchant_ctx, None, cents=2500)

    with (
        patch.object(service, "preview", return_value={"valid": True, "amount_cents": 2500}),
        patch.object(service._booking, "create_shipment", return_value=made) as create,
    ):
        result = service.confirm_multi(
            db,
            settings,
            merchant_ctx,
            AddressInput(**PICKUP),
            [_parcel(DROPS[0])],
        )

    assert create.call_args.kwargs["idempotency_key"] is None
    assert result["orders"][0]["already_booked"] is False


def test_batch_key_must_leave_room_for_the_parcel_suffix(
    db: Session, settings, merchant_ctx: MerchantContext
) -> None:
    """orders.idempotency_key is String(128); the batch key plus ':{index}' must fit."""
    with (
        patch("porterchain_api.routers.merchant.dashboard_booking.require_module"),
        pytest.raises(HTTPException) as exc,
    ):
        booking_multi(
            body=MerchantMultiParcelRequest(pickup=AddressInput(**PICKUP), parcels=[]),
            ctx=merchant_ctx,
            db=db,
            settings=settings,
            idempotency_key="x" * 97,
        )
    assert exc.value.status_code == 400
    assert exc.value.detail == "idempotency_key_too_long"

    longest = MerchantBookingFlowService.parcel_idempotency_key("x" * 96, 9999)
    assert longest is not None and len(longest) <= 128


def test_single_confirm_replays_the_same_order(
    db: Session, settings, merchant_ctx: MerchantContext
) -> None:
    key = f"confirm-{uuid4().hex[:8]}"
    booked = _order(db, merchant_ctx, key)

    service = MerchantBookingFlowService()
    with (
        patch.object(service, "preview", return_value={"valid": True, "amount_cents": 4200}),
        patch.object(service._booking, "create_shipment") as create,
    ):
        create.side_effect = AssertionError("a replayed confirm must not book again")
        payload = service.confirm_booking(
            db,
            settings,
            merchant_ctx,
            _parcel(DROPS[0]),
            idempotency_key=key,
        )

    assert payload["order_id"] == booked.id
    assert payload["tracking_number"] == booked.tracking_number
