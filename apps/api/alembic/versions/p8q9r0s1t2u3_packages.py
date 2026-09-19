"""packages table — scannable parcel identity (spine 1).

Backfill runs via PackageService.sync_from_order (book / amend / label print).
JSON dual-write cutover: 2026-09-26 — see package_service.PACKAGES_JSON_CUTOVER.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "p8q9r0s1t2u3"
down_revision = "o7p8q9r0s1t2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "packages",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "order_id",
            sa.String(length=36),
            sa.ForeignKey("orders.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("stop_key", sa.Text(), nullable=True),
        sa.Column("parcel_index", sa.Integer(), nullable=False),
        sa.Column("total_parcels", sa.Integer(), nullable=False),
        sa.Column("tracking_suffix", sa.Text(), nullable=False),
        sa.Column("weight_kg", sa.Numeric(10, 3), nullable=True),
        sa.Column("dimensions", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="manifested"),
        sa.Column("route_hint", sa.Text(), nullable=True),
        sa.Column("stop_sequence", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("order_id", "parcel_index", name="uq_packages_order_parcel_index"),
        sa.CheckConstraint("parcel_index >= 1", name="ck_packages_parcel_index_positive"),
        sa.CheckConstraint(
            "parcel_index <= total_parcels",
            name="ck_packages_parcel_index_le_total",
        ),
    )
    op.create_index("ix_packages_order_id", "packages", ["order_id"])
    op.create_index("ix_packages_tracking_suffix", "packages", ["tracking_suffix"], unique=True)
    op.create_index("ix_packages_status", "packages", ["status"])


def downgrade() -> None:
    op.drop_index("ix_packages_status", table_name="packages")
    op.drop_index("ix_packages_tracking_suffix", table_name="packages")
    op.drop_index("ix_packages_order_id", table_name="packages")
    op.drop_table("packages")
