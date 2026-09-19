"""Standing-order last_error + invoice last_reminded_at."""

from alembic import op
import sqlalchemy as sa

revision = "m5n6o7p8q9r0"
down_revision = "l4m5n6o7p8q9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("standing_orders", sa.Column("last_error", sa.Text(), nullable=True))
    op.add_column(
        "invoices",
        sa.Column("last_reminded_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("invoices", "last_reminded_at")
    op.drop_column("standing_orders", "last_error")
