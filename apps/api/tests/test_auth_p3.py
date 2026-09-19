"""P3 authz: catalog/schema parity + multi-persona session projection."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from porterchain_api.admin_engine.rbac import MODULE_PERMISSIONS
from porterchain_api.auth.current_principal import CurrentPrincipal, _workspaces_for
from porterchain_api.auth.unified_catalog import UnifiedPermission
from porterchain_api.authz.client import AuthzClient, Relationship, reset_authz_client
from porterchain_api.authz.platform_roles import to_schema_permission
from porterchain_api.authz.tuples import PLATFORM_ID

_SCHEMA = Path(__file__).resolve().parents[1] / "src/porterchain_api/authz/schema.zed"

# Must match packages/auth PORTAL_ACCESS_PERMISSION + system:all.
_PORTAL_PERM = {
    "admin": "platform.admin.access",
    "merchant": "merchant_portal.access",
    "driver": "driver_portal.access",
    "customer": "customer_portal.access",
}


@pytest.fixture(autouse=True)
def _memory_authz(monkeypatch: pytest.MonkeyPatch):
    reset_authz_client()
    monkeypatch.setenv("SPICEDB_USE_MEMORY", "true")
    monkeypatch.setenv("SPICEDB_ENABLED", "false")
    yield
    reset_authz_client()


def test_schema_covers_all_admin_module_permissions() -> None:
    schema = _SCHEMA.read_text(encoding="utf-8")
    block = re.search(r"definition platform \{(.*?)\}", schema, flags=re.DOTALL)
    assert block, "platform definition missing"
    body = block.group(1)
    declared = set(re.findall(r"(?m)^\s*permission\s+(\w+)\s*=", body))
    missing = []
    for module in MODULE_PERMISSIONS:
        name = to_schema_permission(module)
        if name not in declared:
            missing.append(f"{module}→{name}")
    assert not missing, f"schema.zed missing platform permissions: {missing}"


def test_unified_permission_values_match_portal_access_keys() -> None:
    assert UnifiedPermission.PLATFORM_ADMIN_ACCESS.value == _PORTAL_PERM["admin"]
    assert UnifiedPermission.MERCHANT_PORTAL_ACCESS.value == _PORTAL_PERM["merchant"]
    assert UnifiedPermission.DRIVER_PORTAL_ACCESS.value == _PORTAL_PERM["driver"]
    assert UnifiedPermission.CUSTOMER_PORTAL_ACCESS.value == _PORTAL_PERM["customer"]
    assert UnifiedPermission.SYSTEM_ALL.value == "system:all"


def test_multi_persona_session_projects_admin_and_merchant_workspaces() -> None:
    """Admin+merchant on one user → both workspaces (picker input), not admin-only."""
    principal = CurrentPrincipal(
        user_id="u-multi",
        status="active",
        onboarding_status="complete",
        email="multi@example.com",
        session_id=None,
        default_workspace=None,
        roles=frozenset(),
        role_assignments=(),
        permissions=frozenset(
            {
                UnifiedPermission.PLATFORM_ADMIN_ACCESS,
                UnifiedPermission.MERCHANT_PORTAL_ACCESS,
            }
        ),
        organization_ids=frozenset({"org-1"}),
        auth_subject="clerk_multi",
        auth_issuer=None,
        auth_provider="clerk",
        legacy_profile_ids={},
    )
    ctx = principal.session_context()
    kinds = {w["kind"] for w in ctx["workspaces"]}
    assert kinds == {"platform", "organization"}
    assert _PORTAL_PERM["admin"] in ctx["permissions"]
    assert _PORTAL_PERM["merchant"] in ctx["permissions"]
    # system:all alone must not invent merchant workspace
    sa = CurrentPrincipal(
        user_id="u-sa",
        status="active",
        onboarding_status="complete",
        email="sa@example.com",
        session_id=None,
        default_workspace=None,
        roles=frozenset(),
        role_assignments=(),
        permissions=frozenset({UnifiedPermission.SYSTEM_ALL}),
        organization_ids=frozenset(),
        auth_subject="clerk_sa",
        auth_issuer=None,
        auth_provider="clerk",
        legacy_profile_ids={},
    )
    assert [w["kind"] for w in _workspaces_for(sa)] == ["platform"]


def test_authz_client_works_inside_running_asyncio_loop() -> None:
    """Regression: authzed Client used aio channel under uvicorn → empty perms → customer."""
    import asyncio

    from porterchain_api.authz.client import AuthzClient, Relationship
    from porterchain_api.authz.tuples import PLATFORM_ID

    async def _run() -> None:
        # Force a fresh client path similar to API process (loop already running).
        client = AuthzClient(
            enabled=True,
            required=False,
            endpoint="localhost:50051",
            preshared_key="porterchain-spicedb-dev-key",
            use_memory=False,
        )
        if client._use_memory:  # noqa: SLF001
            pytest.skip("SpiceDB not reachable")
        assert type(client._grpc).__name__ == "InsecureClient"  # noqa: SLF001
        uid = "loop-regression-user"
        client.write_relationships(
            [Relationship("platform", PLATFORM_ID, "super_admin", "user", uid)]
        )
        assert client.check(
            resource_type="platform",
            resource_id=PLATFORM_ID,
            permission="portal",
            subject_id=uid,
        )
        assert client.check(
            resource_type="platform",
            resource_id=PLATFORM_ID,
            permission="system_all",
            subject_id=uid,
        )

    asyncio.run(_run())
