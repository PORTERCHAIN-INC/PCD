"""Custom merchant price: flat price per parcel, any size (Ravi 2026-11-03)."""

import sqlalchemy as sa
from alembic import op

revision = "cp9flat01"
down_revision = "fpc01fleetcontracts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("pricing_org_pricing", sa.Column("flat_parcel_cents", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("pricing_org_pricing", "flat_parcel_cents")
