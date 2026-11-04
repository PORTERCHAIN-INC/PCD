"""Porterchain Inc. GST/HST registration 743402620 RT0001, effective 2026-09-28.

Owner-confirmed (2026-10-29). Inserted only when tax_registrations is empty, so an
admin-entered history (Settings > Tax registration) is never overwritten.
Downgrade removes only this row.
"""

import uuid

import sqlalchemy as sa
from alembic import op

revision = "hst743reg01"
down_revision = "bt84opsrules01"
branch_labels = None
depends_on = None

NUMBER = "743402620 RT0001"
LEGAL_NAME = "Porterchain Inc."
NOTE = "owner-confirmed registration (migration hst743reg01)"


def upgrade() -> None:
    bind = op.get_bind()
    if bind.execute(sa.text("SELECT COUNT(*) FROM tax_registrations")).scalar():
        return
    bind.execute(
        sa.text(
            "INSERT INTO tax_registrations (id, gst_hst_number, legal_name, effective_from, note) "
            "VALUES (:id, :n, :name, DATE '2026-09-28', :note)"
        ),
        {"id": str(uuid.uuid4()), "n": NUMBER, "name": LEGAL_NAME, "note": NOTE},
    )


def downgrade() -> None:
    op.get_bind().execute(sa.text("DELETE FROM tax_registrations WHERE note = :note"), {"note": NOTE})
