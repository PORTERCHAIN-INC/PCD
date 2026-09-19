"""Drop Postgres ACL tables — SpiceDB owns authorization relationships."""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "z9a0b1c2d3e4"
down_revision: Union[str, None] = "y8z9a0b1c2d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index(op.f("ix_user_permission_overrides_user_id"), table_name="user_permission_overrides")
    op.drop_index("ix_user_permission_overrides_permission", table_name="user_permission_overrides")
    op.drop_index("ix_user_permission_overrides_user", table_name="user_permission_overrides")
    op.drop_table("user_permission_overrides")

    op.drop_index("ix_user_role_assignments_scope", table_name="user_role_assignments")
    op.drop_index("ix_user_role_assignments_role_key", table_name="user_role_assignments")
    op.drop_index(op.f("ix_user_role_assignments_user_id"), table_name="user_role_assignments")
    op.drop_table("user_role_assignments")


def downgrade() -> None:
    raise NotImplementedError("ACL tables are retired — restore from SpiceDB bootstrap, not Postgres")
