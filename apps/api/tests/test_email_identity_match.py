"""Email identity match — Clerk verified email must equal system profile email."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from porterchain_api.admin_models import AdminUser
from porterchain_api.auth.claims import ClerkClaims
from porterchain_api.auth.email_identity import (
    EMAIL_CLERK_MISMATCH,
    delete_email_mismatched_bindings,
    emails_match,
    normalize_email,
    require_system_email_matches_clerk,
)
from porterchain_api.auth.persona_principal import resolve_persona_principal


def test_normalize_and_match() -> None:
    assert normalize_email("  Admin@PorterChain.com ") == "admin@porterchain.com"
    assert emails_match("Admin@PorterChain.com", "admin@porterchain.com")
    assert not emails_match("admin@porterchain.com", "ravichauhan7434@gmail.com")


def test_require_system_email_matches_clerk() -> None:
    require_system_email_matches_clerk("a@x.com", "A@x.com")
    with pytest.raises(PermissionError, match=EMAIL_CLERK_MISMATCH):
        require_system_email_matches_clerk("admin@porterchain.com", "ravichauhan7434@gmail.com")


def test_delete_mismatched_admin_binding() -> None:
    db = MagicMock()
    admin = AdminUser(
        id="a1",
        clerk_user_id="user_gmail",
        email="admin@porterchain.com",
        name="Mismatch",
        role="super_admin",
    )
    deleted: list[object] = []

    def query(model):
        q = MagicMock()
        if model is AdminUser:
            q.filter.return_value.all.return_value = [admin]
            q.filter.return_value.first.return_value = None
        else:
            q.filter.return_value.all.return_value = []
            q.filter.return_value.first.return_value = None
        return q

    db.query.side_effect = query
    db.delete.side_effect = deleted.append
    n = delete_email_mismatched_bindings(
        db, clerk_user_id="user_gmail", clerk_email="ravichauhan7434@gmail.com"
    )
    assert n == 1
    assert admin in deleted


def test_persona_principal_skips_email_mismatched_admin() -> None:
    db = MagicMock()
    admin = AdminUser(
        id="a1",
        clerk_user_id="user_gmail",
        email="admin@porterchain.com",
        name="Mismatch",
        role="super_admin",
        is_active=True,
    )

    def query(model):
        q = MagicMock()
        if model is AdminUser:
            q.filter.return_value.first.return_value = admin
        else:
            q.filter.return_value.first.return_value = None
        return q

    db.query.side_effect = query
    claims = ClerkClaims(clerk_user_id="user_gmail", email="ravichauhan7434@gmail.com")
    assert resolve_persona_principal(db, claims) is None
