"""Audited impersonation — Super Admin break-glass only."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest

from porterchain_api.admin_engine.impersonation_service import ImpersonationService
from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.admin_engine.staff_lookups import ensure_local_super_admin
from porterchain_api.admin_models import Driver
import porterchain_api.crm_models  # noqa: F401 — register crm_leads FK target for Driver
from porterchain_api.auth.impersonation_session import (
    IMP_BEARER_PREFIX,
    bearer_token_for_session,
    create_session,
    get_session,
    resolve_from_bearer,
    revoke_session,
)
from porterchain_api.domain.admin_states import AdminRole, DriverStatus


class _FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    def ping(self) -> bool:
        return True

    def setex(self, key: str, ttl: int, value: str) -> None:
        self.store[key] = value

    def get(self, key: str) -> str | None:
        return self.store.get(key)

    def delete(self, key: str) -> int:
        return 1 if self.store.pop(key, None) is not None else 0


@pytest.fixture
def fake_redis():
    client = _FakeRedis()
    with patch(
        "porterchain_api.auth.impersonation_session._client",
        return_value=client,
    ):
        yield client


def _super_ctx(db) -> AdminContext:
    user = ensure_local_super_admin(db)
    return AdminContext(user=user, role=AdminRole.SUPER_ADMIN)


def _admin_ctx() -> AdminContext:
    user = MagicMock()
    user.id = "admin-plain-1"
    user.email = "plain-admin@porterchain.com"
    return AdminContext(user=user, role=AdminRole.ADMIN)


def test_create_session_requires_reason(fake_redis) -> None:
    with pytest.raises(ValueError, match="impersonation_reason_too_short"):
        create_session(
            actor_admin_id="a1",
            actor_email="a@porterchain.com",
            actor_role="super_admin",
            target_type="driver",
            target_id="d1",
            target_email="d@example.com",
            reason="short",
        )


def test_create_and_resolve_session(fake_redis) -> None:
    session = create_session(
        actor_admin_id="a1",
        actor_email="a@porterchain.com",
        actor_role="super_admin",
        target_type="driver",
        target_id="d1",
        target_email="d@example.com",
        reason="Support ticket review of missing jobs",
    )
    assert session is not None
    bearer = bearer_token_for_session(session.session_id)
    assert bearer.startswith(IMP_BEARER_PREFIX)
    loaded = resolve_from_bearer(bearer)
    assert loaded is not None
    assert loaded.target_id == "d1"
    assert revoke_session(session.session_id)
    assert get_session(session.session_id) is None


def test_start_forbidden_for_non_super_admin(db, settings, fake_redis) -> None:
    driver = Driver(
        full_name="Imp Driver",
        email=f"imp-{uuid.uuid4().hex[:8]}@example.com",
        status=DriverStatus.APPROVED.value,
        clerk_user_id=f"pending:imp-{uuid.uuid4().hex[:8]}@example.com",
    )
    db.add(driver)
    db.commit()
    with pytest.raises(PermissionError, match="impersonation_super_admin_only"):
        ImpersonationService().start(
            db,
            _admin_ctx(),
            settings,
            target_type="driver",
            target_id=driver.id,
            reason="Trying to open as driver without super admin",
        )


def test_start_ok_for_super_admin(db, settings, fake_redis) -> None:
    driver = Driver(
        full_name="Imp Driver SA",
        email=f"imp-sa-{uuid.uuid4().hex[:8]}@example.com",
        status=DriverStatus.APPROVED.value,
        clerk_user_id=f"pending:imp-sa-{uuid.uuid4().hex[:8]}@example.com",
    )
    db.add(driver)
    db.commit()
    out = ImpersonationService().start(
        db,
        _super_ctx(db),
        settings,
        target_type="driver",
        target_id=driver.id,
        reason="Support ticket #99 — verify earnings screen",
    )
    assert out["target_type"] == "driver"
    assert out["bearer_token"].startswith(IMP_BEARER_PREFIX)
    assert "/impersonate?token=" in out["portal_bootstrap_url"]
    assert out["seconds_remaining"] > 0


def test_driver_context_accepts_impersonation_bearer(db, settings, fake_redis) -> None:
    import asyncio

    from porterchain_api.auth.driver import get_driver_context

    driver = Driver(
        full_name="Ctx Driver",
        email=f"ctx-{uuid.uuid4().hex[:8]}@example.com",
        status=DriverStatus.APPROVED.value,
        clerk_user_id=f"pending:ctx-{uuid.uuid4().hex[:8]}@example.com",
    )
    db.add(driver)
    db.commit()
    session = create_session(
        actor_admin_id="a1",
        actor_email="a@porterchain.com",
        actor_role="super_admin",
        target_type="driver",
        target_id=driver.id,
        target_email=driver.email,
        reason="Context acceptance check for driver portal",
    )
    assert session is not None
    creds = MagicMock()
    creds.credentials = bearer_token_for_session(session.session_id)
    ctx = asyncio.run(
        get_driver_context(db=db, settings=settings, credentials=creds, x_driver_id=None)
    )
    assert ctx.driver.id == driver.id
