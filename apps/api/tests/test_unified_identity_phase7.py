"""Phase 7 — identity migration CLI: matching, allowlist, dry-run, no elevate."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from porterchain_api.auth.identity_migration.export_loader import (
    load_admin_allowlist,
    load_explicit_map,
    parse_export_document,
)
from porterchain_api.auth.identity_migration.planner import build_migration_plan
from porterchain_api.auth.identity_migration.types import (
    AdminAllowlist,
    ExplicitMapLink,
    SourceExportUser,
)
from porterchain_api.auth.identity_migration.applier import apply_run
from porterchain_api.auth.unified_catalog import AssignableRole


def test_parse_export_ignores_metadata_for_structure_but_records_hint() -> None:
    users = parse_export_document(
        {
            "source_app": "admin",
            "issuer": "https://clerk.example",
            "users": [
                {
                    "id": "user_admin_1",
                    "email_addresses": [
                        {
                            "email_address": "Admin@Porterchain.com",
                            "verification": {"status": "verified"},
                        }
                    ],
                    "public_metadata": {"role": "super_admin"},
                }
            ],
        }
    )
    assert len(users) == 1
    assert users[0].email == "admin@porterchain.com"
    assert users[0].email_verified is True
    assert users[0].metadata_role_hint == "super_admin"


def test_same_email_across_apps_conflicts_without_map() -> None:
    sources = [
        SourceExportUser("customer", "user_c", email="same@x.com", email_verified=True),
        SourceExportUser("admin", "user_a", email="same@x.com", email_verified=True),
    ]
    plan = build_migration_plan(
        label="t1",
        sources=sources,
        explicit_map=[],
        allowlist=AdminAllowlist(),
        db=None,
    )
    assert all(r.status == "conflict" for r in plan.records)
    assert all("same_email_across_legacy_apps" in (r.conflict_reason or "") for r in plan.records)


def test_admin_without_allowlist_conflicts() -> None:
    sources = [SourceExportUser("admin", "user_admin", email="a@x.com", email_verified=True)]
    plan = build_migration_plan(
        label="t2",
        sources=sources,
        explicit_map=[],
        allowlist=AdminAllowlist(),
        db=None,
    )
    assert plan.records[0].status == "conflict"
    assert "allowlist" in (plan.records[0].conflict_reason or "")


def test_admin_allowlist_grants_roles_via_map() -> None:
    sources = [SourceExportUser("admin", "user_admin", email="a@x.com", email_verified=True)]
    allowlist = AdminAllowlist(
        legacy_admin_clerk_user_ids={"user_admin"},
        role_by_clerk_user_id={"user_admin": [AssignableRole.ADMIN.value]},
    )
    plan = build_migration_plan(
        label="t3",
        sources=sources,
        explicit_map=[
            ExplicitMapLink(
                source_app="admin",
                source_clerk_user_id="user_admin",
                target_clerk_user_id="user_platform",
                roles=[AssignableRole.ADMIN.value],
            )
        ],
        allowlist=allowlist,
        db=None,
    )
    assert plan.records[0].status == "matched_map"
    assert AssignableRole.ADMIN.value in plan.records[0].proposed_roles
    assert plan.records[0].detail.get("metadata_role_hint_ignored") is None


def test_metadata_hint_never_becomes_proposed_role() -> None:
    sources = [
        SourceExportUser(
            "customer",
            "user_c",
            email="c@x.com",
            email_verified=True,
            metadata_role_hint="super_admin",
        )
    ]
    plan = build_migration_plan(
        label="t4",
        sources=sources,
        explicit_map=[],
        allowlist=AdminAllowlist(),
        db=None,
    )
    assert plan.records[0].status == "unmatched"
    assert plan.records[0].proposed_roles == [AssignableRole.CUSTOMER.value]
    assert plan.records[0].detail.get("metadata_role_hint_ignored") == "super_admin"
    assert AssignableRole.SUPER_ADMIN.value not in plan.records[0].proposed_roles


def test_invite_role_on_map_rejected_without_allowlist() -> None:
    sources = [SourceExportUser("customer", "user_c", email="c@x.com", email_verified=True)]
    plan = build_migration_plan(
        label="t5",
        sources=sources,
        explicit_map=[
            ExplicitMapLink(
                source_app="customer",
                source_clerk_user_id="user_c",
                roles=[AssignableRole.SUPER_ADMIN.value, AssignableRole.CUSTOMER.value],
            )
        ],
        allowlist=AdminAllowlist(),
        db=None,
    )
    # customer accepted; super_admin rejected — still matched_map with customer only
    assert plan.records[0].status == "matched_map"
    assert plan.records[0].proposed_roles == [AssignableRole.CUSTOMER.value]
    assert "super_admin" in plan.records[0].detail.get("rejected_invite_roles", [])


def test_load_allowlist_and_map(tmp_path: Path) -> None:
    allow = tmp_path / "allow.json"
    allow.write_text(
        json.dumps(
            {
                "legacy_admin_clerk_user_ids": ["user_1"],
                "role_by_clerk_user_id": {"user_1": ["admin"]},
            }
        ),
        encoding="utf-8",
    )
    mapping = tmp_path / "map.json"
    mapping.write_text(
        json.dumps(
            {
                "links": [
                    {
                        "source_app": "admin",
                        "source_clerk_user_id": "user_1",
                        "target_clerk_user_id": "user_new",
                        "roles": ["admin"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    al = load_admin_allowlist(allow)
    assert al.allows_admin_id("user_1")
    links = load_explicit_map(mapping)
    assert links[0].target_clerk_user_id == "user_new"


def test_apply_requires_confirm_token() -> None:
    from unittest.mock import MagicMock

    db = MagicMock()
    # load_run_records will be called — short-circuit by raising before DB if confirm missing
    with pytest.raises(ValueError, match="APPLY"):
        apply_run(db, "run_x", dry_run=False, confirm="nope")


def test_exports_dir_rejects_in_repo(tmp_path: Path) -> None:
    from porterchain_api.auth.identity_migration.export_loader import load_exports_dir

    exports = tmp_path / "exports"
    exports.mkdir()
    (exports / "customer.json").write_text(
        json.dumps({"source_app": "customer", "users": [{"id": "user_1"}]}),
        encoding="utf-8",
    )
    # Treat tmp_path parent as repo containing exports → should fail
    with pytest.raises(ValueError, match="outside the repository"):
        load_exports_dir(exports, repo_root=tmp_path)
