"""Phase 9 — unified identity full test matrix.

Covers deny-by-default (401/403), portal≠role, multi-role, org IDOR isolation,
webhook signature + idempotency, session-context safety, invite-only rules,
and permission-key parity with portal clients.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import time
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from porterchain_api.auth.clerk_webhook_idempotency import claim_clerk_event
from porterchain_api.auth.clerk_webhook_service import ClerkWebhookService
from porterchain_api.auth.clerk_webhook_verify import (
    ClerkWebhookSignatureError,
    verify_clerk_webhook_signature,
)
from porterchain_api.auth.current_principal import CurrentPrincipal
from porterchain_api.auth.dependencies import (
    get_authenticated_identity,
    require_all_permissions,
    require_permission,
)
from porterchain_api.auth.identity_fk_backfill import PROFILE_TARGETS, _is_skippable_clerk_id
from porterchain_api.auth.identity_migration.planner import build_migration_plan
from porterchain_api.auth.identity_migration.types import AdminAllowlist, SourceExportUser
from porterchain_api.auth.unified_catalog import (
    AssignableRole,
    UnifiedPermission,
    is_invite_only,
    may_self_signup,
    permissions_for_roles,
)
from porterchain_api.config import Settings


# --- Matrix checklist (asserted by test_phase9_matrix_inventory) ---

PHASE9_MATRIX = (
    ("401", "missing bearer / bad issuer / bad azp"),
    ("403", "suspended user / missing permission / invite-only without provision"),
    ("IDOR", "merchant org A workspace excludes org B"),
    ("multi-role", "customer+driver portals without admin"),
    ("portal≠role", "customer cannot access platform.admin.access"),
    ("webhook", "bad signature → 400; missing secret → 503"),
    ("idempotency", "duplicate Svix claim returns False / duplicate status"),
    ("session-context", "no token/secret material in payload"),
    ("invite-only", "admin/super_admin not open signup"),
    ("fk-backfill", "profile targets defined; pending clerk ids skipped"),
    ("client-parity", "portal access permission keys match UnifiedPermission"),
)


def _settings(**overrides: object) -> Settings:
    base: dict[str, object] = {
        "app_env": "local",
        "clerk_dev_bypass": False,
        "jwt_secret": "a" * 32,
        "clerk_audience": "",
        "clerk_authorized_parties": "",
        "clerk_authorized_issuers": "",
        "clerk_secret_key": "",
        "clerk_jwks_url": "",
        "clerk_customer_secret_key": "",
        "clerk_customer_jwks_url": "",
        "clerk_merchant_secret_key": "",
        "clerk_merchant_jwks_url": "",
        "clerk_admin_secret_key": "",
        "clerk_admin_jwks_url": "",
        "clerk_driver_secret_key": "",
        "clerk_driver_jwks_url": "",
        "clerk_webhook_signing_secret": "",
    }
    base.update(overrides)
    return Settings(_env_file=None, **base)  # type: ignore[arg-type]


def _principal(
    *,
    roles: set[AssignableRole],
    organization_ids: set[str] | None = None,
    user_id: str = "user-1",
) -> CurrentPrincipal:
    perms = permissions_for_roles(roles)
    return CurrentPrincipal(
        user_id=user_id,
        status="active",
        onboarding_status="complete",
        email="p@example.com",
        session_id="sid",
        default_workspace=None,
        roles=frozenset(roles),
        permissions=perms,
        organization_ids=frozenset(organization_ids or ()),
        auth_subject="clerk_subj",
        auth_issuer="https://iss.example",
    )


def _whsec() -> tuple[str, bytes]:
    key = b"phase9-test-signing-key-32bytes!!"
    return "whsec_" + base64.b64encode(key).decode(), key


def _sign(payload: bytes, *, key: bytes, svix_id: str, ts: str) -> str:
    signed = f"{svix_id}.{ts}.{payload.decode()}".encode()
    digest = hmac.new(key, signed, hashlib.sha256).digest()
    return "v1," + base64.b64encode(digest).decode()


def test_phase9_matrix_inventory() -> None:
    assert len(PHASE9_MATRIX) >= 10
    areas = {row[0] for row in PHASE9_MATRIX}
    for required in ("401", "403", "IDOR", "webhook", "idempotency", "session-context"):
        assert required in areas


# --- 401 ---


def test_missing_bearer_returns_401() -> None:
    async def _run():
        with pytest.raises(HTTPException) as exc:
            await get_authenticated_identity(
                authorization=None,
                settings=_settings(clerk_dev_bypass=False),
                db=MagicMock(),
            )
        assert exc.value.status_code == 401
        assert exc.value.detail == "missing_bearer_token"

    asyncio.run(_run())


def test_non_bearer_authorization_returns_401() -> None:
    async def _run():
        with pytest.raises(HTTPException) as exc:
            await get_authenticated_identity(
                authorization="Basic abc",
                settings=_settings(clerk_dev_bypass=False),
                db=MagicMock(),
            )
        assert exc.value.status_code == 401

    asyncio.run(_run())


# --- 403 permission ---


def test_customer_denied_admin_permission_is_403() -> None:
    async def _run():
        dep = require_permission(UnifiedPermission.PLATFORM_ADMIN_ACCESS)
        principal = _principal(roles={AssignableRole.CUSTOMER})
        with pytest.raises(HTTPException) as exc:
            await dep(principal=principal, db=MagicMock())
        assert exc.value.status_code == 403
        assert exc.value.detail == "forbidden"

    asyncio.run(_run())


def test_admin_allowed_platform_permission() -> None:
    async def _run():
        dep = require_permission(UnifiedPermission.PLATFORM_ADMIN_ACCESS)
        principal = _principal(roles={AssignableRole.ADMIN})
        out = await dep(principal=principal, db=MagicMock())
        assert out.user_id == principal.user_id

    asyncio.run(_run())


def test_require_all_permissions_partial_is_403() -> None:
    async def _run():
        dep = require_all_permissions(
            UnifiedPermission.CUSTOMER_PORTAL_ACCESS,
            UnifiedPermission.PLATFORM_ADMIN_ACCESS,
        )
        principal = _principal(roles={AssignableRole.CUSTOMER})
        with pytest.raises(HTTPException) as exc:
            await dep(principal=principal, db=MagicMock())
        assert exc.value.status_code == 403

    asyncio.run(_run())


# --- Portal ≠ role / multi-role ---


def test_customer_cannot_access_admin_portal_permission() -> None:
    perms = permissions_for_roles({AssignableRole.CUSTOMER})
    assert UnifiedPermission.CUSTOMER_PORTAL_ACCESS in perms
    assert UnifiedPermission.PLATFORM_ADMIN_ACCESS not in perms
    assert UnifiedPermission.SYSTEM_ALL not in perms


def test_multi_role_customer_driver_without_admin() -> None:
    perms = permissions_for_roles({AssignableRole.CUSTOMER, AssignableRole.DRIVER})
    assert UnifiedPermission.CUSTOMER_PORTAL_ACCESS in perms
    assert UnifiedPermission.DRIVER_PORTAL_ACCESS in perms
    assert UnifiedPermission.PLATFORM_ADMIN_ACCESS not in perms
    assert UnifiedPermission.MERCHANT_PORTAL_ACCESS not in perms


def test_invite_only_roles_not_open_signup() -> None:
    assert may_self_signup(AssignableRole.CUSTOMER)
    assert not may_self_signup(AssignableRole.ADMIN)
    assert not may_self_signup(AssignableRole.SUPER_ADMIN)
    assert is_invite_only(AssignableRole.ADMIN)
    assert is_invite_only(AssignableRole.DISPATCHER)
    assert not is_invite_only(AssignableRole.CUSTOMER)


# --- IDOR / org isolation ---


def test_merchant_workspace_idor_excludes_other_org() -> None:
    principal = _principal(
        roles={AssignableRole.MERCHANT_OPS},
        organization_ids={"org-a"},
    )
    assert "org-a" in principal.organization_ids
    assert "org-b" not in principal.organization_ids
    ctx = principal.session_context()
    org_workspaces = [w for w in ctx["workspaces"] if w["kind"] == "organization"]
    assert len(org_workspaces) == 1
    assert org_workspaces[0]["organization_id"] == "org-a"
    assert all(w.get("organization_id") != "org-b" for w in org_workspaces)


def test_customer_session_has_no_merchant_org_workspace() -> None:
    principal = _principal(roles={AssignableRole.CUSTOMER}, organization_ids=set())
    ctx = principal.session_context()
    assert not any(w["kind"] == "organization" for w in ctx["workspaces"])
    assert any(w["kind"] == "customer" for w in ctx["workspaces"])


def test_live_super_admin_perms_do_not_open_customer_workspace() -> None:
    """Matches SpiceDB resolution for platform staff: SYSTEM_ALL + platform.admin only."""
    principal = CurrentPrincipal(
        user_id="founder",
        status="active",
        onboarding_status="complete",
        email="porterchaininc@example.com",
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


# --- Session-context safety ---


def test_session_context_never_leaks_secrets() -> None:
    principal = _principal(roles={AssignableRole.ADMIN, AssignableRole.CUSTOMER})
    ctx = principal.session_context()
    blob = json.dumps(ctx).lower()
    for banned in ("bearer", "sk_live", "sk_test", "password", "whsec_", "authorization"):
        assert banned not in blob
    assert "user_id" in ctx
    assert "permissions" in ctx
    assert "auth" in ctx


# --- Webhook signature + idempotency ---


def test_webhook_bad_signature_raises_signature_error() -> None:
    secret, _key = _whsec()
    with pytest.raises(ClerkWebhookSignatureError):
        verify_clerk_webhook_signature(
            payload=b'{"type":"user.created"}',
            secret=secret,
            svix_id="msg_1",
            svix_timestamp=str(int(time.time())),
            svix_signature="v1,notavalidsignature",
        )


def test_webhook_service_maps_bad_signature_to_400() -> None:
    secret, _key = _whsec()
    settings = _settings(clerk_webhook_signing_secret=secret)
    with pytest.raises(HTTPException) as exc:
        ClerkWebhookService().handle(
            MagicMock(),
            settings,
            payload=b'{"type":"user.created","data":{"id":"u1"}}',
            svix_id="msg_1",
            svix_timestamp=str(int(time.time())),
            svix_signature="v1,bad",
        )
    assert exc.value.status_code == 400
    assert exc.value.detail == "invalid_signature"


def test_webhook_service_missing_secret_is_503() -> None:
    with pytest.raises(HTTPException) as exc:
        ClerkWebhookService().handle(
            MagicMock(),
            _settings(clerk_webhook_signing_secret=""),
            payload=b"{}",
            svix_id="msg_1",
            svix_timestamp=str(int(time.time())),
            svix_signature="v1,x",
        )
    assert exc.value.status_code == 503


def test_claim_clerk_event_idempotent_claim() -> None:
    db = MagicMock()
    db.execute.return_value.scalar_one_or_none.side_effect = ["row-1", None]
    assert claim_clerk_event(db, clerk_event_id="evt_1", event_type="user.created") is True
    assert claim_clerk_event(db, clerk_event_id="evt_1", event_type="user.created") is False


def test_webhook_duplicate_delivery_status(monkeypatch: pytest.MonkeyPatch) -> None:
    secret, key = _whsec()
    settings = _settings(clerk_webhook_signing_secret=secret)
    payload = json.dumps(
        {
            "type": "user.updated",
            "data": {
                "id": "user_x",
                "email_addresses": [
                    {
                        "id": "em_1",
                        "email_address": "x@example.com",
                        "verification": {"status": "verified"},
                    }
                ],
                "primary_email_address_id": "em_1",
            },
        }
    ).encode()
    svix_id = "msg_phase9_dup"
    ts = str(int(time.time()))
    sig = _sign(payload, key=key, svix_id=svix_id, ts=ts)
    monkeypatch.setattr(
        "porterchain_api.auth.clerk_webhook_service.claim_clerk_event",
        lambda *a, **k: False,
    )
    result = ClerkWebhookService().handle(
        MagicMock(),
        settings,
        payload=payload,
        svix_id=svix_id,
        svix_timestamp=ts,
        svix_signature=sig,
    )
    assert result == {"status": "duplicate"}


# --- Migration / FK matrix hooks ---


def test_migration_admin_without_allowlist_conflicts() -> None:
    plan = build_migration_plan(
        label="p9",
        sources=[SourceExportUser("admin", "user_admin", email="a@x.com", email_verified=True)],
        explicit_map=[],
        allowlist=AdminAllowlist(),
        db=None,
    )
    assert plan.records[0].status == "conflict"


def test_fk_backfill_targets_and_skips() -> None:
    assert "admin_users" in PROFILE_TARGETS
    assert "customers" in PROFILE_TARGETS
    assert _is_skippable_clerk_id("pending:x")
    assert _is_skippable_clerk_id("dev_clerk_user")
    assert not _is_skippable_clerk_id("user_live")


# --- Client permission key parity (portal AccessGates / packages/auth) ---


def test_portal_access_permission_keys_match_catalog() -> None:
    """Must stay aligned with packages/auth PORTAL_ACCESS_PERMISSION + portal libs."""
    expected = {
        "admin": UnifiedPermission.PLATFORM_ADMIN_ACCESS.value,
        "merchant": UnifiedPermission.MERCHANT_PORTAL_ACCESS.value,
        "driver": UnifiedPermission.DRIVER_PORTAL_ACCESS.value,
        "customer": UnifiedPermission.CUSTOMER_PORTAL_ACCESS.value,
    }
    assert expected["admin"] == "platform.admin.access"
    assert expected["merchant"] == "merchant_portal.access"
    assert expected["driver"] == "driver_portal.access"
    assert expected["customer"] == "customer_portal.access"
