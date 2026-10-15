"""booking_attachments + booking_attachment_events (pickup / delivery documents)."""

import sqlalchemy as sa
from alembic import op

revision = "ba0attach0001"
down_revision = "md0dedupe0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "booking_attachments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("order_id", sa.String(36), sa.ForeignKey("orders.id"), nullable=True, index=True),
        sa.Column("merchant_id", sa.String(36), nullable=True, index=True),
        sa.Column("customer_id", sa.String(36), nullable=True, index=True),
        sa.Column("stop", sa.String(16), nullable=False, server_default="pickup"),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(64), nullable=False),
        sa.Column("size_bytes", sa.Integer, nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("content", sa.LargeBinary, nullable=True),
        sa.Column("note", sa.String(500), nullable=True),
        sa.Column("required_at_stop", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("location_key", sa.String(255), nullable=True, index=True),
        sa.Column("is_location_template", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("source_template_id", sa.String(36), nullable=True),
        sa.Column("uploaded_by", sa.String(128), nullable=True),
        sa.Column("first_viewed_by_driver_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("shown_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("shown_by_driver_id", sa.String(36), nullable=True),
        sa.Column("proof_content", sa.LargeBinary, nullable=True),
        sa.Column("proof_content_type", sa.String(64), nullable=True),
        sa.Column("link_token_hash", sa.String(64), nullable=True, index=True),
        sa.Column("link_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("purged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "booking_attachment_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("attachment_id", sa.String(36), nullable=False, index=True),
        sa.Column("order_id", sa.String(36), nullable=True, index=True),
        sa.Column("actor_type", sa.String(16), nullable=False),
        sa.Column("actor_id", sa.String(128), nullable=True),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("payload", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("booking_attachment_events")
    op.drop_table("booking_attachments")
