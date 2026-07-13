"""Add cover_image_url to blog_posts."""

from alembic import op
import sqlalchemy as sa

revision = "u4v5w6x7y8z9"
down_revision = "t3u4v5w6x7y8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "blog_posts",
        sa.Column("cover_image_url", sa.String(length=1024), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("blog_posts", "cover_image_url")
