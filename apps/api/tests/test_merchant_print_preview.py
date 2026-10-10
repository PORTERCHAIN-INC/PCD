"""AF — merchant print preview and pickup list, not fake shipping labels."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from porterchain_api.auth.merchant import get_merchant_context
from porterchain_api.booking_engine.numbers import (
    generate_order_number,
    generate_tracking_number,
)
from porterchain_api.booking_models import Order
from porterchain_api.config import get_settings
from porterchain_api.db import get_db
from porterchain_api.domain.merchant_states import MerchantRole, MerchantStatus
from porterchain_api.domain.states import OrderState
from porterchain_api.main import app
from porterchain_api.merchant_engine.orders_service import (
    MerchantOrdersService,
    print_error_message,
)
from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_api.merchant_engine.toronto import format_datetime_toronto
from porterchain_api.merchant_models import Merchant, MerchantUser
from porterchain_api.reporting.order_documents import (
    build_pickup_list_pdf,
    build_print_preview_pdf,
)


def _addr() -> dict:
    return {"formatted": "1 King St W, Toronto", "city": "Toronto", "postal": "M5H 1A1"}


def _merchant_ctx(db) -> MerchantContext:
    suffix = uuid4().hex[:8]
    merchant = Merchant(
        company_name=f"Print Co {suffix}",
        email=f"print-{suffix}@test.local",
        status=MerchantStatus.ACTIVE.value,
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


def _order(db, merchant_id: str, *, po: str | None = "PO-99") -> Order:
    order = Order(
        order_number=generate_order_number(),
        tracking_number=generate_tracking_number(),
        state=OrderState.DISPATCH_READY.value,
        merchant_id=merchant_id,
        amount_cents=2500,
        currency="cad",
        pickup=_addr(),
        dropoff=_addr(),
        scheduled_at=datetime(2026, 9, 10, 18, 0, tzinfo=UTC),
        purchase_order_number=po,
    )
    db.add(order)
    db.flush()
    return order


def test_print_copy_is_english() -> None:
    assert print_error_message("orders_required") == "Select at least one order to print."
    assert "20" in print_error_message("too_many_orders")
    wall = format_datetime_toronto(datetime(2026, 9, 10, 18, 0, tzinfo=UTC))
    assert wall == "2026-09-10 14:00"


def test_print_preview_pdf_is_not_a_shipping_label(db) -> None:
    ctx = _merchant_ctx(db)
    order = _order(db, ctx.merchant.id)
    pdf = build_print_preview_pdf(order)
    assert pdf.startswith(b"%PDF")
    assert b"Print preview" in pdf
    assert b"Shipping Label" not in pdf
    assert b"Ready for pickup" in pdf
    assert b"PO-99" in pdf
    assert b"Fleetbase" not in pdf
    blob = pdf.lower()
    assert b"valhalla" not in blob
    assert b"osrm" not in blob


def test_pickup_list_includes_company(db) -> None:
    ctx = _merchant_ctx(db)
    first = _order(db, ctx.merchant.id, po="PO-1")
    second = _order(db, ctx.merchant.id, po="PO-2")
    pdf = build_pickup_list_pdf([first, second], merchant_name=ctx.merchant.company_name)
    assert b"Pickup list" in pdf
    assert ctx.merchant.company_name.encode("latin-1", errors="replace") in pdf
    assert first.tracking_number.encode() in pdf
    assert second.tracking_number.encode() in pdf
    assert b"Shipping Label" not in pdf


def test_merchant_service_scopes_print_to_owner(db) -> None:
    ctx = _merchant_ctx(db)
    other = _merchant_ctx(db)
    mine = _order(db, ctx.merchant.id)
    theirs = _order(db, other.merchant.id)
    db.commit()
    svc = MerchantOrdersService()
    pdf, name = svc.print_preview_pdf(db, ctx, mine.id)
    assert pdf.startswith(b"%PDF")
    assert name.startswith("print-preview-")
    try:
        svc.print_preview_pdf(db, ctx, theirs.id)
        raise AssertionError("foreign print preview should fail")
    except LookupError as exc:
        assert str(exc) == "order_not_found"
    try:
        svc.pickup_list_pdf(db, ctx, [theirs.id])
        raise AssertionError("foreign pickup list should fail")
    except LookupError:
        pass


def test_print_http_english_and_ownership(db, settings, monkeypatch) -> None:
    holder: dict = {}
    monkeypatch.setattr(
        "porterchain_api.routers.merchant.orders_tracking.require_module",
        lambda ctx, module: None,
    )
    app.dependency_overrides[get_merchant_context] = lambda: holder["ctx"]
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_settings] = lambda: settings
    client = TestClient(app)
    try:
        ctx = _merchant_ctx(db)
        other = _merchant_ctx(db)
        order = _order(db, ctx.merchant.id)
        foreign = _order(db, other.merchant.id)
        db.commit()
        holder["ctx"] = ctx

        empty = client.get("/v1/merchant/orders/pickup-list.pdf")
        assert empty.status_code == 400
        assert "Select at least one order" in empty.json()["detail"]

        stolen = client.get(f"/v1/merchant/orders/{foreign.id}/print-preview.pdf")
        assert stolen.status_code == 404
        assert "not found" in stolen.json()["detail"].lower()

        preview = client.get(f"/v1/merchant/orders/{order.id}/print-preview.pdf")
        assert preview.status_code == 200
        assert preview.headers["content-type"].startswith("application/pdf")
        assert preview.content.startswith(b"%PDF")
        assert b"Print preview" in preview.content
        assert b"Shipping Label" not in preview.content

        listing = client.get("/v1/merchant/orders/pickup-list.pdf", params={"ids": [order.id]})
        assert listing.status_code == 200
        assert listing.content.startswith(b"%PDF")
        assert b"Pickup list" in listing.content
    finally:
        app.dependency_overrides.clear()
