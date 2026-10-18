"""Blog: retire fictional authors and unpublish the unverified case study.

Revision ID: bf0focusauth1a2b
Revises: cw0corrwide0001

Upgrade (Oct 2026 website truth pass, approved by Ravi):
  * posts by "peter-porter", "sarah-chen" and "marcus-okonkwo" move to "porterchain";
  * those three author rows are deleted; the house author is renamed "PorterChain team";
  * the case study "case-study-construction-distributor-gta" (every locale) goes back to draft.

Every changed value is copied into ``blog_focus_oct2026_backup`` first, so ``downgrade``
restores the exact previous state (author rows, each post's author_id and status).
"""

from __future__ import annotations

import json

import sqlalchemy as sa

from alembic import op

revision = "bf0focusauth1a2b"
down_revision = "cw0corrwide0001"
branch_labels = None
depends_on = None

FICTIONAL_AUTHOR_IDS = ("peter-porter", "sarah-chen", "marcus-okonkwo")
HOUSE_AUTHOR_ID = "porterchain"
HOUSE_AUTHOR = {
    "name": "PorterChain team",
    "role": "Editorial",
    "bio": "Practical guides from the PorterChain team in the GTA.",
}
CASE_STUDY_SLUG = "case-study-construction-distributor-gta"
BACKUP_TABLE = "blog_focus_oct2026_backup"


def _in_clause(column: str, values: tuple[str, ...]) -> tuple[str, dict[str, str]]:
    names = [f"v{i}" for i in range(len(values))]
    return f"{column} IN ({', '.join(':' + n for n in names)})", dict(
        zip(names, values)
    )


def upgrade() -> None:
    bind = op.get_bind()
    op.create_table(
        BACKUP_TABLE,
        sa.Column("kind", sa.String(length=32), primary_key=True),
        sa.Column("ref", sa.String(length=64), primary_key=True),
        sa.Column("payload", sa.Text(), nullable=False),
    )
    backup = sa.table(
        BACKUP_TABLE,
        sa.column("kind", sa.String),
        sa.column("ref", sa.String),
        sa.column("payload", sa.Text),
    )
    rows: list[dict[str, str]] = []

    author_ids = (*FICTIONAL_AUTHOR_IDS, HOUSE_AUTHOR_ID)
    clause, params = _in_clause("id", author_ids)
    for aid, name, role, bio in bind.execute(
        sa.text(f"SELECT id, name, role, bio FROM blog_authors WHERE {clause}"), params
    ):
        rows.append(
            {
                "kind": "author",
                "ref": aid,
                "payload": json.dumps({"name": name, "role": role, "bio": bio}),
            }
        )

    clause, params = _in_clause("author_id", FICTIONAL_AUTHOR_IDS)
    for post_id, author_id in bind.execute(
        sa.text(f"SELECT id, author_id FROM blog_posts WHERE {clause}"), params
    ):
        rows.append({"kind": "post_author", "ref": post_id, "payload": author_id})

    for post_id, status in bind.execute(
        sa.text(
            "SELECT id, status FROM blog_posts WHERE slug = :slug AND status <> 'draft'"
        ),
        {"slug": CASE_STUDY_SLUG},
    ):
        rows.append({"kind": "post_status", "ref": post_id, "payload": status})

    if rows:
        op.bulk_insert(backup, rows)

    bind.execute(
        sa.text(f"UPDATE blog_posts SET author_id = :house WHERE {clause}"),
        {"house": HOUSE_AUTHOR_ID, **params},
    )
    bind.execute(
        sa.text("UPDATE blog_posts SET status = 'draft' WHERE slug = :slug"),
        {"slug": CASE_STUDY_SLUG},
    )
    clause, params = _in_clause("id", FICTIONAL_AUTHOR_IDS)
    bind.execute(sa.text(f"DELETE FROM blog_authors WHERE {clause}"), params)
    bind.execute(
        sa.text(
            "UPDATE blog_authors SET name = :name, role = :role, bio = :bio WHERE id = :id"
        ),
        {"id": HOUSE_AUTHOR_ID, **HOUSE_AUTHOR},
    )


def downgrade() -> None:
    bind = op.get_bind()
    saved = list(
        bind.execute(sa.text(f"SELECT kind, ref, payload FROM {BACKUP_TABLE}"))
    )

    for kind, ref, payload in saved:
        if kind != "author":
            continue
        data = json.loads(payload)
        exists = bind.execute(
            sa.text("SELECT 1 FROM blog_authors WHERE id = :id"), {"id": ref}
        ).first()
        if exists:
            bind.execute(
                sa.text(
                    "UPDATE blog_authors SET name = :name, role = :role, bio = :bio WHERE id = :id"
                ),
                {"id": ref, **data},
            )
        else:
            bind.execute(
                sa.text(
                    "INSERT INTO blog_authors (id, name, role, bio) VALUES (:id, :name, :role, :bio)"
                ),
                {"id": ref, **data},
            )

    for kind, ref, payload in saved:
        if kind == "post_author":
            bind.execute(
                sa.text("UPDATE blog_posts SET author_id = :author WHERE id = :id"),
                {"author": payload, "id": ref},
            )
        elif kind == "post_status":
            bind.execute(
                sa.text("UPDATE blog_posts SET status = :status WHERE id = :id"),
                {"status": payload, "id": ref},
            )

    op.drop_table(BACKUP_TABLE)
