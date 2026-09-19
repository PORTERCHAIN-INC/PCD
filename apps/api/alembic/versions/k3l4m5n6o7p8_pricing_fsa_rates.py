"""FSA-based flat rates (postal-code pricing for Shopify and merchant channels)."""

from alembic import op
import sqlalchemy as sa

revision = "k3l4m5n6o7p8"
down_revision = "j2k3l4m5n6o7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pricing_fsa_rates",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("merchant_id", sa.String(length=36), nullable=True),
        # NULL on any of these three means "any" — see PricingFsaRate.
        sa.Column("origin_fsa", sa.String(length=3), nullable=True),
        sa.Column("dest_fsa", sa.String(length=3), nullable=False),
        sa.Column("vehicle_class", sa.String(length=32), nullable=True),
        sa.Column("flat_cents", sa.Integer(), nullable=False),
        sa.Column("includes_location_fees", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("label", sa.String(length=128), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("config", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_pricing_fsa_rates_merchant_id", "pricing_fsa_rates", ["merchant_id"])
    op.create_index("ix_pricing_fsa_rates_dest_fsa", "pricing_fsa_rates", ["dest_fsa"])
    op.create_index("ix_pricing_fsa_rates_is_active", "pricing_fsa_rates", ["is_active"])
    op.create_index(
        "uq_pricing_fsa_rates_scope",
        "pricing_fsa_rates",
        ["merchant_id", "origin_fsa", "dest_fsa", "vehicle_class"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_pricing_fsa_rates_scope", table_name="pricing_fsa_rates")
    op.drop_index("ix_pricing_fsa_rates_is_active", table_name="pricing_fsa_rates")
    op.drop_index("ix_pricing_fsa_rates_dest_fsa", table_name="pricing_fsa_rates")
    op.drop_index("ix_pricing_fsa_rates_merchant_id", table_name="pricing_fsa_rates")
    op.drop_table("pricing_fsa_rates")
