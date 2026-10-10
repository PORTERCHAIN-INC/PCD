"""Wave 4 Batch H: presence mirror, reject/rehire, lifecycle classify."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from porterchain_api.domain.admin_states import DriverStatus


def test_rehire_rejects_approved() -> None:
    from porterchain_api.admin_engine.driver_service import AdminDriverService

    svc = AdminDriverService()
    driver = SimpleNamespace(
        id="d1",
        status=DriverStatus.APPROVED.value,
        is_online=False,
        clerk_user_id="user_x",
    )
    db = MagicMock()
    ctx = SimpleNamespace(user=SimpleNamespace(id="admin-1"))
    svc._get_or_raise = MagicMock(return_value=driver)  # type: ignore[method-assign]

    try:
        svc.rehire_driver(db, ctx, "d1")
        raise AssertionError("expected ValueError")
    except ValueError as exc:
        assert str(exc) == "driver_not_rehirable"


def test_customer_dashboard_schema_has_bookings_and_stats() -> None:
    from porterchain_api.schemas_booking import CustomerDashboardResponse, CustomerRebookResponse

    dash = CustomerDashboardResponse.model_validate(
        {
            "active_order": None,
            "orders": [],
            "bookings": [{"booking_id": "b1", "state": "confirmed"}],
            "invoices": [],
            "payments": [],
            "stats": {"total_orders": 0, "total_bookings": 1},
        }
    )
    assert dash.stats["total_bookings"] == 1
    rebook = CustomerRebookResponse.model_validate(
        {
            "pickup": {"formatted": "A"},
            "dropoff": {"formatted": "B"},
            "vehicle_class": "cargo_van",
            "source_order_id": "o1",
            "tracking_number": "TRK",
        }
    )
    assert rebook.source_order_id == "o1"


def test_reject_and_rehire_lifecycle() -> None:
    from porterchain_api.admin_engine.driver_service import AdminDriverService

    svc = AdminDriverService()
    driver = SimpleNamespace(
        id="d1",
        status=DriverStatus.PENDING.value,
        is_online=True,
        availability="online",
        clerk_user_id="user_x",
    )
    db = MagicMock()
    ctx = SimpleNamespace(user=SimpleNamespace(id="admin-1"))

    svc._get_or_raise = MagicMock(return_value=driver)  # type: ignore[method-assign]
    svc._audit = MagicMock()  # type: ignore[method-assign]

    with (
        patch("porterchain_api.admin_engine.driver_service.emit_event"),
        patch("porterchain_api.auth.authz_sync.sync_authz_after_persona_mutation"),
    ):
        out, warning = svc.reject_driver(db, ctx, "d1", settings=None)
        assert out.status == DriverStatus.REJECTED.value
        assert warning is None

        rehined = svc.rehire_driver(db, ctx, "d1")
        assert rehined.status == DriverStatus.PENDING.value
