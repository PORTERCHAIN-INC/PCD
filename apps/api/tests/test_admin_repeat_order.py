"""Admin Repeat order: same locked price, dates shifted to America/Toronto today."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest

from porterchain_api.admin_engine.repeat_order_service import (
    _schedule_for_today,
    repeat_summary,
)
from porterchain_api.domain.merchant_states import MerchantRole, MerchantStatus
from porterchain_api.domain.states import OrderSource, OrderState
from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_api.merchant_models import Merchant, MerchantUser

TORONTO = ZoneInfo("America/Toronto")

def _pg_reachable() -> bool:
    import socket
    try:
        with socket.create_connection(("127.0.0.1", 55432), timeout=0.3):
            return True
    except OSError:
        return False




def test_schedule_for_today_shifts_windows_and_keeps_clock_time() -> None:
    original = SimpleNamespace(
        scheduled_at=datetime(2026, 9, 12, 18, 0, tzinfo=UTC),  # 14:00 Toronto (EDT)
        compliance_metadata={
            "schedule_mode": "later",
            "stops": [
                {
                    "type": "pickup",
                    "time_window_start": "2026-09-12T18:00:00+00:00",
                    "time_window_end": "2026-09-12T21:00:00+00:00",
                }
            ],
        },
    )
    # Fixed "now": 2026-11-05 10:00 America/Toronto
    now = datetime(2026, 11, 5, 15, 0, tzinfo=UTC)
    scheduled_at, mode, meta = _schedule_for_today(original, now=now)
    local = scheduled_at.astimezone(TORONTO)
    assert local.date().isoformat() == "2026-11-05"
    assert local.hour == 14
    assert mode == "later"
    stop = meta["stops"][0]
    start = datetime.fromisoformat(stop["time_window_start"]).astimezone(TORONTO)
    end = datetime.fromisoformat(stop["time_window_end"]).astimezone(TORONTO)
    assert start.date().isoformat() == "2026-11-05"
    assert end.hour == 17  # 21:00 UTC was 17:00 Toronto EDT; wall clock preserved


def test_schedule_for_today_falls_back_to_now_when_window_passed() -> None:
    original = SimpleNamespace(
        scheduled_at=datetime(2026, 9, 12, 12, 0, tzinfo=UTC),  # 08:00 Toronto
        compliance_metadata={
            "schedule_mode": "later",
            "stops": [
                {
                    "type": "pickup",
                    "time_window_start": "2026-09-12T12:00:00+00:00",
                    "time_window_end": "2026-09-12T13:00:00+00:00",
                }
            ],
        },
    )
    now = datetime(2026, 11, 5, 20, 0, tzinfo=UTC)  # 15:00 Toronto — past 08–09
    scheduled_at, mode, meta = _schedule_for_today(original, now=now)
    assert mode == "now"
    assert scheduled_at == now
    stop = meta["stops"][0]
    end = datetime.fromisoformat(stop["time_window_end"])
    assert end > now


def test_create_repeat_committed_rejects_missing_order() -> None:
    from porterchain_api.admin_engine.orders_service import AdminOrdersService

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    with pytest.raises(LookupError, match="order_not_found"):
        AdminOrdersService().create_repeat_committed(db, MagicMock(), "missing")


def _ctx(db) -> MerchantContext:
    suffix = uuid4().hex[:8]
    merchant = Merchant(
        company_name=f"Repeat Co {suffix}",
        email=f"repeat-{suffix}@test.local",
        status=MerchantStatus.ACTIVE.value,
        profile={},
    )
    db.add(merchant)
    db.flush()
    user = MerchantUser(
        merchant_id=merchant.id,
        auth_subject=f"idp_{suffix}",
        email=f"owner-{suffix}@test.local",
        role=MerchantRole.OWNER.value,
    )
    db.add(user)
    db.flush()
    return MerchantContext(merchant=merchant, user=user, role=MerchantRole.OWNER)


@pytest.mark.skipif(not _pg_reachable(), reason="test postgres :55432 not up (scripts/test-infra.sh)")
def test_repeat_keeps_price_and_updates_dates(db, settings) -> None:
    from porterchain_api.merchant_engine.booking_service import MerchantBookingService
    from porterchain_api.schemas_merchant import AddressInput, MerchantBookDeliveryRequest

    ctx = _ctx(db)
    body = MerchantBookDeliveryRequest(
        pickup=AddressInput(formatted="100 King St W, Toronto", postal="M5X 1A1", lat=43.65, lng=-79.38),
        dropoff=AddressInput(formatted="200 Bay St, Toronto", postal="M5J 2J2", lat=43.65, lng=-79.38),
        scheduled_at=datetime(2026, 9, 10, 18, 0, tzinfo=UTC),
        schedule_mode="later",
        vehicle_class="cargo_van",
        package_type="looseParcel",
        pickup_window_start=datetime(2026, 9, 10, 18, 0, tzinfo=UTC),
        pickup_window_end=datetime(2026, 9, 10, 21, 0, tzinfo=UTC),
    )
    with patch(
        "porterchain_api.merchant_engine.booking_service.transition_to_dispatch_ready",
        side_effect=lambda db, order, **_k: order,
    ):
        original = MerchantBookingService().create_shipment(db, settings, ctx, body)
    original_price = int(original.amount_cents)
    assert original_price > 0

    fixed_now = datetime(2026, 11, 5, 15, 0, tzinfo=UTC)  # 10:00 Toronto
    from porterchain_api.admin_engine import repeat_order_service as ros

    real = ros.create_repeat_order

    def _wrapped(db, settings, original, *, actor_id=None, now=None):
        return real(db, settings, original, actor_id=actor_id, now=fixed_now)

    with (
        patch.object(ros, "create_repeat_order", side_effect=_wrapped),
        patch(
            "porterchain_api.booking_engine.order_transitions.transition_to_dispatch_ready",
            side_effect=lambda db, order, **_k: order,
        ),
    ):
        from porterchain_api.admin_engine.orders_service import AdminOrdersService

        summary = AdminOrdersService().create_repeat_committed(
            db, settings, original.id, actor_id="admin-1"
        )

    assert summary["amount_cents"] == original_price
    assert summary["price_locked"] is True
    assert summary["order_id"] != original.id
    assert summary["tracking_number"] != original.tracking_number
    assert summary["source_order_id"] == original.id

    from porterchain_api.booking_models import Order

    copy = db.query(Order).filter(Order.id == summary["order_id"]).one()
    assert copy.amount_cents == original_price
    assert copy.assigned_driver_id is None
    assert copy.order_source == OrderSource.ADMIN.value
    assert copy.merchant_id == original.merchant_id
    assert copy.pickup["formatted"] == original.pickup["formatted"]
    assert copy.dropoff["formatted"] == original.dropoff["formatted"]
    local = copy.scheduled_at.astimezone(TORONTO)
    assert local.date().isoformat() == "2026-11-05"
    meta = copy.compliance_metadata or {}
    assert meta["repeat"]["locked_price_cents"] == original_price
    assert meta["repeat"]["of"] == original.id


def test_repeat_summary_shape() -> None:
    order = SimpleNamespace(
        id="o2",
        order_number="PC-1",
        tracking_number="TRK-1",
        state=OrderState.BOOKED.value,
        amount_cents=4599,
        currency="cad",
        scheduled_at=datetime(2026, 11, 5, 15, 0, tzinfo=UTC),
        compliance_metadata={"repeat": {"of": "o1", "of_tracking": "TRK-0"}},
    )
    out = repeat_summary(order)
    assert out["amount_cents"] == 4599
    assert out["source_order_id"] == "o1"
    assert out["price_locked"] is True


def test_create_repeat_order_locks_source_amount() -> None:
    """Price is copied from the source — pricing engine is never consulted."""
    from porterchain_api.admin_engine.repeat_order_service import create_repeat_order
    from porterchain_api.booking_models import Order

    original = SimpleNamespace(
        id="src-1",
        order_number="PC-OLD",
        tracking_number="TRK-OLD",
        amount_cents=7777,
        currency="cad",
        merchant_id="m1",
        customer_id=None,
        payment_terms="NET30",
        pickup={"formatted": "A", "postal": "M5X 1A1"},
        dropoff={"formatted": "B", "postal": "M5J 2J2"},
        scheduled_at=datetime(2026, 9, 10, 18, 0, tzinfo=UTC),
        internal_reference="ref",
        purchase_order_number="PO-1",
        cost_centre="CC",
        special_instructions="fragile",
        compliance_metadata={"schedule_mode": "later", "stops": [], "vehicle_class": "cargo_van"},
        is_sandbox=True,
    )
    db = MagicMock()
    captured: dict = {}

    def _add(obj):
        if isinstance(obj, Order):
            captured["order"] = obj

    db.add.side_effect = _add
    merchant = SimpleNamespace(id="m1", payment_terms="NET30")
    validated = SimpleNamespace(warnings=[], contract_id=None)
    with (
        patch("porterchain_api.merchant_engine.lookups.get_merchant", return_value=merchant),
        patch(
            "porterchain_api.merchant_engine.booking_validation.MerchantSyncService.validate_booking",
            return_value=validated,
        ),
        patch("porterchain_api.admin_engine.repeat_order_service.generate_order_number", return_value="PC-NEW"),
        patch("porterchain_api.admin_engine.repeat_order_service.generate_tracking_number", return_value="TRK-NEW"),
        patch("porterchain_api.admin_engine.repeat_order_service.emit_event"),
        patch("porterchain_api.services.collect_only.attach_legs"),
        patch("porterchain_api.services.collect_only.is_collect_only", return_value=False),
        patch("porterchain_api.pricing_engine.get_pricing_service") as pricing,
    ):
        out = create_repeat_order(
            db,
            MagicMock(),
            original,  # type: ignore[arg-type]
            actor_id="admin-9",
            now=datetime(2026, 11, 5, 15, 0, tzinfo=UTC),
        )
    pricing.assert_not_called()
    assert out is captured["order"]
    assert out.amount_cents == 7777
    assert out.tracking_number == "TRK-NEW"
    assert out.order_number == "PC-NEW"
    assert out.assigned_driver_id is None
    assert out.compliance_metadata["repeat"]["locked_price_cents"] == 7777
    assert out.scheduled_at.astimezone(TORONTO).date().isoformat() == "2026-11-05"
