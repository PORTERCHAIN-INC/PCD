"""Fleet partner contracts (manual fixed-rate contracts for contractor fleets) + free-text translations."""

import sqlalchemy as sa
from alembic import op

revision = "fpc01fleetcontracts"
down_revision = "hst743reg01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "fleet_partner_contracts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("partner_id", sa.String(36), sa.ForeignKey("logistics_partners.id", ondelete="CASCADE"), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("rate_basis", sa.String(16), nullable=False),
        sa.Column("rate_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("min_charge_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(8), nullable=False, server_default="cad"),
        sa.Column("document_ref", sa.String(255), nullable=True),
        sa.Column("notes", sa.String(2000), nullable=True),
        sa.Column("is_dummy", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_fleet_partner_contracts_partner_id", "fleet_partner_contracts", ["partner_id"])
    op.create_table(
        "free_text_translations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("entity_type", sa.String(48), nullable=False),
        sa.Column("entity_id", sa.String(64), nullable=False),
        sa.Column("field", sa.String(64), nullable=False),
        sa.Column("original", sa.Text(), nullable=False),
        sa.Column("source_lang", sa.String(8), nullable=True),
        sa.Column("translated_en", sa.Text(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("translated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("entity_type", "entity_id", "field", name="uq_free_text_translations_target"),
    )
    op.create_index("ix_free_text_translations_status", "free_text_translations", ["status"])


def downgrade() -> None:
    op.drop_index("ix_free_text_translations_status", table_name="free_text_translations")
    op.drop_table("free_text_translations")
    op.drop_index("ix_fleet_partner_contracts_partner_id", table_name="fleet_partner_contracts")
    op.drop_table("fleet_partner_contracts")
