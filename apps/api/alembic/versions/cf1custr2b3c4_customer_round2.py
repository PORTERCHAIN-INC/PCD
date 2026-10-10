"""customer round 2: address book, notes, credits, deletion jobs, reorder nudges

Revision ID: cf1custr2b3c4
Revises: cf0fastbook1a2b
"""

import sqlalchemy as sa

from alembic import op

revision = "cf1custr2b3c4"
down_revision = "cf0fastbook1a2b"
branch_labels = None
depends_on = None


def _id() -> sa.Column:
    return sa.Column("id", sa.String(36), primary_key=True)


def _cust(nullable: bool = False) -> sa.Column:
    return sa.Column("customer_id", sa.String(36), sa.ForeignKey("customers.id", ondelete="CASCADE"), nullable=nullable)


def _created() -> sa.Column:
    return sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)


def upgrade() -> None:
    op.create_table(
        "customer_addresses",
        _id(),
        _cust(),
        sa.Column("address_key", sa.String(128), nullable=False),
        sa.Column("label", sa.String(64)),
        sa.Column("formatted", sa.String(512), nullable=False),
        sa.Column("postal", sa.String(16)),
        sa.Column("lat", sa.Float()),
        sa.Column("lng", sa.Float()),
        sa.Column("place_id", sa.String(255)),
        sa.Column("contact_name", sa.String(255)),
        sa.Column("phone", sa.String(32)),
        sa.Column("saved", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("use_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_used_at", sa.DateTime(timezone=True)),
        _created(),
    )
    op.create_index("ix_customer_addresses_customer_id", "customer_addresses", ["customer_id"])
    op.create_index("ix_customer_addresses_customer_key", "customer_addresses", ["customer_id", "address_key"], unique=True)

    op.create_table(
        "customer_notes",
        _id(),
        _cust(),
        sa.Column("author", sa.String(255), nullable=False),
        sa.Column("body", sa.String(2000), nullable=False),
        _created(),
    )
    op.create_index("ix_customer_notes_customer_id", "customer_notes", ["customer_id"])

    op.create_table(
        "customer_credits",
        _id(),
        _cust(),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="CAD"),
        sa.Column("reason", sa.String(500), nullable=False),
        sa.Column("order_id", sa.String(36)),
        sa.Column("actor", sa.String(255), nullable=False),
        _created(),
    )
    op.create_index("ix_customer_credits_customer_id", "customer_credits", ["customer_id"])

    op.create_table(
        "privacy_deletion_jobs",
        _id(),
        sa.Column("customer_id", sa.String(36)),
        sa.Column("reference", sa.String(64), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="pending_review"),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("plan", sa.JSON(), nullable=False),
        sa.Column("result", sa.JSON()),
        sa.Column("reviewer", sa.String(255)),
        sa.Column("review_note", sa.String(1000)),
        sa.Column("due_at", sa.DateTime(timezone=True)),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.Column("executed_at", sa.DateTime(timezone=True)),
        _created(),
    )
    op.create_index("ix_privacy_deletion_jobs_customer_id", "privacy_deletion_jobs", ["customer_id"])
    op.create_index("ix_privacy_deletion_jobs_reference", "privacy_deletion_jobs", ["reference"], unique=True)
    op.create_index("ix_privacy_deletion_jobs_status", "privacy_deletion_jobs", ["status"])

    op.create_table(
        "reorder_nudges",
        _id(),
        _cust(),
        sa.Column("order_id", sa.String(36), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="draft"),
        sa.Column("reason", sa.String(255), nullable=False),
        sa.Column("approved_by", sa.String(255)),
        _created(),
        sa.Column("decided_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_reorder_nudges_customer_id", "reorder_nudges", ["customer_id"])
    op.create_index("ix_reorder_nudges_status", "reorder_nudges", ["status"])
    op.create_index("ix_reorder_nudges_customer_order", "reorder_nudges", ["customer_id", "order_id"], unique=True)


def downgrade() -> None:
    for table in ("reorder_nudges", "privacy_deletion_jobs", "customer_credits", "customer_notes", "customer_addresses"):
        op.drop_table(table)
