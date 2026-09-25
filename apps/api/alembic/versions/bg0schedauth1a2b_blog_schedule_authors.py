"""Merge heads; blog scheduled_publish_at + blog_authors.

Revision ID: bg0schedauth1a2b
Revises: v5w6x7y8z9a0, au0clerknull1a2b
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "bg0schedauth1a2b"
down_revision = ("v5w6x7y8z9a0", "au0clerknull1a2b")
branch_labels = None
depends_on = None

_SEED_AUTHORS = (
    (
        "porterchain",
        "Porterchain Team",
        "Editorial",
        "Insights from the Porterchain commercial logistics team.",
    ),
    (
        "peter-porter",
        "Peter Porter",
        "Founder & CEO",
        "Building Canada's most trusted commercial logistics partner for local businesses.",
    ),
    (
        "sarah-chen",
        "Sarah Chen",
        "Head of Dispatch Operations",
        "Operations leader focused on SLA execution, route planning, and partner network quality.",
    ),
    (
        "marcus-okonkwo",
        "Marcus Okonkwo",
        "Principal Engineer",
        "Engineering lead for routing, tracking systems, and delivery operations reliability.",
    ),
)


def upgrade() -> None:
    op.create_table(
        "blog_authors",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("role", sa.String(length=256), nullable=False, server_default=""),
        sa.Column("bio", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.add_column(
        "blog_posts",
        sa.Column("scheduled_publish_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_blog_posts_scheduled_publish_at",
        "blog_posts",
        ["scheduled_publish_at"],
    )

    authors = sa.table(
        "blog_authors",
        sa.column("id", sa.String),
        sa.column("name", sa.String),
        sa.column("role", sa.String),
        sa.column("bio", sa.Text),
    )
    op.bulk_insert(
        authors,
        [
            {"id": aid, "name": name, "role": role, "bio": bio}
            for aid, name, role, bio in _SEED_AUTHORS
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_blog_posts_scheduled_publish_at", table_name="blog_posts")
    op.drop_column("blog_posts", "scheduled_publish_at")
    op.drop_table("blog_authors")
