"""Wave 4 Batch E: vehicle soft-rank, stripe/contracts, compliance assign, identity_conflict."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from porterchain_api.admin_engine.control_tower.scoring import (
    driver_verification_gap,
    hard_filter_driver,
)
from porterchain_api.merchant_engine.booking_flow_service import MerchantBookingFlowService


def test_recommend_vehicle_prefs_cannot_downgrade_weight() -> None:
    """M-23: heavy load must not collapse to preferred sedan."""
    svc = MerchantBookingFlowService()
    ctx = SimpleNamespace(merchant=SimpleNamespace(preferred_vehicles=["sedan", "suv"]))
    out = svc.recommend_vehicle(ctx, weight_kg=800)
    assert out["recommended_vehicle"] in ("sprinter_van", "box_16", "box_20", "cargo_van")
    assert out["recommended_vehicle"] != "sedan_suv"
    assert out["eligible_vehicles"][0] != "sedan_suv"


def test_recommend_vehicle_soft_ranks_among_eligible() -> None:
    svc = MerchantBookingFlowService()
    ctx = SimpleNamespace(merchant=SimpleNamespace(preferred_vehicles=["box_20", "sprinter_van"]))
    out = svc.recommend_vehicle(ctx, weight_kg=80)
    # cargo_van floor; box_20 preferred and eligible → pick box_20
    assert out["recommended_vehicle"] == "box_20"


def test_driver_verification_gap() -> None:
    d = SimpleNamespace(
        license_verified=False,
        insurance_verified=True,
        background_check_status="passed",
        documents={},
    )
    assert driver_verification_gap(d) == "driver_license_not_verified"
    d.license_verified = True
    d.background_check_status = "pending"
    assert driver_verification_gap(d) == "driver_background_check_incomplete"
    d.background_check_status = "cleared"
    assert driver_verification_gap(d) is None


def test_assign_rejects_unverified_license() -> None:
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
        status=DriverStatus.APPROVED.value,
        medical_transport_certified=True,
        license_verified=False,
        insurance_verified=True,
        background_check_status="passed",
        documents={},
    )
    db = MagicMock()
    db.query.return_value.filter.return_value.first.side_effect = [order, driver]
    ctx = SimpleNamespace(user=SimpleNamespace(id="admin-1"))
    with pytest.raises(ValueError, match="driver_license_not_verified"):
        AdminOperationsService()._assign_driver_no_commit(db, ctx, "o1", "d1")


def test_hard_filter_excludes_unverified() -> None:
    d = SimpleNamespace(
        license_verified=True,
        insurance_verified=False,
        background_check_status="passed",
        medical_transport_certified=True,
        documents={},
        full_name="X",
        id="1",
    )
    reason = hard_filter_driver(
        d, medical_required=False, required_class=None, classes=set(), skills_needed=[]
    )
    assert reason and "Insurance" in reason


def test_require_customer_maps_identity_conflict() -> None:
    from fastapi import HTTPException

    from porterchain_api.auth.customer import require_customer

    db = MagicMock()
    claims = SimpleNamespace(clerk_user_id="user_staff", email="a@b.com")
    settings = SimpleNamespace()

    with (
        patch("porterchain_api.auth.customer.assert_clerk_id_exclusive"),
        patch(
            "porterchain_api.auth.customer.resolve_customer_contact",
            return_value=("a@b.com", None),
        ),
        patch.object(
            __import__("porterchain_api.auth.customer", fromlist=["_customers"])._customers,
            "get_or_create_from_clerk",
            side_effect=ValueError("identity_conflict:clerk_user_is_admin"),
        ),
    ):
        with pytest.raises(HTTPException) as ei:
            require_customer(db, claims, settings)
    assert ei.value.status_code == 403
    assert "identity_conflict" in str(ei.value.detail)


def test_stripe_enabled_writes_profile() -> None:
    from porterchain_api.admin_engine.merchant_service import AdminMerchantService

    svc = AdminMerchantService()
    merchant = SimpleNamespace(
        id="m1",
        payment_terms="NET_30",
        credit_limit_cents=0,
        pricing_config={},
        billing_cycle="MONTHLY",
        preferred_vehicles=[],
        parent_merchant_id=None,
        profile={},
        company_name="Acme",
        phone=None,
        hst_number=None,
        stripe_enabled=False,
        website=None,
        industry=None,
    )
    db = MagicMock()
    ctx = SimpleNamespace(user=SimpleNamespace(id="admin-1"))
    svc._get_or_raise = MagicMock(return_value=merchant)  # type: ignore[method-assign]
    svc._audit = MagicMock()  # type: ignore[method-assign]

    svc.update_merchant_terms(db, ctx, "m1", stripe_enabled=True)
    assert merchant.stripe_enabled is True
    assert "stripe_enabled" not in (merchant.profile or {})
