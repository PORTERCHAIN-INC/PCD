"""GST/HST registration history (append-only) — single source for whether we charge tax.

One row per change. The registration in force on a date is the latest row whose
``effective_from`` is on or before that date; a row with no number means "not
registered" from that date. Rows are never updated or deleted by the app.

Data: a valid number already stored in ``system_config.settings_finance.gst_hst_number``
is copied in as effective from 1970-01-01 so a system that was already registered keeps
charging tax. With no stored number the system is a non-registrant (no GST/HST).

Revision ID: tr6taxreg0006
Revises: cn5creditnotes0005
"""

from __future__ import annotations

import json
import re
import uuid

import sqlalchemy as sa

from alembic import op

revision = "tr6taxreg0006"
down_revision = "cn5creditnotes0005"
branch_labels = None
depends_on = None

_BN = re.compile(r"^(\d{9})RT(\d{4})$")


def upgrade() -> None:
    op.create_table(
        "tax_registrations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("gst_hst_number", sa.String(20), nullable=True),
        sa.Column("legal_name", sa.String(255), nullable=True),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_tax_registrations_effective", "tax_registrations", ["effective_from", "created_at"])

    bind = op.get_bind()
    row = bind.execute(sa.text("SELECT value FROM system_config WHERE key = 'settings_finance'")).first()
    value = row[0] if row else None
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError:
            value = None
    raw = str((value or {}).get("gst_hst_number") or "") if isinstance(value, dict) else ""
    m = _BN.match(re.sub(r"[\s-]", "", raw.upper()))
    if m:
        bind.execute(
            sa.text(
                "INSERT INTO tax_registrations (id, gst_hst_number, legal_name, effective_from, note) "
                "VALUES (:id, :n, NULL, DATE '1970-01-01', 'migrated from settings_finance')"
            ),
            {"id": str(uuid.uuid4()), "n": f"{m.group(1)} RT{m.group(2)}"},
        )


def downgrade() -> None:
    op.drop_index("ix_tax_registrations_effective", table_name="tax_registrations")
    op.drop_table("tax_registrations")
