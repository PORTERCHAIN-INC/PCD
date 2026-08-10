"""Wave 1 Partners P0 gates — privacy, tracking PII, docs sync, payouts, customer delete."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from porterchain_api.admin_engine.clerk_directory_service import ClerkDirectoryService
from porterchain_api.admin_engine.driver_service import AdminDriverService
from porterchain_api.billing_engine.driver_finance_service import DriverFinanceService
from porterchain_api.booking_engine.public_address import public_address_snapshot
from porterchain_api.booking_engine.public_tracking_snapshot import build_public_live_tracking
from porterchain_api.compliance_engine.privacy_service import PrivacyService


def test_public_address_strips_street_pii() -> None:
    snap = public_address_snapshot(
        {
            "formatted": "123 King St W, Toronto, ON",
            "street": "123 King St W",
            "city": "Toronto",
            "province": "ON",
            "postal_code": "M5H2N2",
            "lat": 43.65,
            "lng": -79.38,
            "place_id": "ChIJsecret",
            "contact_phone": "+14165550100",
        }
    )
    assert snap is not None
    assert snap["city"] == "Toronto"
    assert snap["province"] == "ON"
    assert snap["postal_code"] == "M5H"
    assert snap["lat"] == 43.65
    assert "formatted" not in snap
    assert "street" not in snap
    assert "place_id" not in snap
    assert "contact_phone" not in snap


def test_public_live_tracking_redacts_addresses(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "porterchain_api.booking_engine.public_tracking_snapshot._translate_live",
        lambda _raw: {"location": None, "last_updated": None},
    )
    order = SimpleNamespace(
        state="IN_TRANSIT",
        scheduled_at=None,
        pickup={
            "formatted": "1 Secret Lane",
            "city": "Mississauga",
            "province": "ON",
            "lat": 43.5,
            "lng": -79.6,
        },
        dropoff={
            "formatted": "9 Hidden Ave",
            "city": "Brampton",
            "province": "ON",
            "lat": 43.7,
            "lng": -79.7,
        },
    )
    live = build_public_live_tracking(order, None, maps=MagicMock())
    assert live["pickup"]["city"] == "Mississauga"
    assert "formatted" not in (live["pickup"] or {})
    assert live["dropoff"]["city"] == "Brampton"
    assert "formatted" not in (live["dropoff"] or {})


def test_customer_delete_forbidden() -> None:
    svc = ClerkDirectoryService()
    with pytest.raises(ValueError, match="customer_delete_forbidden"):
        svc.delete_clerk_user(
            MagicMock(),
            MagicMock(),
            MagicMock(),
            "customer",
            platform_user_id="cust-1",
        )


def test_customer_provision_branch_unreachable() -> None:
    svc = ClerkDirectoryService()
    with pytest.raises(ValueError, match="customer_self_signup_only"):
        svc._provision_from_clerk(
            MagicMock(),
            MagicMock(),
            "customer",
            email="c@example.com",
            clerk_user_id="user_x",
            name="C",
            role=None,
            merchant_id=None,
        )


def test_dsr_sets_privacy_hold() -> None:
    customer = SimpleNamespace(
        id="cust-1",
        email="c@example.com",
        clerk_user_id="user_c",
        privacy_status=None,
        privacy_hold_reference=None,
        privacy_hold_at=None,
    )
    db = MagicMock()
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "porterchain_api.compliance_engine.privacy_service.emit_event",
            lambda *a, **k: None,
        )
        result = PrivacyService().request_customer_deletion(db, customer)
    assert result["status"] == "received"
    assert customer.privacy_status == "deletion_hold"
    assert customer.privacy_hold_reference == result["reference"]
    assert customer.privacy_hold_at is not None


def test_verify_syncs_portal_doc_status() -> None:
    driver = SimpleNamespace(
        id="d1",
        license_verified=False,
        insurance_verified=False,
        vehicle_verified=False,
        medical_transport_certified=False,
        background_check_status="pending",
        documents={"license": {"status": "pending_review", "verified": False, "url": "https://x"}},
    )
    db = MagicMock()
    svc = AdminDriverService()
    svc._get_or_raise = MagicMock(return_value=driver)  # type: ignore[method-assign]
    svc.update_verification(
        db,
        MagicMock(),
        "d1",
        license_verified=True,
    )
    assert driver.license_verified is True
    assert driver.documents["license"]["verified"] is True
    assert driver.documents["license"]["status"] == "verified"


def test_create_payout_debits_wallet() -> None:
    from porterchain_api.admin_models import Driver

    driver = SimpleNamespace(id="d1", wallet_balance_cents=5000)
    db = MagicMock()
    db.get = MagicMock(side_effect=lambda model, pk: driver if model is Driver else None)
    added: list[object] = []
    db.add = MagicMock(side_effect=lambda obj: added.append(obj))

    payout = DriverFinanceService().create_payout(db, "d1")
    assert payout.amount_cents == 5000
    assert payout.status == "pending"
    assert driver.wallet_balance_cents == 0
    assert any(getattr(x, "tx_type", None) == "payout" for x in added)
    db.commit.assert_called()


def test_assign_requires_approved_status() -> None:
    from porterchain_api.admin_engine.operations_service import AdminOperationsService
    from porterchain_api.domain.admin_states import DriverStatus

    order = SimpleNamespace(
        id="o1",
        compliance_metadata={},
        assigned_driver_id=None,
        order_number="ORD-1",
        tracking_number="TRK-1",
        customer_id=None,
        merchant_id=None,
    )
    driver = SimpleNamespace(
        id="d1",
        status=DriverStatus.PENDING.value,
        medical_transport_certified=True,
        license_verified=True,
        insurance_verified=True,
        background_check_status="passed",
    )
    db = MagicMock()
    db.query.return_value.filter.return_value.first.side_effect = [order, driver]
    ctx = SimpleNamespace(user=SimpleNamespace(id="admin-1"))
    svc = AdminOperationsService()
    with pytest.raises(ValueError, match="driver_not_approved"):
        svc._assign_driver_no_commit(db, ctx, "o1", "d1")


def test_assign_rejects_uncertified_medical() -> None:
    from porterchain_api.admin_engine.operations_service import AdminOperationsService
    from porterchain_api.domain.admin_states import DriverStatus

    order = SimpleNamespace(
        id="o1",
        compliance_metadata={"chain_of_custody": {"specimen_id": "S1"}},
        assigned_driver_id=None,
        order_number="ORD-1",
        tracking_number="TRK-1",
        customer_id=None,
        merchant_id=None,
    )
    driver = SimpleNamespace(
        id="d1",
        status=DriverStatus.APPROVED.value,
        medical_transport_certified=False,
        license_verified=True,
        insurance_verified=True,
        background_check_status="passed",
    )
    db = MagicMock()
    db.query.return_value.filter.return_value.first.side_effect = [order, driver]
    ctx = SimpleNamespace(user=SimpleNamespace(id="admin-1"))
    svc = AdminOperationsService()
    with pytest.raises(ValueError, match="driver_not_medical_certified"):
        svc._assign_driver_no_commit(db, ctx, "o1", "d1")
