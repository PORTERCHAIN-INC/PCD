"""Users directory — DB-first visibility; Clerk enriches identity for non-staff."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from porterchain_api.admin_engine.settings_service import (
    AdminSettingsService,
    _merge_clerk_directory,
    _staff_identity_status,
    _staff_invite_status,
    _staff_status_label,
)
from porterchain_api.schemas_admin import PlatformUserItem


def _item(
    *,
    email: str,
    clerk_user_id: str = "user_real",
    user_type: str = "customer",
    identity_status: str = "registered",
    clerk_linked: bool = True,
    invite_status: str = "accepted",
) -> PlatformUserItem:
    return PlatformUserItem(
        id="cust-1",
        user_type=user_type,
        email=email,
        name="Real Customer",
        role="customer" if user_type == "customer" else "merchant_ops",
        status="active",
        access_status="authorized",
        invite_status=invite_status,
        identity_status=identity_status,
        status_label="ok",
        clerk_linked=clerk_linked,
        clerk_user_id=clerk_user_id,
        created_at=datetime.now(UTC),
    )


def test_merge_rejects_staff_user_type() -> None:
    with pytest.raises(ValueError, match="staff_directory_is_staff_idp_not_clerk"):
        _merge_clerk_directory(
            [],
            settings=MagicMock(),
            user_type="staff",
            limit=50,
            search=None,
        )


def test_staff_status_helpers_use_staff_idp_subjects() -> None:
    assert _staff_invite_status("staff:abc") == "accepted"
    assert _staff_identity_status("staff:abc") == "registered"
    assert _staff_invite_status("pending:ops@example.com") == "invite_pending"
    assert _staff_identity_status(None) == "not_registered"
    assert _staff_invite_status("user_legacy") == "accepted"
    assert _staff_identity_status("user_legacy") == "registered"
    label = _staff_status_label("authorized", "accepted", "registered")
    assert "Clerk" not in label
    assert "Staff IdP" in label
    legacy = _staff_status_label(
        "authorized", "accepted", "registered", subject="user_legacy"
    )
    assert "Legacy id" in legacy
    assert "Clerk registered" not in legacy


def test_list_platform_users_staff_skips_clerk_merge(db, settings) -> None:
    """Staff directory must not call Clerk — even when Clerk is empty/down."""
    with patch(
        "porterchain_api.admin_engine.settings_service.fetch_clerk_snapshots",
        side_effect=AssertionError("staff must not fetch Clerk"),
    ):
        resp = AdminSettingsService().list_platform_users(db, settings, "staff", limit=50)
    assert resp.clerk_synced is False
    assert resp.clerk_total is None
    assert isinstance(resp.items, list)
    for item in resp.items:
        assert item.user_type == "staff"
        assert item.clerk_linked is False
        assert item.clerk_user_id is None
        assert "Clerk" not in item.status_label


def test_merge_keeps_db_rows_missing_from_clerk() -> None:
    snap = MagicMock(
        clerk_user_id="user_real",
        first_name="Real",
        last_name="",
        clerk_status="active",
        email_verified=True,
        password_set=False,
        last_sign_in_at=None,
        created_at=datetime.now(UTC),
    )
    with patch(
        "porterchain_api.admin_engine.settings_service.fetch_clerk_snapshots",
        return_value={"real@example.com": snap},
    ):
        merged, synced, total = _merge_clerk_directory(
            [
                _item(email="real@example.com", clerk_user_id="user_real"),
                _item(email="ghost@example.com", clerk_user_id="clerk_fake_xyz"),
            ],
            settings=MagicMock(),
            user_type="customer",
            limit=50,
            search=None,
        )
    assert synced is True
    assert total == 1
    by_email = {i.email.lower(): i for i in merged}
    assert set(by_email) == {"real@example.com", "ghost@example.com"}
    assert by_email["real@example.com"].clerk_linked is True
    assert by_email["ghost@example.com"].clerk_linked is False
    assert by_email["ghost@example.com"].identity_status == "not_registered"
    assert "Not in Clerk" in by_email["ghost@example.com"].status_label


def test_merge_keeps_db_rows_when_clerk_errors() -> None:
    with patch(
        "porterchain_api.admin_engine.settings_service.fetch_clerk_snapshots",
        side_effect=RuntimeError("clerk down"),
    ):
        merged, synced, total = _merge_clerk_directory(
            [_item(email="anyone@example.com")],
            settings=MagicMock(),
            user_type="customer",
            limit=50,
            search=None,
        )
    assert synced is False
    assert total == 0
    assert len(merged) == 1
    assert merged[0].email == "anyone@example.com"
    assert merged[0].identity_status == "not_registered"


def test_merge_empty_clerk_still_shows_db_rows() -> None:
    with patch(
        "porterchain_api.admin_engine.settings_service.fetch_clerk_snapshots",
        return_value={},
    ):
        merged, synced, total = _merge_clerk_directory(
            [_item(email="local-fixture@example.com")],
            settings=MagicMock(),
            user_type="customer",
            limit=50,
            search=None,
        )
    assert synced is True
    assert total == 0
    assert len(merged) == 1
    assert merged[0].email == "local-fixture@example.com"
    assert "Not in Clerk" in merged[0].status_label


def test_merge_clerk_does_not_inject_unprovisioned_on_customer_tab() -> None:
    snap = MagicMock(
        clerk_user_id="user_staff",
        first_name="Founder",
        last_name="",
        clerk_status="active",
        email_verified=True,
        password_set=False,
        last_sign_in_at=None,
        created_at=datetime.now(UTC),
    )
    with patch(
        "porterchain_api.admin_engine.settings_service.fetch_clerk_snapshots",
        return_value={
            "real@example.com": snap,
            "porterchaininc@gmail.com": snap,
        },
    ):
        merged, synced, total = _merge_clerk_directory(
            [_item(email="real@example.com", clerk_user_id="user_staff")],
            settings=MagicMock(),
            user_type="customer",
            limit=50,
            search=None,
            include_unprovisioned=False,
        )
    assert synced is True
    assert total == 2
    emails = {i.email.lower() for i in merged}
    assert emails == {"real@example.com"}
    assert "porterchaininc@gmail.com" not in emails


def test_merchant_keeps_unlinked_seats_and_injects_unprovisioned() -> None:
    snap = MagicMock(
        clerk_user_id="user_live",
        first_name="Live",
        last_name="Seat",
        clerk_status="active",
        email_verified=True,
        password_set=True,
        last_sign_in_at=None,
        created_at=datetime.now(UTC),
        banned=False,
    )
    orphan = MagicMock(
        clerk_user_id="user_orphan",
        first_name="Orphan",
        last_name="",
        clerk_status="active",
        email_verified=True,
        password_set=False,
        last_sign_in_at=None,
        created_at=datetime.now(UTC),
        banned=False,
    )
    with patch(
        "porterchain_api.admin_engine.settings_service.fetch_clerk_snapshots",
        return_value={
            "live@example.com": snap,
            "orphan@example.com": orphan,
        },
    ):
        merged, synced, total = _merge_clerk_directory(
            [
                _item(
                    email="live@example.com",
                    clerk_user_id="user_live",
                    user_type="merchant",
                ),
                _item(
                    email="reserved@example.com",
                    clerk_user_id="pending:abc",
                    user_type="merchant",
                    identity_status="invite_pending",
                    clerk_linked=False,
                    invite_status="invite_pending",
                ),
            ],
            settings=MagicMock(),
            user_type="merchant",
            limit=50,
            search=None,
            include_unprovisioned=True,
            keep_unlinked=True,
        )
    assert synced is True
    assert total == 2
    by_email = {i.email.lower(): i for i in merged}
    assert set(by_email) == {"live@example.com", "reserved@example.com", "orphan@example.com"}
    assert by_email["live@example.com"].clerk_linked is True
    assert by_email["reserved@example.com"].identity_status == "invite_pending"
    assert by_email["reserved@example.com"].clerk_linked is False
    assert by_email["orphan@example.com"].provisioned is False
    assert by_email["orphan@example.com"].detail_href == "/merchants"


def test_merchant_keep_unlinked_when_clerk_errors() -> None:
    with patch(
        "porterchain_api.admin_engine.settings_service.fetch_clerk_snapshots",
        side_effect=RuntimeError("clerk down"),
    ):
        merged, synced, total = _merge_clerk_directory(
            [
                _item(
                    email="seat@example.com",
                    clerk_user_id="pending:x",
                    user_type="merchant",
                    clerk_linked=False,
                    identity_status="invite_pending",
                    invite_status="invite_pending",
                )
            ],
            settings=MagicMock(),
            user_type="merchant",
            limit=50,
            search=None,
            include_unprovisioned=True,
            keep_unlinked=True,
        )
    assert synced is False
    assert total == 0
    assert len(merged) == 1
    assert merged[0].email == "seat@example.com"
    assert merged[0].identity_status == "invite_pending"


def test_merchant_same_email_keeps_one_row_per_seat() -> None:
    """Multi-org seats sharing an email must not collapse to a single directory row."""
    snap = MagicMock(
        clerk_user_id="user_shared",
        first_name="Shared",
        last_name="Ops",
        clerk_status="active",
        email_verified=True,
        password_set=True,
        last_sign_in_at=None,
        created_at=datetime.now(UTC),
        banned=False,
    )
    seat_a = _item(
        email="ops@example.com",
        clerk_user_id="user_shared",
        user_type="merchant",
    ).model_copy(update={"id": "mu-a", "organization": "Acme Logistics"})
    seat_b = _item(
        email="ops@example.com",
        clerk_user_id="user_shared",
        user_type="merchant",
    ).model_copy(update={"id": "mu-b", "organization": "Beta Freight"})
    with patch(
        "porterchain_api.admin_engine.settings_service.fetch_clerk_snapshots",
        return_value={"ops@example.com": snap},
    ):
        merged, synced, total = _merge_clerk_directory(
            [seat_a, seat_b],
            settings=MagicMock(),
            user_type="merchant",
            limit=50,
            search=None,
            include_unprovisioned=False,
        )
    assert synced is True
    assert total == 1
    assert len(merged) == 2
    assert {i.id for i in merged} == {"mu-a", "mu-b"}
    assert {i.organization for i in merged} == {"Acme Logistics", "Beta Freight"}
    assert all(i.clerk_linked for i in merged)


def test_list_platform_users_customer_shows_db_when_clerk_empty(db, settings) -> None:
    with patch(
        "porterchain_api.admin_engine.settings_service.fetch_clerk_snapshots",
        return_value={},
    ):
        resp = AdminSettingsService().list_platform_users(db, settings, "customer", limit=50)
    assert resp.clerk_synced is True
    # May be empty DB in fresh fixture — must not raise / fail-closed to [].
    assert isinstance(resp.items, list)
