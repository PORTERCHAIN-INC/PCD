"""AS — one quote picture on book, route, Order 360, and admin order."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from porterchain_api.domain.catalog_labels import quote_line_label
from porterchain_api.merchant_engine.booking_flow_service import MerchantBookingFlowService
from porterchain_api.merchant_engine.booking_service import MerchantBookingService
from porterchain_api.merchant_engine.orders_service import MerchantOrdersService
from porterchain_api.merchant_engine.quote_snapshot import (
    QUOTE_PICTURE_KEYS,
    merchant_facing_quote,
    merchant_quote_picture,
    sanitize_pricing_breakdown,
)
from porterchain_api.order_engine.platform_service import OrderPlatformService
from porterchain_api.schemas_merchant import AddressInput, MerchantBookDeliveryRequest


def _book_body() -> MerchantBookDeliveryRequest:
    return MerchantBookDeliveryRequest(
        pickup=AddressInput(
            formatted="100 King St W, Toronto", postal="M5X 1A1", lat=43.65, lng=-79.38
        ),
        dropoff=AddressInput(
            formatted="200 Bay St, Toronto", postal="M5J 2J2", lat=43.64, lng=-79.37
        ),
        vehicle_class="cargoVan",
        package_type="looseParcel",
        weight_kg=10.0,
        scheduled_at=datetime.now(UTC) + timedelta(hours=4),
        schedule_mode="scheduled",
        requires_liftgate=True,
    )


def _assert_picture(blob: dict) -> None:
    assert QUOTE_PICTURE_KEYS <= set(blob)
    text = str(blob).lower()
    assert "valhalla" not in text
    assert "osrm" not in text
    assert "routing_source" not in text
    assert "driver_payout" not in text
    for line in blob.get("items") or blob.get("line_items") or []:
        label = str(line.get("label") or "")
        assert label
        assert " " in label or label[0].isupper()
        assert "_" not in label or " " in label


def test_quote_line_glossary() -> None:
    assert quote_line_label("liftgate", "liftgate") == "Liftgate"
    assert quote_line_label("base", "Cargo van · up to 10 km base") == "Cargo van · up to 10 km base"
    assert quote_line_label("downtown", None) == "Downtown surcharge"


def test_nested_quote_row_drops_vendor_keys() -> None:
    nested = {
        "items": [{"code": "liftgate", "label": "liftgate", "amount_cents": 2200}],
        "summary": {
            "final_cents": 2486,
            "subtotal_cents": 2200,
            "tax_cents": 286,
            "currency": "cad",
            "metadata": {"routing_source": "valhalla", "driver_payout_cents_preview": 9},
        },
    }
    clean = sanitize_pricing_breakdown(nested)
    assert clean is not None
    _assert_picture(clean)
    assert clean["final_cents"] == 2486
    assert clean["tax_cents"] == 286
    assert clean["items"][0]["label"] == "Liftgate"
    assert clean["items"] == clean["line_items"]
    picture = merchant_quote_picture(nested)
    assert picture["amount_cents"] == 2486
    assert "valhalla" not in str(picture).lower()


def test_preview_route_and_360_share_picture(db, settings, merchant_ctx) -> None:
    merchant_ctx.merchant.payment_terms = "NET_30"
    db.commit()
    flow = MerchantBookingFlowService()
    preview = flow.preview(db, settings, merchant_ctx, _book_body())
    assert preview.get("valid") is True
    book = preview["pricing_breakdown"]
    _assert_picture(book)
    assert book["tax_cents"] is not None
    assert book["final_cents"] == preview["amount_cents"]

    raw_engine = {
        **book,
        "metadata": {"routing_source": "osrm"},
        "duration_seconds": 600,
        "total_drops": 2,
        "total_pickups": 1,
    }
    route = merchant_facing_quote(raw_engine)
    assert route is not None
    _assert_picture(route)
    assert route["items"] == book["items"]
    assert route["final_cents"] == book["final_cents"]
    assert route["total_drops"] == 2

    with patch(
        "porterchain_api.merchant_engine.booking_service.transition_to_dispatch_ready",
        side_effect=lambda db, order, **_k: order,
    ):
        order = MerchantBookingService().create_shipment(db, settings, merchant_ctx, _book_body())
    merchant_360 = MerchantOrdersService().get_detail_360(db, settings, merchant_ctx, order.id)
    _assert_picture(merchant_360["pricing_breakdown"])
    assert merchant_360["pricing_breakdown"]["final_cents"] == order.amount_cents

    admin_360 = OrderPlatformService().get_detail_360(db, settings, order.id)
    assert admin_360 is not None
    _assert_picture(admin_360["pricing_breakdown"])
    assert admin_360["pricing_breakdown"]["items"] == merchant_360["pricing_breakdown"]["items"]
    assert admin_360["pricing_breakdown"]["final_cents"] == merchant_360["pricing_breakdown"]["final_cents"]
