"""Phase 2 unified identity — additive schema only (no drops of legacy columns).

Revision ID: w6x7y8z9a0b1
Revises: v5w6x7y8z9a0
Create Date: 2026-07-28

Adds:
- porterchain_users.onboarding_status, default_workspace
- identity_links provider/issuer/subject/legacy flags (+ partial unique)
- user_emails, user_role_assignments, user_permission_overrides
- access_audit_logs, identity_migration_runs, identity_migration_records

Does not change runtime auth paths or drop clerk_user_id columns.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "w6x7y8z9a0b1"
down_revision: Union[str, None] = "v5w6x7y8z9a0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "porterchain_users",
        sa.Column("onboarding_status", sa.String(length=32), nullable=False, server_default="not_started"),
    )
    op.add_column(
        "porterchain_users",
        sa.Column("default_workspace", sa.String(length=64), nullable=True),
    )
    op.create_index(
        op.f("ix_porterchain_users_onboarding_status"),
        "porterchain_users",
        ["onboarding_status"],
        unique=False,
    )

    op.add_column("identity_links", sa.Column("provider", sa.String(length=32), nullable=True))
    op.add_column("identity_links", sa.Column("issuer", sa.String(length=512), nullable=True))
    op.add_column("identity_links", sa.Column("subject", sa.String(length=128), nullable=True))
    op.add_column(
        "identity_links",
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.add_column(
        "identity_links",
        sa.Column("is_legacy", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column("identity_links", sa.Column("linked_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("identity_links", sa.Column("deactivated_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f("ix_identity_links_provider"), "identity_links", ["provider"], unique=False)
    op.create_index(op.f("ix_identity_links_issuer"), "identity_links", ["issuer"], unique=False)
    op.create_index(op.f("ix_identity_links_subject"), "identity_links", ["subject"], unique=False)
    op.create_index(
        "uq_identity_links_provider_issuer_subject",
        "identity_links",
        ["provider", "issuer", "subject"],
        unique=True,
        postgresql_where=sa.text("subject IS NOT NULL"),
    )

    op.create_table(
        "user_emails",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("normalized_email", sa.String(length=320), nullable=False),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("source", sa.String(length=64), nullable=False, server_default="clerk"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["porterchain_users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "normalized_email", name="uq_user_emails_user_email"),
    )
    op.create_index("ix_user_emails_normalized_email", "user_emails", ["normalized_email"], unique=False)
    op.create_index(op.f("ix_user_emails_user_id"), "user_emails", ["user_id"], unique=False)

    op.create_table(
        "user_role_assignments",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("role_key", sa.String(length=64), nullable=False),
        sa.Column("scope_type", sa.String(length=32), nullable=False, server_default="global"),
        sa.Column("scope_id", sa.String(length=36), nullable=False, server_default=""),
        sa.Column("assigned_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["porterchain_users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "role_key",
            "scope_type",
            "scope_id",
            name="uq_user_role_assignments_user_role_scope",
        ),
    )
    op.create_index(op.f("ix_user_role_assignments_user_id"), "user_role_assignments", ["user_id"], unique=False)
    op.create_index("ix_user_role_assignments_role_key", "user_role_assignments", ["role_key"], unique=False)
    op.create_index(
        "ix_user_role_assignments_scope",
        "user_role_assignments",
        ["scope_type", "scope_id"],
        unique=False,
    )

    op.create_table(
        "user_permission_overrides",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("permission_key", sa.String(length=128), nullable=False),
        sa.Column("effect", sa.String(length=16), nullable=False),
        sa.Column("reason", sa.String(length=512), nullable=True),
        sa.Column("scope_type", sa.String(length=32), nullable=False, server_default="global"),
        sa.Column("scope_id", sa.String(length=36), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["porterchain_users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_permission_overrides_user", "user_permission_overrides", ["user_id"], unique=False)
    op.create_index(
        "ix_user_permission_overrides_permission",
        "user_permission_overrides",
        ["permission_key"],
        unique=False,
    )
    op.create_index(op.f("ix_user_permission_overrides_user_id"), "user_permission_overrides", ["user_id"], unique=False)

    op.create_table(
        "access_audit_logs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("actor_user_id", sa.String(length=36), nullable=True),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("resource_type", sa.String(length=64), nullable=True),
        sa.Column("resource_id", sa.String(length=64), nullable=True),
        sa.Column("outcome", sa.String(length=32), nullable=False),
        sa.Column("detail", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_access_audit_logs_actor", "access_audit_logs", ["actor_user_id"], unique=False)
    op.create_index("ix_access_audit_logs_action", "access_audit_logs", ["action"], unique=False)
    op.create_index("ix_access_audit_logs_created", "access_audit_logs", ["created_at"], unique=False)

    op.create_table(
        "identity_migration_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="planned"),
        sa.Column("dry_run", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("source_summary", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("counts", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_identity_migration_runs_status"), "identity_migration_runs", ["status"], unique=False)

    op.create_table(
        "identity_migration_records",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("source_app", sa.String(length=32), nullable=False),
        sa.Column("source_issuer", sa.String(length=512), nullable=True),
        sa.Column("source_clerk_user_id", sa.String(length=128), nullable=False),
        sa.Column("internal_user_id", sa.String(length=36), nullable=True),
        sa.Column("target_clerk_user_id", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("conflict_reason", sa.Text(), nullable=True),
        sa.Column("proposed_roles", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("detail", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["identity_migration_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "run_id",
            "source_app",
            "source_clerk_user_id",
            name="uq_identity_migration_records_run_source",
        ),
    )
    op.create_index("ix_identity_migration_records_run", "identity_migration_records", ["run_id"], unique=False)
    op.create_index(
        "ix_identity_migration_records_source",
        "identity_migration_records",
        ["source_app", "source_clerk_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_identity_migration_records_internal",
        "identity_migration_records",
        ["internal_user_id"],
        unique=False,
    )
    op.create_index(op.f("ix_identity_migration_records_run_id"), "identity_migration_records", ["run_id"], unique=False)
    op.create_index(op.f("ix_identity_migration_records_status"), "identity_migration_records", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_identity_migration_records_status"), table_name="identity_migration_records")
    op.drop_index(op.f("ix_identity_migration_records_run_id"), table_name="identity_migration_records")
    op.drop_index("ix_identity_migration_records_internal", table_name="identity_migration_records")
    op.drop_index("ix_identity_migration_records_source", table_name="identity_migration_records")
    op.drop_index("ix_identity_migration_records_run", table_name="identity_migration_records")
    op.drop_table("identity_migration_records")

    op.drop_index(op.f("ix_identity_migration_runs_status"), table_name="identity_migration_runs")
    op.drop_table("identity_migration_runs")

    op.drop_index("ix_access_audit_logs_created", table_name="access_audit_logs")
    op.drop_index("ix_access_audit_logs_action", table_name="access_audit_logs")
    op.drop_index("ix_access_audit_logs_actor", table_name="access_audit_logs")
    op.drop_table("access_audit_logs")

    op.drop_index(op.f("ix_user_permission_overrides_user_id"), table_name="user_permission_overrides")
    op.drop_index("ix_user_permission_overrides_permission", table_name="user_permission_overrides")
    op.drop_index("ix_user_permission_overrides_user", table_name="user_permission_overrides")
    op.drop_table("user_permission_overrides")

    op.drop_index("ix_user_role_assignments_scope", table_name="user_role_assignments")
    op.drop_index("ix_user_role_assignments_role_key", table_name="user_role_assignments")
    op.drop_index(op.f("ix_user_role_assignments_user_id"), table_name="user_role_assignments")
    op.drop_table("user_role_assignments")

    op.drop_index(op.f("ix_user_emails_user_id"), table_name="user_emails")
    op.drop_index("ix_user_emails_normalized_email", table_name="user_emails")
    op.drop_table("user_emails")

    op.drop_index("uq_identity_links_provider_issuer_subject", table_name="identity_links")
    op.drop_index(op.f("ix_identity_links_subject"), table_name="identity_links")
    op.drop_index(op.f("ix_identity_links_issuer"), table_name="identity_links")
    op.drop_index(op.f("ix_identity_links_provider"), table_name="identity_links")
    op.drop_column("identity_links", "deactivated_at")
    op.drop_column("identity_links", "linked_at")
    op.drop_column("identity_links", "is_legacy")
    op.drop_column("identity_links", "is_current")
    op.drop_column("identity_links", "subject")
    op.drop_column("identity_links", "issuer")
    op.drop_column("identity_links", "provider")

    op.drop_index(op.f("ix_porterchain_users_onboarding_status"), table_name="porterchain_users")
    op.drop_column("porterchain_users", "default_workspace")
    op.drop_column("porterchain_users", "onboarding_status")
