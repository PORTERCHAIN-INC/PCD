"""Chain of custody on existing packages: status check + partner barcode cross-reference.

Revision ID: dm3custody0003
Revises: dm2fkorphan0002

* ``ck_packages_status_known``: ``packages.status`` may only hold the six custody states
  of ``domain.states.PackageState``. Added ``NOT VALID`` (enforced for every new write at
  once); existing rows with an unknown status are printed and copied into
  ``fk_orphan_quarantine`` (column 'status', action='reported', nothing changed), and the
  constraint is VALIDATEd only when there are none. Transitions themselves are enforced in
  ``merchant_engine.package_state.set_package_status`` (single writer, audit in order_events).
* ``package_external_identifiers``: partner/marketplace barcodes -> one package
  (unique per source + normalized value), used by driver scan lookup.

No new tracking number: packages already carry the signed opaque ``PC1`` label id
(reporting/qr_codec.py) plus ``tracking_suffix``; see docs/architecture/NEW_ADDITION_GATE.md.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "dm3custody0003"
down_revision = "dm2fkorphan0002"
branch_labels = None
depends_on = None

STATES = ("manifested", "picked_up", "loaded", "out_for_delivery", "delivered", "missing_at_pickup")
CHECK = "status IN (" + ",".join(f"'{s}'" for s in STATES) + ")"


def upgrade() -> None:
    bind = op.get_bind()
    bad = bind.execute(
        sa.text(
            "INSERT INTO fk_orphan_quarantine (table_name, column_name, row_pk, bad_value, row_data, action) "
            f"SELECT 'packages', 'status', p.id, coalesce(p.status, 'NULL'), to_jsonb(p), 'reported' "
            f"FROM packages p WHERE p.status IS NULL OR NOT ({CHECK.replace('status', 'p.status')})"
        )
    ).rowcount
    op.execute(f"ALTER TABLE packages ADD CONSTRAINT ck_packages_status_known CHECK ({CHECK}) NOT VALID")
    if bad:
        print(
            f"[dm3custody0003] {bad} package(s) have an unknown status; constraint left NOT VALID. "
            "Fix them (see fk_orphan_quarantine, action='reported') then run: "
            "ALTER TABLE packages VALIDATE CONSTRAINT ck_packages_status_known"
        )
    else:
        op.execute("ALTER TABLE packages VALIDATE CONSTRAINT ck_packages_status_known")

    op.create_table(
        "package_external_identifiers",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("package_id", sa.String(36), sa.ForeignKey("packages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("order_id", sa.String(36), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("value", sa.String(128), nullable=False),
        sa.Column("value_normalized", sa.String(128), nullable=False),
        sa.Column("created_by", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("source", "value_normalized", name="uq_package_external_identifiers_source_value"),
    )
    for col in ("package_id", "order_id", "value_normalized"):
        op.create_index(f"ix_package_external_identifiers_{col}", "package_external_identifiers", [col])


def downgrade() -> None:
    for col in ("value_normalized", "order_id", "package_id"):
        op.drop_index(f"ix_package_external_identifiers_{col}", table_name="package_external_identifiers")
    op.drop_table("package_external_identifiers")
    op.execute("ALTER TABLE packages DROP CONSTRAINT ck_packages_status_known")
    op.execute(
        "DELETE FROM fk_orphan_quarantine WHERE table_name = 'packages' AND column_name = 'status' "
        "AND action = 'reported'"
    )
