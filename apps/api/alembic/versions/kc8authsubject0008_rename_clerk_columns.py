"""Rename Clerk-era identity columns to provider-neutral names; remap subjects.

``clerk_user_id`` -> ``auth_subject`` (Keycloak ``sub``) on every persona table, plus the
invitation / org / migration-record columns. Index and constraint names follow.

Backfill: when ``PCD_SUBJECT_REMAP_CSV`` points at the ``subject-remap.csv`` written by
``infrastructure/keycloak/migrate_clerk_users.py`` (columns ``legacy_subject,keycloak_sub,email``),
every ``auth_subject`` equal to a legacy subject is rewritten to the Keycloak sub. Without the
variable the rename runs and no subjects change (fresh / test databases).

Revision ID: kc8authsubject0008
Revises: kc7dropclerkwh0007
"""

from __future__ import annotations

import csv
import os

import sqlalchemy as sa

from alembic import op

revision = "kc8authsubject0008"
down_revision = "kc7dropclerkwh0007"
branch_labels = None
depends_on = None

SUBJECT_TABLES = (
    "admin_users",
    "customers",
    "drivers",
    "identity_links",
    "merchant_users",
    "porterchain_users",
    "user_invitations",
)
# (table, old column, new column)
OTHER_COLUMNS = (
    ("user_invitations", "clerk_invitation_id", "external_invitation_id"),
    ("merchants", "clerk_org_id", "external_org_id"),
    ("identity_migration_records", "source_clerk_user_id", "source_subject"),
    ("identity_migration_records", "target_clerk_user_id", "target_subject"),
)
INDEXES = tuple((f"ix_{t}_clerk_user_id", f"ix_{t}_auth_subject") for t in SUBJECT_TABLES) + (
    ("ix_merchants_clerk_org_id", "ix_merchants_external_org_id"),
)
CONSTRAINTS = (("merchant_users", "uq_merchant_users_clerk_merchant", "uq_merchant_users_subject_merchant"),)


def _load_remap(path: str) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    with open(path, newline="") as fh:
        for row in csv.DictReader(fh):
            old = (row.get("legacy_subject") or "").strip()
            new = (row.get("keycloak_sub") or "").strip()
            if old and new and old != new:
                pairs.append((old, new))
    return pairs


def _rename_all(direction: int) -> None:
    for table in SUBJECT_TABLES:
        old, new = ("clerk_user_id", "auth_subject")[::direction]
        op.alter_column(table, old, new_column_name=new)
    for table, old, new in OTHER_COLUMNS:
        a, b = (old, new)[::direction]
        op.alter_column(table, a, new_column_name=b)
    for old, new in INDEXES:
        a, b = (old, new)[::direction]
        op.execute(f'ALTER INDEX IF EXISTS "{a}" RENAME TO "{b}"')
    for table, old, new in CONSTRAINTS:
        a, b = (old, new)[::direction]
        op.execute(f'ALTER TABLE "{table}" RENAME CONSTRAINT "{a}" TO "{b}"')


def upgrade() -> None:
    _rename_all(1)
    path = os.environ.get("PCD_SUBJECT_REMAP_CSV", "").strip()
    if not path:
        return
    pairs = _load_remap(path)
    bind = op.get_bind()
    for table in SUBJECT_TABLES:
        stmt = sa.text(f'UPDATE "{table}" SET auth_subject = :new WHERE auth_subject = :old')
        for old, new in pairs:
            bind.execute(stmt, {"old": old, "new": new})
    for col in ("source_subject", "target_subject"):
        stmt = sa.text(f'UPDATE identity_migration_records SET {col} = :new WHERE {col} = :old')
        for old, new in pairs:
            bind.execute(stmt, {"old": old, "new": new})


def downgrade() -> None:
    # Subject remap is not reversed (Keycloak subs stay); only names roll back.
    _rename_all(-1)
