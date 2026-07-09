"""Shared fixtures for service-layer coverage tests."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.admin_models import AdminUser, Driver
from porterchain_api.booking_engine.numbers import generate_order_number, generate_tracking_number
from porterchain_api.domain.admin_states import AdminRole, DriverStatus
from porterchain_api.domain.merchant_states import MerchantRole, MerchantStatus
from porterchain_api.domain.states import OrderState
from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_api.merchant_models import Merchant, MerchantUser
from porterchain_api.models import Order


def _addr() -> dict:
    return {"formatted": "1 King St W, Toronto", "lat": 43.6488, "lng": -79.3817}


@pytest.fixture(autouse=True)
def ensure_pricing_data(db: Session) -> None:
    """Seed minimal pricing tariff + zone so merchant preview/simulate work."""
    from porterchain_api.admin_models import PricingTariff, PricingZone

    if not db.query(PricingTariff).filter(PricingTariff.is_active.is_(True)).first():
        db.add(
            PricingTariff(
                name="Test Merchant Cargo Van",
                tariff_type="merchant",
                vehicle_class="cargoVan",
                zone="gta_core",
                base_cents=1500,
                per_km_cents=110,
                is_active=True,
                config={},
            )
        )
    bounds = {"min_lat": 43.58, "max_lat": 43.78, "min_lng": -79.55, "max_lng": -79.25}
    for zone in db.query(PricingZone).all():
        if not zone.bounds or "min_lat" not in (zone.bounds or {}):
            zone.bounds = bounds
    if not db.query(PricingZone).filter(PricingZone.code == "gta_core").first():
        db.add(PricingZone(code="gta_core", name="GTA Core", bounds=bounds, multiplier=1.0))
    db.commit()


@pytest.fixture
def admin_ctx(db: Session) -> AdminContext:
    suffix = uuid4().hex[:8]
    user = AdminUser(
        clerk_user_id=f"clerk_admin_{suffix}",
        email=f"admin-{suffix}@svc.test",
        name="Service Test Admin",
        role=AdminRole.SUPER_ADMIN.value,
        is_active=True,
    )
    db.add(user)
    db.flush()
    return AdminContext(user=user, role=AdminRole.SUPER_ADMIN)


@pytest.fixture
def merchant_ctx(db: Session) -> MerchantContext:
    suffix = uuid4().hex[:8]
    merchant = Merchant(
        company_name=f"Svc Merchant {suffix}",
        email=f"merchant-{suffix}@svc.test",
        status=MerchantStatus.ACTIVE.value,
    )
    db.add(merchant)
    db.flush()
    user = MerchantUser(
        merchant_id=merchant.id,
        clerk_user_id=f"clerk_merchant_{suffix}",
        email=f"user-{suffix}@svc.test",
        role=MerchantRole.OPS.value,
    )
    db.add(user)
    db.flush()
    return MerchantContext(merchant=merchant, user=user, role=MerchantRole.OPS)


@pytest.fixture
def dispatch_order(db: Session, merchant_ctx: MerchantContext) -> Order:
    order = Order(
        order_number=generate_order_number(),
        tracking_number=generate_tracking_number(),
        state=OrderState.DISPATCH_READY.value,
        merchant_id=merchant_ctx.merchant.id,
        amount_cents=3200,
        currency="cad",
        pickup=_addr(),
        dropoff=_addr(),
        scheduled_at=datetime.now(UTC),
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


@pytest.fixture
def driver(db: Session) -> Driver:
    suffix = uuid4().hex[:8]
    row = Driver(
        email=f"driver-{suffix}@svc.test",
        full_name=f"Driver {suffix}",
        status=DriverStatus.APPROVED.value,
        clerk_user_id=f"clerk_driver_{suffix}",
        is_online=True,
    )
    db.add(row)
    db.flush()
    return row
