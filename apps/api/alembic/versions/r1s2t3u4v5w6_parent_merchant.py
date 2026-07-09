"""Parent merchant hierarchy for enterprise orgs (§11.2.3)."""

from alembic import op
import sqlalchemy as sa

revision = "r1s2t3u4v5w6"
down_revision = "q0r1s2t3u4v5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("merchants", sa.Column("parent_merchant_id", sa.String(length=36), nullable=True))
    op.create_foreign_key(
        "fk_merchants_parent_merchant_id",
        "merchants",
        "merchants",
        ["parent_merchant_id"],
        ["id"],
    )
    op.create_index("ix_merchants_parent_merchant_id", "merchants", ["parent_merchant_id"])


def downgrade() -> None:
    op.drop_index("ix_merchants_parent_merchant_id", table_name="merchants")
    op.drop_constraint("fk_merchants_parent_merchant_id", "merchants", type_="foreignkey")
    op.drop_column("merchants", "parent_merchant_id")
