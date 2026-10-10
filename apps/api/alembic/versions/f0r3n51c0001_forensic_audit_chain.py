"""forensic_audit_chain (hash-chained, append-only) + forensic_checkpoints

Revision ID: f0r3n51c0001
Revises: l1f7g4t3c4p5
"""

import sqlalchemy as sa
from alembic import op

revision = "f0r3n51c0001"
down_revision = "l1f7g4t3c4p5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "forensic_audit_chain",
        sa.Column("seq", sa.BigInteger(), primary_key=True, autoincrement=False),
        sa.Column("at", sa.String(40), nullable=False),
        sa.Column("category", sa.String(32), nullable=False, index=True),
        sa.Column("action", sa.String(128), nullable=False, index=True),
        sa.Column("actor", sa.String(128)),
        sa.Column("target_type", sa.String(64)),
        sa.Column("target_id", sa.String(128)),
        sa.Column("ip", sa.String(64)),
        sa.Column("outcome", sa.String(16), nullable=False),
        sa.Column("source", sa.String(48), nullable=False),
        sa.Column("detail", sa.JSON(), nullable=False),
        sa.Column("prev_hash", sa.String(64), nullable=False),
        sa.Column("hash", sa.String(64), nullable=False, unique=True),
    )
    op.create_table(
        "forensic_checkpoints",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("seq", sa.BigInteger(), nullable=False),
        sa.Column("head_hash", sa.String(64), nullable=False),
        sa.Column("key_id", sa.String(32), nullable=False),
        sa.Column("algorithm", sa.String(16), nullable=False),
        sa.Column("signature", sa.Text(), nullable=False),
    )
    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            """
            CREATE OR REPLACE FUNCTION forensic_append_only() RETURNS trigger AS $$
            BEGIN
              RAISE EXCEPTION 'forensic audit tables are append-only (% on %)', TG_OP, TG_TABLE_NAME;
            END $$ LANGUAGE plpgsql;
            """
        )
        for t in ("forensic_audit_chain", "forensic_checkpoints"):
            op.execute(f"CREATE TRIGGER {t}_no_update BEFORE UPDATE OR DELETE ON {t} "
                       "FOR EACH ROW EXECUTE FUNCTION forensic_append_only();")
            op.execute(f"CREATE TRIGGER {t}_no_truncate BEFORE TRUNCATE ON {t} "
                       "FOR EACH STATEMENT EXECUTE FUNCTION forensic_append_only();")


def downgrade() -> None:
    # Evidence tables are never dropped by a downgrade.
    pass
