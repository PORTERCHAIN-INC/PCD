"""P1 — addresses, stops, driver_documents, credit_notes."""

from alembic import op
import sqlalchemy as sa

revision = "w5x6y7z8a9b0"
down_revision = "v4w5x6y7z8a9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "addresses",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("formatted", sa.String(length=512), nullable=False),
        sa.Column("line1", sa.String(length=255), nullable=True),
        sa.Column("city", sa.String(length=128), nullable=True),
        sa.Column("region", sa.String(length=64), nullable=True),
        sa.Column("postal", sa.String(length=16), nullable=True),
        sa.Column("country", sa.String(length=8), nullable=False, server_default="CA"),
        sa.Column("lat", sa.Float(), nullable=True),
        sa.Column("lng", sa.Float(), nullable=True),
        sa.Column("place_id", sa.String(length=255), nullable=True),
        sa.Column("contact_name", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_addresses_postal", "addresses", ["postal"])

    op.create_table(
        "stops",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("order_id", sa.String(length=36), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("kind", sa.String(length=16), nullable=False, server_default="drop"),
        sa.Column("address_id", sa.String(length=36), nullable=True),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("fleetbase_stop_id", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["address_id"], ["addresses.id"]),
    )
    op.create_index("ix_stops_order_id", "stops", ["order_id"])
    op.create_index("ix_stops_kind", "stops", ["kind"])
    op.create_index("ix_stops_status", "stops", ["status"])
    op.create_index("ix_stops_address_id", "stops", ["address_id"])
    op.create_index("ix_stops_order_sequence", "stops", ["order_id", "sequence"])

    op.add_column("saved_addresses", sa.Column("address_id", sa.String(length=36), nullable=True))
    op.create_index("ix_saved_addresses_address_id", "saved_addresses", ["address_id"])
    op.create_foreign_key(
        "fk_saved_addresses_address_id",
        "saved_addresses",
        "addresses",
        ["address_id"],
        ["id"],
    )

    op.create_table(
        "driver_documents",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("driver_id", sa.String(length=36), nullable=False),
        sa.Column("doc_type", sa.String(length=64), nullable=False),
        sa.Column("label", sa.String(length=128), nullable=True),
        sa.Column("file_url", sa.String(length=512), nullable=True),
        sa.Column("reference_number", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending_review"),
        sa.Column("verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("uploaded_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["driver_id"], ["drivers.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_driver_documents_driver_id", "driver_documents", ["driver_id"])
    op.create_index("ix_driver_documents_doc_type", "driver_documents", ["doc_type"])
    op.create_index("ix_driver_documents_status", "driver_documents", ["status"])

    op.create_table(
        "credit_notes",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("merchant_id", sa.String(length=36), nullable=True),
        sa.Column("invoice_id", sa.String(length=36), nullable=True),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="open"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["merchant_id"], ["merchants.id"]),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"]),
    )
    op.create_index("ix_credit_notes_merchant_id", "credit_notes", ["merchant_id"])
    op.create_index("ix_credit_notes_invoice_id", "credit_notes", ["invoice_id"])
    op.create_index("ix_credit_notes_status", "credit_notes", ["status"])


def downgrade() -> None:
    op.drop_index("ix_credit_notes_status", table_name="credit_notes")
    op.drop_index("ix_credit_notes_invoice_id", table_name="credit_notes")
    op.drop_index("ix_credit_notes_merchant_id", table_name="credit_notes")
    op.drop_table("credit_notes")
    op.drop_index("ix_driver_documents_status", table_name="driver_documents")
    op.drop_index("ix_driver_documents_doc_type", table_name="driver_documents")
    op.drop_index("ix_driver_documents_driver_id", table_name="driver_documents")
    op.drop_table("driver_documents")
    op.drop_constraint("fk_saved_addresses_address_id", "saved_addresses", type_="foreignkey")
    op.drop_index("ix_saved_addresses_address_id", table_name="saved_addresses")
    op.drop_column("saved_addresses", "address_id")
    op.drop_index("ix_stops_order_sequence", table_name="stops")
    op.drop_index("ix_stops_address_id", table_name="stops")
    op.drop_index("ix_stops_status", table_name="stops")
    op.drop_index("ix_stops_kind", table_name="stops")
    op.drop_index("ix_stops_order_id", table_name="stops")
    op.drop_table("stops")
    op.drop_index("ix_addresses_postal", table_name="addresses")
    op.drop_table("addresses")
