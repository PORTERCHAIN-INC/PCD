"""GST/HST credit notes for invoice adjustments (void, line credit, partial credit).

Adds the prescribed credit-note fields (SOR/91-44 s.3) to ``credit_notes`` and a
running ``invoices.credited_cents`` that ``invoice_status`` / ``outstanding_cents``
net against. Existing rows keep working: new columns are nullable or defaulted, and
legacy notes have no number. Downgrade drops exactly what was added.

Revision ID: cn5creditnotes0005
Revises: dm4nocod0004
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "cn5creditnotes0005"
down_revision = "dm4nocod0004"
branch_labels = None
depends_on = None

_COLS = (
    ("credit_note_number", sa.String(32), {}),
    ("kind", sa.String(16), {}),
    ("reason_code", sa.String(32), {}),
    ("internal_note", sa.Text(), {}),
    ("customer_reason", sa.Text(), {}),
    ("subtotal_cents", sa.Integer(), {}),
    ("tax_cents", sa.Integer(), {}),
    ("tax_province", sa.String(8), {}),
    ("currency", sa.String(8), {}),
    ("lines_json", sa.JSON(), {}),
    ("original_invoice_number", sa.String(64), {}),
    ("original_invoice_date", sa.DateTime(timezone=True), {}),
    ("customer_id", sa.String(36), {}),
    ("recipient_name", sa.String(255), {}),
    ("issued_by", sa.String(64), {}),
    ("approved_by", sa.String(64), {}),
    ("issued_at", sa.DateTime(timezone=True), {}),
    ("settlement", sa.String(32), {}),
    ("settlement_cents", sa.Integer(), {}),
    ("settlement_ref", sa.String(128), {}),
)


def upgrade() -> None:
    for name, type_, kw in _COLS:
        op.add_column("credit_notes", sa.Column(name, type_, nullable=True, **kw))
    op.create_index("uq_credit_notes_number", "credit_notes", ["credit_note_number"], unique=True)
    op.add_column(
        "invoices",
        sa.Column("credited_cents", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("invoices", "credited_cents")
    op.drop_index("uq_credit_notes_number", table_name="credit_notes")
    for name, _t, _k in reversed(_COLS):
        op.drop_column("credit_notes", name)
