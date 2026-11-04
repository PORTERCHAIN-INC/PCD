"""Raw material run: pick up at a supplier, deliver to the merchant's own address,
billed to the merchant, no warehouse holding (Phase 0)."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import patch

from porterchain_api.merchant_engine.booking_service import MerchantBookingService
from porterchain_api.services import collect_only as co
from tests.test_merchant_book_al import _body, _ctx
from porterchain_api.schemas_merchant import AddressInput

SUPPLIER = AddressInput(formatted="55 Supplier Rd, Mississauga", postal="L5T 1A1", lat=43.65, lng=-79.66)
OWN = AddressInput(formatted="200 Bay St, Toronto", postal="M5J 2J2", lat=43.65, lng=-79.38)


def _book(db, settings, ctx, **extra):
    with patch(
        "porterchain_api.merchant_engine.booking_service.transition_to_dispatch_ready",
        side_effect=lambda db, order, **_k: order,
    ):
        return MerchantBookingService().create_shipment(
            db, settings, ctx, _body(pickup=SUPPLIER, dropoff=OWN, **extra)
        )


def test_supplier_pickup_delivers_to_own_address_billed_to_merchant(db, settings) -> None:
    ctx = _ctx(db)
    order = _book(db, settings, ctx, purchase_order_number="PO-RAW-1",
                  internal_reference="raw steel coil")
    assert order.merchant_id == ctx.merchant.id
    assert not co.is_collect_only(order)
    stops = (order.compliance_metadata or {}).get("stops") or []
    assert stops[0]["type"] == "pickup" and "Supplier" in str(stops[0])
    assert stops[-1]["type"] != "pickup" and "200 Bay" in str(stops[-1])
    assert "warehouse" not in str(stops).lower()


def test_supplier_pickup_with_window_is_same_day_not_held(db, settings) -> None:
    ctx = _ctx(db)
    order = _book(
        db, settings, ctx,
        pickup_window_start=datetime(2026, 9, 11, 13, 0, tzinfo=UTC),
        pickup_window_end=datetime(2026, 9, 11, 16, 0, tzinfo=UTC),
    )
    assert not co.is_collect_only(order)
    assert len((order.compliance_metadata or {}).get("stops") or []) == 2
