"""Phase 8 — porterchain_user_id FK columns + backfill resolver (no elevate)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from porterchain_api.admin_models import AdminUser, Driver
from porterchain_api.auth.identity_fk_backfill import (
    PROFILE_TARGETS,
    BackfillAction,
    _is_skippable_clerk_id,
    resolve_porterchain_user_id,
)
from porterchain_api.booking_models import Customer
from porterchain_api.invitation_models import UserInvitation
from porterchain_api.merchant_models import MerchantUser


def test_profile_models_expose_porterchain_user_id() -> None:
    for model in (AdminUser, MerchantUser, Customer, Driver, UserInvitation):
        assert hasattr(model, "porterchain_user_id")
        assert hasattr(model, "clerk_user_id")


def test_profile_targets_cover_five_tables() -> None:
    assert set(PROFILE_TARGETS) == {
        "admin_users",
        "merchant_users",
        "customers",
        "drivers",
        "user_invitations",
    }


def test_skippable_clerk_ids() -> None:
    assert _is_skippable_clerk_id(None)
    assert _is_skippable_clerk_id("")
    assert _is_skippable_clerk_id("pending:abc")
    assert _is_skippable_clerk_id("dev_clerk_user")
    assert not _is_skippable_clerk_id("user_abc")


def test_resolve_via_porterchain_users() -> None:
    db = MagicMock()
    user = SimpleNamespace(id="pc-1", clerk_user_id="user_abc")
    q = MagicMock()
    q.filter.return_value.first.return_value = user
    db.query.return_value = q

    resolved, method = resolve_porterchain_user_id(db, "user_abc")
    assert resolved == "pc-1"
    assert method == "porterchain_users"


def test_resolve_via_identity_link_when_platform_is_pc_user() -> None:
    from porterchain_api.identity_models import IdentityLink
    from porterchain_api.user_models import PorterchainUser

    db = MagicMock()
    link = SimpleNamespace(
        clerk_user_id="user_abc",
        subject="user_abc",
        platform_user_id="pc-from-link",
        email=None,
    )
    pc = SimpleNamespace(id="pc-from-link")

    def query(model):
        q = MagicMock()
        if model is PorterchainUser:
            def first():
                # Distinguish clerk_user_id lookup vs id lookup by inspecting filter args is hard;
                # use call count: 1st PorterchainUser query = by clerk (miss), 2nd = by id (hit)
                n = getattr(query, "_pc_n", 0) + 1
                query._pc_n = n  # type: ignore[attr-defined]
                return None if n == 1 else pc

            q.filter.return_value.first.side_effect = first
        elif model is IdentityLink:
            q.filter.return_value.first.return_value = link
        else:
            q.filter.return_value.first.return_value = None
        return q

    query._pc_n = 0  # type: ignore[attr-defined]
    db.query.side_effect = query
    resolved, method = resolve_porterchain_user_id(db, "user_abc")
    assert resolved == "pc-from-link"
    assert method == "identity_link"


def test_resolve_unmatched_without_create() -> None:
    db = MagicMock()
    q = MagicMock()
    q.filter.return_value.first.return_value = None
    db.query.return_value = q
    resolved, method = resolve_porterchain_user_id(db, "user_missing", create_missing=False)
    assert resolved is None
    assert method == "none"


def test_backfill_action_never_embeds_secrets() -> None:
    action = BackfillAction(
        table="admin_users",
        row_id="adm-1",
        clerk_user_id="user_abc",
        current_porterchain_user_id=None,
        resolved_porterchain_user_id="pc-1",
        status="would_set",
        detail={"method": "porterchain_users"},
    )
    blob = str(action.to_dict())
    assert "sk_" not in blob
    assert "password" not in blob
