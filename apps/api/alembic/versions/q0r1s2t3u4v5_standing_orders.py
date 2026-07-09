"""Standing orders for recurring merchant bookings (§8.1.11)."""

from alembic import op
import sqlalchemy as sa

revision = "q0r1s2t3u4v5"
down_revision = "p9q0r1s2t3u4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "standing_orders",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("merchant_id", sa.String(length=36), nullable=False),
        sa.Column("booking_template_id", sa.String(length=36), nullable=False),
        sa.Column("recurrence_rule", sa.String(length=64), nullable=False, server_default="weekly"),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_order_id", sa.String(length=36), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["merchant_id"], ["merchants.id"]),
        sa.ForeignKeyConstraint(["booking_template_id"], ["merchant_booking_templates.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_standing_orders_merchant_id", "standing_orders", ["merchant_id"])
    op.create_index("ix_standing_orders_booking_template_id", "standing_orders", ["booking_template_id"])
    op.create_index("ix_standing_orders_next_run_at", "standing_orders", ["next_run_at"])
    op.create_index("ix_standing_orders_is_active", "standing_orders", ["is_active"])


def downgrade() -> None:
    op.drop_index("ix_standing_orders_is_active", table_name="standing_orders")
    op.drop_index("ix_standing_orders_next_run_at", table_name="standing_orders")
    op.drop_index("ix_standing_orders_booking_template_id", table_name="standing_orders")
    op.drop_index("ix_standing_orders_merchant_id", table_name="standing_orders")
    op.drop_table("standing_orders")
