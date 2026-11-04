"""G-INS (Ravi 2026-10-29): declared-value cover stays off until a super admin confirms cargo insurance."""

from __future__ import annotations

import pytest

from porterchain_api.admin_engine.settings_bindings import resolve_writable_config_key
from porterchain_api.admin_engine.settings_service import AdminSettingsService
from porterchain_api.domain.admin_states import AdminRole
from porterchain_api.domain.pricing_version import SUPER_ADMIN_ONLY
from porterchain_api.pricing_engine.repository import SqlAlchemyPricingRepository

from uuid import uuid4

from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.admin_models import AdminUser


def _admin(db, role: AdminRole) -> AdminContext:
    s = uuid4().hex[:8]
    user = AdminUser(auth_subject=f"idp_{role.value}_{s}", email=f"{role.value}-{s}@svc.test", name="G-INS test",
                     role=role.value, is_active=True)
    db.add(user)
    db.flush()
    return AdminContext(user=user, role=role)

_OK = {"confirmed": True, "insurer": "Test Insurer", "policy_ref": "POL-TEST-1"}


def test_cargo_insurance_is_super_admin_only_and_off_by_default(db, admin_ctx) -> None:
    svc = AdminSettingsService()
    assert resolve_writable_config_key("cargo_insurance", reason="x") == "cargo_insurance"
    assert svc.get_config_value(db, "cargo_insurance")["confirmed"] is False
    with pytest.raises(PermissionError, match=SUPER_ADMIN_ONLY):
        svc.set_config(db, _admin(db, AdminRole.ADMIN), "cargo_insurance", _OK, reason="nope")
    with pytest.raises(ValueError, match="cargo_insurance_needs_insurer_and_policy_ref"):
        svc.set_config(db, admin_ctx, "cargo_insurance", {"confirmed": True}, reason="incomplete")
    saved = svc.set_config(db, admin_ctx, "cargo_insurance", _OK, reason="insurer confirmed")
    assert saved.value["confirmed"] is True and saved.value["policy_ref"] == "POL-TEST-1"


def test_parcel_coverage_enabled_stays_off_until_confirmed(db, admin_ctx) -> None:
    from porterchain_pricing.coverage import normalize_coverage

    svc = AdminSettingsService()
    svc.set_config(db, admin_ctx, "parcel_coverage", {"enabled": True}, reason="try to turn on")
    db.flush()
    repo = SqlAlchemyPricingRepository(db)
    assert normalize_coverage(repo._load_system_value("parcel_coverage"), repo._load_system_value("cargo_insurance"))["enabled"] is False
    svc.set_config(db, admin_ctx, "cargo_insurance", _OK, reason="insurer confirmed")
    db.flush()
    repo = SqlAlchemyPricingRepository(db)
    assert normalize_coverage(repo._load_system_value("parcel_coverage"), repo._load_system_value("cargo_insurance"))["enabled"] is True


@pytest.fixture(autouse=True)
def _reset_settings(db, admin_ctx):
    """set_config commits; put both settings back so later tests see the shipped (off) state."""
    yield
    svc = AdminSettingsService()
    svc.set_config(db, admin_ctx, "cargo_insurance", {"confirmed": False}, reason="test reset")
    svc.set_config(db, admin_ctx, "parcel_coverage", {"enabled": False}, reason="test reset")
