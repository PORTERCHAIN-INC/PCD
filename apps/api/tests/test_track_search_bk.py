"""BK — Track search takes a tracking number, an order number, or a PO."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from porterchain_api.auth.merchant import get_merchant_context
from porterchain_api.booking_engine.numbers import generate_order_number, generate_tracking_number
from porterchain_api.booking_engine.repositories.order_repository import OrderRepository
from porterchain_api.config import get_settings
from porterchain_api.db import get_db
from porterchain_api.domain.merchant_states import MerchantRole, MerchantStatus
from porterchain_api.domain.states import OrderState
from porterchain_api.main import app
from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_api.merchant_engine.tracking_service import (
    AmbiguousTrackingQuery,
    MerchantTrackingService,
    tracking_error_message,
)
from porterchain_api.merchant_models import Merchant, MerchantUser
from porterchain_api.booking_models import Order


def _addr(street: str = "1 King St W, Toronto") -> dict:
    return {"formatted": street, "lat": 43.6488, "lng": -79.3817}


def _merchant_ctx(db) -> MerchantContext:
    suffix = uuid4().hex[:8]
    merchant = Merchant(
        company_name=f"PO Search Co {suffix}",
        email=f"po-{suffix}@test.local",
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


def _order(db, merchant_id: str, *, po: str | None = None, street: str | None = None) -> Order:
    order = Order(
        order_number=generate_order_number(),
        tracking_number=generate_tracking_number(),
        state=OrderState.IN_TRANSIT.value,
        merchant_id=merchant_id,
        amount_cents=2500,
        currency="cad",
        pickup=_addr(),
        dropoff=_addr(street) if street else _addr(),
        purchase_order_number=po,
        scheduled_at=datetime.now(UTC),
    )
    db.add(order)
    db.flush()
    return order


# --- Repository: what the three references resolve to ---


def test_po_finds_the_shipment(db) -> None:
    """The number a merchant's own customer quotes on the phone is the PO."""
    ctx = _merchant_ctx(db)
    order = _order(db, ctx.merchant.id, po="PO-99812")

    repo = OrderRepository()
    assert [o.id for o in repo.find_for_merchant_lookup(db, ctx.merchant.id, "PO-99812")] == [
        order.id
    ]


def test_every_reference_is_case_insensitive(db) -> None:
    """Numbers are stored uppercase but get typed and pasted in any case."""
    ctx = _merchant_ctx(db)
    order = _order(db, ctx.merchant.id, po="Po-Mixed-42")
    repo = OrderRepository()

    for typed in (
        order.tracking_number.lower(),
        order.order_number.lower(),
        "po-mixed-42",
        "PO-MIXED-42",
    ):
        found = repo.find_for_merchant_lookup(db, ctx.merchant.id, typed)
        assert [o.id for o in found] == [order.id], typed


def test_one_po_across_several_drops_returns_them_all(db) -> None:
    """A PO is the customer's reference, not ours — it can cover several drops."""
    ctx = _merchant_ctx(db)
    first = _order(db, ctx.merchant.id, po="PO-MULTI", street="10 Bay St, Toronto")
    second = _order(db, ctx.merchant.id, po="PO-MULTI", street="20 Bay St, Toronto")

    found = OrderRepository().find_for_merchant_lookup(db, ctx.merchant.id, "PO-MULTI")
    assert {o.id for o in found} == {first.id, second.id}


def test_a_tracking_number_wins_over_a_po(db) -> None:
    """Unique references short-circuit; a PO never widens an exact hit."""
    ctx = _merchant_ctx(db)
    target = _order(db, ctx.merchant.id, po="PO-SHARED")
    _order(db, ctx.merchant.id, po=target.tracking_number)

    found = OrderRepository().find_for_merchant_lookup(db, ctx.merchant.id, target.tracking_number)
    assert [o.id for o in found] == [target.id]


def test_another_companys_po_is_invisible(db) -> None:
    ctx = _merchant_ctx(db)
    other = _merchant_ctx(db)
    _order(db, other.merchant.id, po="PO-THEIRS")

    assert OrderRepository().find_for_merchant_lookup(db, ctx.merchant.id, "PO-THEIRS") == []


def test_wildcards_are_characters_not_patterns(db) -> None:
    """A pasted reference containing % must not match every order."""
    ctx = _merchant_ctx(db)
    real = _order(db, ctx.merchant.id, po="PO-100%")
    _order(db, ctx.merchant.id, po="PO-ANYTHING")
    repo = OrderRepository()

    assert repo.find_for_merchant_lookup(db, ctx.merchant.id, "%") == []
    assert repo.find_for_merchant_lookup(db, ctx.merchant.id, "PO-1_0%") == []
    assert [o.id for o in repo.find_for_merchant_lookup(db, ctx.merchant.id, "PO-100%")] == [
        real.id
    ]


def test_blank_search_finds_nothing(db) -> None:
    ctx = _merchant_ctx(db)
    _order(db, ctx.merchant.id, po="PO-1")

    repo = OrderRepository()
    for blank in ("", "   ", None):
        assert repo.find_for_merchant_lookup(db, ctx.merchant.id, blank) == []  # type: ignore[arg-type]


# --- Service: ambiguity is a question, not a guess ---


def test_tracking_a_unique_po_works(db, settings) -> None:
    ctx = _merchant_ctx(db)
    order = _order(db, ctx.merchant.id, po="PO-ONLY-ONE")

    snapshot = MerchantTrackingService().track_by_number(db, settings, ctx, "po-only-one")
    assert snapshot["order_id"] == order.id


def test_an_ambiguous_po_asks_instead_of_guessing(db, settings) -> None:
    """Showing one of three vans at random is worse than asking."""
    ctx = _merchant_ctx(db)
    _order(db, ctx.merchant.id, po="PO-DUP", street="10 Bay St, Toronto")
    _order(db, ctx.merchant.id, po="PO-DUP", street="20 Bay St, Toronto")

    with pytest.raises(AmbiguousTrackingQuery) as exc:
        MerchantTrackingService().track_by_number(db, settings, ctx, "PO-DUP")

    assert "2 shipments share PO PO-DUP" in exc.value.message
    choices = exc.value.choices()
    assert len(choices) == 2
    assert {c["dropoff"] for c in choices} == {"10 Bay St, Toronto", "20 Bay St, Toronto"}
    assert all(c["tracking_number"] and c["order_id"] for c in choices)


def test_the_miss_message_names_all_three_references() -> None:
    message = tracking_error_message("tracking_not_found")
    assert "tracking number" in message.lower()
    assert "order number" in message.lower()
    assert "po" in message.lower()


# --- HTTP ---


@pytest.fixture
def merchant_client(db, settings, monkeypatch):
    holder: dict = {}
    monkeypatch.setattr(
        "porterchain_api.routers.merchant.orders_tracking.require_module",
        lambda ctx, module: None,
    )
    app.dependency_overrides[get_merchant_context] = lambda: holder["ctx"]
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_settings] = lambda: settings
    yield TestClient(app), holder
    app.dependency_overrides.clear()


def test_track_endpoint_accepts_a_po(merchant_client, db) -> None:
    client, holder = merchant_client
    ctx = _merchant_ctx(db)
    order = _order(db, ctx.merchant.id, po="PO-HTTP-1")
    holder["ctx"] = ctx

    res = client.get("/v1/merchant/track/PO-HTTP-1")
    assert res.status_code == 200
    assert res.json()["live_tracking"]["order_id"] == order.id


def test_track_endpoint_offers_a_choice_for_a_shared_po(merchant_client, db) -> None:
    client, holder = merchant_client
    ctx = _merchant_ctx(db)
    _order(db, ctx.merchant.id, po="PO-HTTP-2", street="10 Bay St, Toronto")
    _order(db, ctx.merchant.id, po="PO-HTTP-2", street="20 Bay St, Toronto")
    holder["ctx"] = ctx

    res = client.get("/v1/merchant/track/PO-HTTP-2")
    assert res.status_code == 409
    detail = res.json()["detail"]
    assert "Pick the one you want to track" in detail["message"]
    assert len(detail["choices"]) == 2


def test_track_endpoint_still_404s_on_a_real_miss(merchant_client, db) -> None:
    """The ambiguous case must not swallow a genuine miss into a 500."""
    client, holder = merchant_client
    holder["ctx"] = _merchant_ctx(db)

    res = client.get("/v1/merchant/track/PO-NOT-A-THING")
    assert res.status_code == 404
    assert "No shipment matches" in res.json()["detail"]
