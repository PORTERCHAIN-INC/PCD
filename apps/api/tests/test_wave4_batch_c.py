"""Wave 4 Batch C: visitor merge FK + suspend Fleetbase warning."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from porterchain_api.booking_engine.visitor_tracking_service import VisitorTrackingService


def test_merge_to_customer_persists_fk() -> None:
    db = MagicMock()
    visitor = SimpleNamespace(id="sess-1", customer_id=None)
    db.query.return_value.filter.return_value.first.return_value = visitor

    with patch("porterchain_api.booking_engine.visitor_tracking_service.emit_event") as emit:
        VisitorTrackingService().merge_to_customer(db, "sess-1", "cust-9")

    assert visitor.customer_id == "cust-9"
    db.commit.assert_called()
    emit.assert_called_once()
    assert emit.call_args.kwargs["payload"]["customer_id"] == "cust-9"


def test_merge_to_customer_missing_session_still_emits() -> None:
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    with patch("porterchain_api.booking_engine.visitor_tracking_service.emit_event") as emit:
        VisitorTrackingService().merge_to_customer(db, "missing", "cust-1")
    emit.assert_called_once()
    db.commit.assert_called()


def test_suspend_driver_stays_on_porterchain() -> None:
    from porterchain_api.admin_engine.driver_service import AdminDriverService
    from porterchain_api.domain.admin_states import DriverStatus

    svc = AdminDriverService()
    driver = SimpleNamespace(
        id="d1",
        status="APPROVED",
        is_online=True,
        availability="idle",
        clerk_user_id="user_x",
    )
    db = MagicMock()
    ctx = SimpleNamespace(user=SimpleNamespace(id="admin-1"))
    settings = SimpleNamespace()

    svc._get_or_raise = MagicMock(return_value=driver)  # type: ignore[method-assign]
    svc._audit = MagicMock()  # type: ignore[method-assign]

    with (
        patch("porterchain_api.admin_engine.driver_service.emit_event"),
        patch("porterchain_api.auth.authz_sync.sync_authz_after_persona_mutation"),
    ):
        out, warning = svc.suspend_driver(db, ctx, "d1", settings)

    assert out.status == DriverStatus.SUSPENDED.value
    assert warning is None
