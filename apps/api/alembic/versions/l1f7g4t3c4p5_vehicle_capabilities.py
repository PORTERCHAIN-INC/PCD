"""vehicles.capabilities (shared equipment flags, e.g. liftgate)

Revision ID: l1f7g4t3c4p5
Revises: m1i2n3t4e5r6
"""

import sqlalchemy as sa
from alembic import op

revision = "l1f7g4t3c4p5"
down_revision = "m1i2n3t4e5r6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("vehicles", sa.Column("capabilities", sa.JSON(), nullable=False, server_default="[]"))


def downgrade() -> None:
    op.drop_column("vehicles", "capabilities")
