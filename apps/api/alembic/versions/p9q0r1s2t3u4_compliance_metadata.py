"""Order compliance metadata + driver medical transport cert (§8.1.2 · §8.1.5)."""

from alembic import op
import sqlalchemy as sa

revision = "p9q0r1s2t3u4"
down_revision = "o3p4q5r6s7t8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("compliance_metadata", sa.JSON(), nullable=True))
    op.add_column(
        "drivers",
        sa.Column("medical_transport_certified", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("drivers", "medical_transport_certified")
    op.drop_column("orders", "compliance_metadata")
