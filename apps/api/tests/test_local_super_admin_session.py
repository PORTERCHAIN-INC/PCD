"""Local Super Admin — Staff IdP session mint (development)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from porterchain_api.admin_engine.staff_idp_service import StaffIdpService
from porterchain_api.admin_engine.staff_lookups import (
    LOCAL_SUPER_ADMIN_EMAIL,
    LOCAL_SUPER_ADMIN_NAME,
    ensure_local_super_admin,
)
from porterchain_api.domain.admin_states import AdminRole


def test_ensure_local_super_admin_forces_super_admin(db) -> None:
    user = ensure_local_super_admin(db)
    assert user.email == LOCAL_SUPER_ADMIN_EMAIL
    assert user.name == LOCAL_SUPER_ADMIN_NAME
    assert user.role == AdminRole.SUPER_ADMIN.value
    assert user.is_active is True
    assert user.porterchain_user_id
    assert str(user.clerk_user_id).startswith("staff:")

    # Idempotent upgrade — weaker role cannot stick.
    user.role = "read_only"
    db.commit()
    again = ensure_local_super_admin(db)
    assert again.id == user.id
    assert again.role == AdminRole.SUPER_ADMIN.value


def test_mint_local_super_admin_session_requires_dev_bypass(db, settings) -> None:
    settings.clerk_dev_bypass = False
    with pytest.raises(ValueError, match="local_super_admin_disabled"):
        StaffIdpService().mint_local_super_admin_session(db, settings)


@patch("porterchain_api.admin_engine.staff_idp_service.create_session")
def test_mint_local_super_admin_session_ok(mock_create, db, settings) -> None:
    settings.clerk_dev_bypass = True
    settings.app_env = "development"
    mock_create.return_value = MagicMock(
        session_id="sess_local_1",
        expires_at=9999999999.0,
    )
    out = StaffIdpService().mint_local_super_admin_session(db, settings)
    assert out["role"] == AdminRole.SUPER_ADMIN.value
    assert out["designation"] == "super_admin"
    assert out["environment"] == "development"
    assert out["email"] == LOCAL_SUPER_ADMIN_EMAIL
    assert out["bearer_token"] == "staff_sess_sess_local_1"
    mock_create.assert_called_once()


def test_ensure_staff_identity_resyncs_spicedb_when_already_bound(db) -> None:
    """Regression: bound staff:{id} must still write platform#portal (Access denied fix)."""
    from porterchain_api.admin_engine.staff_idp_service import ensure_staff_identity
    from porterchain_api.authz.client import get_authz_client
    from porterchain_api.authz.tuples import PLATFORM_ID

    user = ensure_local_super_admin(db)
    client = get_authz_client()
    mem = getattr(client, "_memory", None)
    assert mem is not None
    with mem.lock:
        mem.relationships = {
            t
            for t in mem.relationships
            if not (t[3] == "user" and t[4] == user.porterchain_user_id)
        }
    # Previously early-returned without sync when already staff-bound.
    ensure_staff_identity(db, user)
    assert client.check(
        resource_type="platform",
        resource_id=PLATFORM_ID,
        permission="portal",
        subject_id=user.porterchain_user_id,
    )
    assert client.check(
        resource_type="platform",
        resource_id=PLATFORM_ID,
        permission="system_all",
        subject_id=user.porterchain_user_id,
    )
