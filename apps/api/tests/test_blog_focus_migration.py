"""bf0focusauth1a2b: fictional authors retired and case study unpublished, fully reversible."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations

_PATH = (
    Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "bf0focusauth1a2b_blog_retire_fictional_authors.py"
)


def _load():
    spec = importlib.util.spec_from_file_location("bf0focusauth1a2b", _PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _seed(conn) -> None:
    conn.execute(
        sa.text(
            "CREATE TABLE blog_authors (id VARCHAR(64) PRIMARY KEY, name VARCHAR(256) NOT NULL,"
            " role VARCHAR(256) NOT NULL DEFAULT '', bio TEXT NOT NULL DEFAULT '')"
        )
    )
    conn.execute(
        sa.text(
            "CREATE TABLE blog_posts (id VARCHAR(36) PRIMARY KEY, slug VARCHAR(160), locale VARCHAR(8),"
            " author_id VARCHAR(64), status VARCHAR(32))"
        )
    )
    for aid, name in [
        ("porterchain", "Porterchain Team"),
        ("peter-porter", "Peter Porter"),
        ("sarah-chen", "Sarah Chen"),
        ("marcus-okonkwo", "Marcus Okonkwo"),
    ]:
        conn.execute(
            sa.text(
                "INSERT INTO blog_authors (id, name, role, bio) VALUES (:i, :n, 'r', 'b')"
            ),
            {"i": aid, "n": name},
        )
    for pid, slug, author, status in [
        ("p1", "same-day-b2b-delivery-toronto", "peter-porter", "published"),
        ("p2", "fleet-overflow-capacity-gta", "sarah-chen", "published"),
        (
            "p3",
            "case-study-construction-distributor-gta",
            "marcus-okonkwo",
            "published",
        ),
        ("p4", "case-study-construction-distributor-gta", "porterchain", "published"),
        ("p5", "wholesale-distribution-gta", "porterchain", "draft"),
    ]:
        conn.execute(
            sa.text(
                "INSERT INTO blog_posts (id, slug, locale, author_id, status)"
                " VALUES (:i, :s, 'en', :a, :st)"
            ),
            {"i": pid, "s": slug, "a": author, "st": status},
        )


def _state(conn):
    authors = dict(conn.execute(sa.text("SELECT id, name FROM blog_authors")).all())
    posts = {
        r[0]: (r[1], r[2])
        for r in conn.execute(
            sa.text("SELECT id, author_id, status FROM blog_posts")
        ).all()
    }
    return authors, posts


def test_upgrade_retires_fictional_authors_and_downgrade_restores_everything() -> None:
    mig = _load()
    engine = sa.create_engine("sqlite://")
    with engine.begin() as conn:
        _seed(conn)
        before = _state(conn)
        ctx = MigrationContext.configure(conn)
        with Operations.context(ctx):
            mig.upgrade()
        authors, posts = _state(conn)
        assert authors == {"porterchain": "PorterChain team"}
        assert {a for a, _ in posts.values()} == {"porterchain"}
        assert posts["p3"][1] == "draft" and posts["p4"][1] == "draft"
        assert posts["p1"] == ("porterchain", "published")
        assert posts["p5"] == ("porterchain", "draft")

        with Operations.context(ctx):
            mig.downgrade()
        assert _state(conn) == before
        assert not sa.inspect(conn).has_table(mig.BACKUP_TABLE)
