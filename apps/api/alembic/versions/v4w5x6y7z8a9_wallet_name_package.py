"""P0c — customer full_name, package barcode/label/proof pointers."""

from alembic import op
import sqlalchemy as sa

revision = "v4w5x6y7z8a9"
down_revision = "u3v4w5x6y7z8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("customers", sa.Column("full_name", sa.String(length=255), nullable=True))
    op.execute(
        sa.text(
            """
            UPDATE customers
            SET full_name = initcap(split_part(email, '@', 1))
            WHERE full_name IS NULL AND email IS NOT NULL AND email <> ''
            """
        )
    )

    op.add_column("packages", sa.Column("barcode", sa.String(length=64), nullable=True))
    op.add_column("packages", sa.Column("label_url", sa.String(length=512), nullable=True))
    op.add_column(
        "packages",
        sa.Column("signature_required", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column("packages", sa.Column("fleetbase_entity_id", sa.String(length=128), nullable=True))
    op.add_column("packages", sa.Column("fleetbase_proof_id", sa.String(length=128), nullable=True))
    op.create_index("ix_packages_barcode", "packages", ["barcode"], unique=True)
    op.create_index("ix_packages_fleetbase_entity_id", "packages", ["fleetbase_entity_id"])
    op.execute(
        sa.text(
            """
            UPDATE packages
            SET barcode = tracking_suffix
            WHERE barcode IS NULL AND tracking_suffix IS NOT NULL
            """
        )
    )


def downgrade() -> None:
    op.drop_index("ix_packages_fleetbase_entity_id", table_name="packages")
    op.drop_index("ix_packages_barcode", table_name="packages")
    op.drop_column("packages", "fleetbase_proof_id")
    op.drop_column("packages", "fleetbase_entity_id")
    op.drop_column("packages", "signature_required")
    op.drop_column("packages", "label_url")
    op.drop_column("packages", "barcode")
    op.drop_column("customers", "full_name")
