"""bulk_import_jobs kind + job_config for route import v1."""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "bulk_import_jobs",
        sa.Column("kind", sa.String(length=32), nullable=False, server_default="classic"),
    )
    op.add_column("bulk_import_jobs", sa.Column("job_config", sa.JSON(), nullable=True))
    op.create_index("ix_bulk_import_jobs_kind", "bulk_import_jobs", ["kind"])


def downgrade() -> None:
    op.drop_index("ix_bulk_import_jobs_kind", table_name="bulk_import_jobs")
    op.drop_column("bulk_import_jobs", "job_config")
    op.drop_column("bulk_import_jobs", "kind")
