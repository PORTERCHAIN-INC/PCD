"""ONB-C — customer portal onboarding gate (CodeGraph: untested within 3 hops)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from porterchain_api.auth.claims import IdentityClaims
from porterchain_api.auth.customer_onboarding import (
    evaluate_customer_onboarding,
    provision_customer_for_onboarding,
    require_customer_portal_ready,
)


def _claims(*, auth_subject: str = "user_cust_1", email: str | None = "c@example.com") -> IdentityClaims:
    return IdentityClaims(auth_subject=auth_subject, email=email, idp_app="customer")


def test_evaluate_ready_when_all_steps_complete() -> None:
    customer = SimpleNamespace(email="c@example.com")
    db = MagicMock()
    settings = MagicMock()
    with (
        patch(
            "porterchain_api.auth.customer_onboarding.allow_auth_dev_bypass",
            return_value=False,
        ),
        patch(
            "porterchain_api.auth.customer_onboarding.subject_staff_portal",
            return_value=None,
        ),
        patch(
            "porterchain_api.admin_engine.platform_settings.portal_enabled",
            return_value=True,
        ),
    ):
        out = evaluate_customer_onboarding(
            db, _claims(), settings=settings, customer=customer, email="c@example.com"
        )
    assert out["ready"] is True
    assert out["can_access_portal"] is True
    assert out["status"] == "active"
    assert out["blockers"] == []
    assert {s["id"] for s in out["steps"]} == {
        "idp_account",
        "email_on_account",
        "customer_provisioned",
        "identity_authorized",
        "portal_enabled",
    }


def test_evaluate_blocks_missing_email_and_customer() -> None:
    db = MagicMock()
    settings = MagicMock()
    with (
        patch(
            "porterchain_api.auth.customer_onboarding.allow_auth_dev_bypass",
            return_value=False,
        ),
        patch(
            "porterchain_api.auth.customer_onboarding.subject_staff_portal",
            return_value=None,
        ),
        patch(
            "porterchain_api.auth.customer_onboarding.load_persona_bundle",
            return_value=SimpleNamespace(customer=None),
        ),
        patch(
            "porterchain_api.admin_engine.platform_settings.portal_enabled",
            return_value=True,
        ),
    ):
        out = evaluate_customer_onboarding(
            db, _claims(email=None), settings=settings, customer=None, email=None
        )
    assert out["ready"] is False
    assert out["can_access_portal"] is False
    assert "email_on_account" in out["blockers"]
    assert "customer_provisioned" in out["blockers"]


def test_evaluate_pending_idp_id_blocks_unless_dev_bypass() -> None:
    customer = SimpleNamespace(email="c@example.com")
    db = MagicMock()
    settings = MagicMock()
    claims = _claims(auth_subject="pending:c@example.com")
    with (
        patch(
            "porterchain_api.auth.customer_onboarding.allow_auth_dev_bypass",
            return_value=False,
        ),
        patch(
            "porterchain_api.auth.customer_onboarding.subject_staff_portal",
            return_value=None,
        ),
        patch(
            "porterchain_api.admin_engine.platform_settings.portal_enabled",
            return_value=True,
        ),
    ):
        out = evaluate_customer_onboarding(
            db, claims, settings=settings, customer=customer, email="c@example.com"
        )
    assert out["identity_linked"] is False
    assert "idp_account" in out["blockers"]

    with (
        patch(
            "porterchain_api.auth.customer_onboarding.allow_auth_dev_bypass",
            return_value=True,
        ),
        patch(
            "porterchain_api.auth.customer_onboarding.subject_staff_portal",
            return_value=None,
        ),
        patch(
            "porterchain_api.admin_engine.platform_settings.portal_enabled",
            return_value=True,
        ),
    ):
        bypassed = evaluate_customer_onboarding(
            db, claims, settings=settings, customer=customer, email="c@example.com"
        )
    assert bypassed["identity_linked"] is True
    assert "clerk_account" not in bypassed["blockers"]


def test_evaluate_staff_conflict_and_portal_disabled() -> None:
    customer = SimpleNamespace(email="c@example.com")
    db = MagicMock()
    settings = MagicMock()
    with (
        patch(
            "porterchain_api.auth.customer_onboarding.allow_auth_dev_bypass",
            return_value=False,
        ),
        patch(
            "porterchain_api.auth.customer_onboarding.subject_staff_portal",
            return_value="admin",
        ),
        patch(
            "porterchain_api.admin_engine.platform_settings.portal_enabled",
            return_value=False,
        ),
    ):
        out = evaluate_customer_onboarding(
            db, _claims(), settings=settings, customer=customer, email="c@example.com"
        )
    assert out["ready"] is False
    assert out["status"] == "disabled"
    assert "identity_authorized" in out["blockers"]
    assert "portal_enabled" in out["blockers"]
    conflict_step = next(s for s in out["steps"] if s["id"] == "identity_authorized")
    assert conflict_step["status"] == "conflict_admin"


def test_require_customer_portal_ready_raises_with_blockers() -> None:
    customer = SimpleNamespace(email=None)
    db = MagicMock()
    with (
        patch(
            "porterchain_api.auth.customer_onboarding.allow_auth_dev_bypass",
            return_value=False,
        ),
        patch(
            "porterchain_api.auth.customer_onboarding.subject_staff_portal",
            return_value=None,
        ),
        patch(
            "porterchain_api.admin_engine.platform_settings.portal_enabled",
            return_value=True,
        ),
    ):
        with pytest.raises(PermissionError, match="customer_onboarding_blocked:"):
            require_customer_portal_ready(db, _claims(email=None), customer, email=None)


def test_require_customer_portal_ready_passes_when_ready() -> None:
    customer = SimpleNamespace(email="c@example.com")
    db = MagicMock()
    with (
        patch(
            "porterchain_api.auth.customer_onboarding.allow_auth_dev_bypass",
            return_value=False,
        ),
        patch(
            "porterchain_api.auth.customer_onboarding.subject_staff_portal",
            return_value=None,
        ),
        patch(
            "porterchain_api.admin_engine.platform_settings.portal_enabled",
            return_value=True,
        ),
    ):
        require_customer_portal_ready(
            db, _claims(), customer, email="c@example.com"
        )


def test_provision_returns_none_on_staff_conflict() -> None:
    db = MagicMock()
    settings = MagicMock()
    with patch(
        "porterchain_api.auth.customer_onboarding.subject_staff_portal",
        return_value="merchant",
    ):
        assert provision_customer_for_onboarding(db, _claims(), settings) is None


def test_provision_returns_none_without_idp_id() -> None:
    db = MagicMock()
    settings = MagicMock()
    claims = IdentityClaims(auth_subject="", email="c@example.com", idp_app="customer")
    assert provision_customer_for_onboarding(db, claims, settings) is None


def test_customer_portal_client_hits_onboarding_endpoint() -> None:
    from pathlib import Path

    onboarding = (
        Path(__file__).resolve().parents[3]
        / "apps"
        / "customer"
        / "src"
        / "lib"
        / "onboarding.ts"
    ).read_text(encoding="utf-8")
    assert "/v1/auth/customer/onboarding" in onboarding
    assert "fetchCustomerOnboarding" in onboarding
