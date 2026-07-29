"""Users directory = live Clerk ∩ provisioned personas only."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from porterchain_api.admin_engine.settings_service import _merge_clerk_directory
from porterchain_api.schemas_admin import PlatformUserItem


def _item(*, email: str, clerk_user_id: str = "user_real", user_type: str = "customer") -> PlatformUserItem:
    return PlatformUserItem(
        id="cust-1",
        user_type=user_type,
        email=email,
        name="Real Customer",
        role="customer",
        status="active",
        access_status="authorized",
        invite_status="accepted",
        identity_status="registered",
        status_label="ok",
        clerk_linked=True,
        clerk_user_id=clerk_user_id,
        created_at=datetime.now(UTC),
    )


def test_merge_drops_db_only_ghosts_not_in_clerk() -> None:
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
            include_unprovisioned=False,
        )
    assert synced is True
    assert total == 1
    assert {i.email.lower() for i in merged} == {"real@example.com"}


def test_merge_fail_closed_when_clerk_errors() -> None:
    with patch(
        "porterchain_api.admin_engine.settings_service.fetch_clerk_snapshots",
        side_effect=RuntimeError("clerk down"),
    ):
        merged, synced, total = _merge_clerk_directory(
            [_item(email="anyone@example.com")],
            settings=MagicMock(),
            user_type="staff",
            limit=50,
            search=None,
            include_unprovisioned=True,
        )
    assert synced is False
    assert total == 0
    assert merged == []


def test_merge_empty_clerk_shows_nothing() -> None:
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
    assert merged == []


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


def test_merge_clerk_injects_unprovisioned_on_staff_tab() -> None:
    snap = MagicMock(
        clerk_user_id="user_new",
        first_name="New",
        last_name="Staff",
        clerk_status="active",
        email_verified=True,
        password_set=True,
        last_sign_in_at=None,
        created_at=datetime.now(UTC),
    )
    with patch(
        "porterchain_api.admin_engine.settings_service.fetch_clerk_snapshots",
        return_value={"new@example.com": snap},
    ):
        merged, synced, _total = _merge_clerk_directory(
            [],
            settings=MagicMock(),
            user_type="staff",
            limit=50,
            search=None,
            include_unprovisioned=True,
        )
    assert synced is True
    assert len(merged) == 1
    assert merged[0].email == "new@example.com"
    assert merged[0].provisioned is False
    assert merged[0].access_status == "not_authorized"
