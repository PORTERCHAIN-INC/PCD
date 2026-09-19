"""Merchant pricing_model column — SoT for fsa|distance (not JSON auto)."""

from alembic import op
import sqlalchemy as sa

revision = "s1t2u3v4w5x6"
down_revision = "r0s1t2u3v4w5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "merchants",
        sa.Column("pricing_model", sa.String(length=16), nullable=False, server_default="distance"),
    )
    op.execute(
        """
        UPDATE merchants
        SET pricing_model = CASE
            WHEN pricing_config->>'pricing_model' IN ('fsa', 'distance')
            THEN pricing_config->>'pricing_model'
            ELSE 'distance'
        END
        """
    )
    op.execute(
        """
        UPDATE merchants
        SET pricing_config = (pricing_config::jsonb - 'pricing_model')::json
        WHERE pricing_config IS NOT NULL
          AND pricing_config::jsonb ? 'pricing_model'
        """
    )
    op.create_index("ix_merchants_pricing_model", "merchants", ["pricing_model"])
    op.create_check_constraint(
        "ck_merchants_pricing_model",
        "merchants",
        "pricing_model IN ('fsa', 'distance')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_merchants_pricing_model", "merchants", type_="check")
    op.drop_index("ix_merchants_pricing_model", table_name="merchants")
    op.drop_column("merchants", "pricing_model")
