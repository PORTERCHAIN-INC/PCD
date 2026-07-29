"""Fresh auth: SpiceDB tuples from profiles + UX modules catalog."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.rbac import MODULE_PERMISSIONS as ADMIN_MODULES
from porterchain_api.admin_models import Driver
from porterchain_api.auth.current_principal import CurrentPrincipal, RoleAssignmentView
from porterchain_api.auth.ensure_user_service import EnsureUserService
from porterchain_api.auth.identity import AuthenticatedIdentity
from porterchain_api.auth.modules_catalog import (
    ADMIN_MODULE_TO_PERMISSION,
    MERCHANT_MODULE_TO_PERMISSION,
    modules_for_permissions,
)
from porterchain_api.auth.unified_catalog import AccountStatus, AssignableRole, UnifiedPermission
from porterchain_api.authz.client import get_authz_client, reset_authz_client
from porterchain_api.domain.admin_states import DriverStatus
from porterchain_api.domain.merchant_states import MerchantRole, MerchantStatus
from porterchain_api.merchant_engine.rbac import MODULE_PERMISSIONS as MERCHANT_MODULES
from porterchain_api.merchant_models import Merchant, MerchantUser
from porterchain_api.models import Customer


@pytest.fixture(autouse=True)
def _memory_graph(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SPICEDB_ENABLED", "false")
    monkeypatch.setenv("SPICEDB_USE_MEMORY", "true")
    reset_authz_client()
    yield
    reset_authz_client()


def test_modules_catalog_covers_all_admin_modules() -> None:
    missing = set(ADMIN_MODULES) - set(ADMIN_MODULE_TO_PERMISSION)
    assert not missing, f"admin modules missing from catalog: {sorted(missing)}"


def test_modules_catalog_covers_all_merchant_modules() -> None:
    missing = set(MERCHANT_MODULES) - set(MERCHANT_MODULE_TO_PERMISSION)
    assert not missing, f"merchant modules missing from catalog: {sorted(missing)}"


def test_modules_for_permissions_system_all() -> None:
    mods = modules_for_permissions(frozenset({UnifiedPermission.SYSTEM_ALL}))
    assert "dashboard" in mods
    assert "book" in mods


def test_ensure_user_writes_driver_spicedb_tuple(db: Session, settings) -> None:
    from porterchain_api.config import get_settings
    from porterchain_api.authz.client import AuthzClient

    reset_authz_client()
    # Force memory client for this test process
    import porterchain_api.authz.client as client_mod

    client_mod._client = AuthzClient(
        enabled=False, required=False, endpoint="", preshared_key="", use_memory=True
    )

    suffix = uuid4().hex[:8]
    clerk_id = f"clerk_hybrid_{suffix}"
    email = f"driver-{suffix}@hybrid.test"
    driver = Driver(
        clerk_user_id=clerk_id,
        email=email,
        full_name="Hy Brid",
        phone="+15550001111",
        status=DriverStatus.APPROVED.value,
    )
    db.add(driver)
    db.flush()

    identity = AuthenticatedIdentity(
        provider="clerk",
        issuer="https://clerk.test",
        subject=clerk_id,
        email=email,
        email_verified=True,
    )
    user = EnsureUserService().ensure_from_identity(db, identity, email_verified=True, commit=True)
    client = get_authz_client()
    assert client.check(
        resource_type="driver_profile",
        resource_id=driver.id,
        permission="access",
        subject_id=user.id,
    )

    db.delete(driver)
    db.commit()
    EnsureUserService().ensure_from_identity(db, identity, email_verified=True, commit=True)
    assert not client.check(
        resource_type="driver_profile",
        resource_id=driver.id,
        permission="access",
        subject_id=user.id,
    )


def test_ensure_user_org_tuple_and_cross_org_isolation(db: Session) -> None:
    import porterchain_api.authz.client as client_mod
    from porterchain_api.authz.client import AuthzClient

    reset_authz_client()
    client_mod._client = AuthzClient(
        enabled=False, required=False, endpoint="", preshared_key="", use_memory=True
    )

    suffix = uuid4().hex[:8]
    clerk_id = f"clerk_m_{suffix}"
    email = f"ops-{suffix}@hybrid.test"
    org_a = Merchant(
        company_name=f"Org A {suffix}",
        email=f"a-{suffix}@hybrid.test",
        status=MerchantStatus.ACTIVE.value,
        activated_at=datetime.now(UTC),
    )
    org_b = Merchant(
        company_name=f"Org B {suffix}",
        email=f"b-{suffix}@hybrid.test",
        status=MerchantStatus.ACTIVE.value,
        activated_at=datetime.now(UTC),
    )
    db.add_all([org_a, org_b])
    db.flush()
    db.add(
        MerchantUser(
            merchant_id=org_a.id,
            clerk_user_id=clerk_id,
            email=email,
            role=MerchantRole.OPS.value,
            is_active=True,
        )
    )
    db.flush()

    identity = AuthenticatedIdentity(
        provider="clerk",
        issuer="https://clerk.test",
        subject=clerk_id,
        email=email,
        email_verified=True,
    )
    user = EnsureUserService().ensure_from_identity(db, identity, email_verified=True, commit=True)
    client = get_authz_client()
    assert client.check(
        resource_type="organization",
        resource_id=org_a.id,
        permission="portal",
        subject_id=user.id,
    )
    assert not client.check(
        resource_type="organization",
        resource_id=org_b.id,
        permission="portal",
        subject_id=user.id,
    )


def test_customer_spicedb_self_scope(db: Session) -> None:
    import porterchain_api.authz.client as client_mod
    from porterchain_api.authz.client import AuthzClient

    reset_authz_client()
    client_mod._client = AuthzClient(
        enabled=False, required=False, endpoint="", preshared_key="", use_memory=True
    )

    suffix = uuid4().hex[:8]
    clerk_id = f"clerk_c_{suffix}"
    email = f"cust-{suffix}@hybrid.test"
    customer = Customer(clerk_user_id=clerk_id, email=email)
    db.add(customer)
    db.flush()

    identity = AuthenticatedIdentity(
        provider="clerk",
        issuer="https://clerk.test",
        subject=clerk_id,
        email=email,
        email_verified=True,
    )
    user = EnsureUserService().ensure_from_identity(db, identity, email_verified=True, commit=True)
    assert get_authz_client().check(
        resource_type="customer_profile",
        resource_id=customer.id,
        permission="access",
        subject_id=user.id,
    )


def test_session_context_includes_modules() -> None:
    principal = CurrentPrincipal(
        user_id="u1",
        status=AccountStatus.ACTIVE.value,
        onboarding_status="complete",
        email="a@example.com",
        session_id=None,
        default_workspace="admin",
        roles=frozenset({AssignableRole.SUPER_ADMIN}),
        permissions=frozenset({UnifiedPermission.SYSTEM_ALL}),
    )
    ctx = principal.session_context()
    assert "modules" in ctx
    assert "dashboard" in ctx["modules"]


def test_system_all_does_not_inflate_non_admin_workspaces() -> None:
    """Super-admin SpiceDB grant is SYSTEM_ALL + platform.admin — not every portal."""
    principal = CurrentPrincipal(
        user_id="u1",
        status=AccountStatus.ACTIVE.value,
        onboarding_status="complete",
        email="founder@example.com",
        session_id=None,
        default_workspace="admin",
        roles=frozenset({AssignableRole.SUPER_ADMIN}),
        permissions=frozenset(
            {
                UnifiedPermission.PLATFORM_ADMIN_ACCESS,
                UnifiedPermission.SYSTEM_ALL,
            }
        ),
    )
    kinds = {w["kind"] for w in principal.session_context()["workspaces"]}
    assert kinds == {"platform"}
    assert "customer" not in kinds
    assert "organization" not in kinds
    assert "driver" not in kinds


def test_has_organization_scope_helper() -> None:
    principal = CurrentPrincipal(
        user_id="u1",
        status=AccountStatus.ACTIVE.value,
        onboarding_status="complete",
        email="m@example.com",
        session_id=None,
        default_workspace=None,
        roles=frozenset({AssignableRole.MERCHANT_OPS}),
        role_assignments=(
            RoleAssignmentView(
                role_key=AssignableRole.MERCHANT_OPS.value,
                scope_type="organization",
                scope_id="org-a",
            ),
        ),
        permissions=frozenset({UnifiedPermission.MERCHANT_PORTAL_ACCESS}),
        organization_ids=frozenset({"org-a"}),
    )
    assert principal.has_organization_scope("org-a")
    assert not principal.has_organization_scope("org-b")
