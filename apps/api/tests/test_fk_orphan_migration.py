"""dm2fkorphan0002: orphan rows are quarantined (never silently lost) before FKs are added,
and every new FK is enforced with the intended ON DELETE behaviour."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
import sqlalchemy as sa

from porterchain_api.db import engine

_PATH = (
    Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "dm2fkorphan0002_foreign_keys_with_orphan_quarantine.py"
)


def _mod():
    spec = importlib.util.spec_from_file_location("dm2fkorphan0002", _PATH)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def conn():
    with engine.connect() as c:
        tx = c.begin()
        if not c.exec_driver_sql("SELECT to_regclass('fk_orphan_quarantine')").scalar():
            tx.rollback()
            pytest.skip("test database not migrated to dm2fkorphan0002")
        try:
            yield c
        finally:
            tx.rollback()


def test_nullable_orphans_are_nulled_and_recorded(conn) -> None:
    mod = _mod()
    conn.exec_driver_sql("CREATE TABLE t_parent (id varchar(36) PRIMARY KEY)")
    conn.exec_driver_sql("CREATE TABLE t_child (id varchar(36) PRIMARY KEY, parent_id varchar(36) NULL)")
    conn.exec_driver_sql("INSERT INTO t_parent VALUES ('p1')")
    conn.exec_driver_sql("INSERT INTO t_child VALUES ('c1','p1'),('c2','ghost'),('c3',NULL)")
    n, action = mod.quarantine_orphans(conn, "t_child", "parent_id", "t_parent")
    assert (n, action) == (1, "nulled")
    assert dict(conn.exec_driver_sql("SELECT id, parent_id FROM t_child").all()) == {
        "c1": "p1",
        "c2": None,
        "c3": None,
    }
    q = conn.exec_driver_sql(
        "SELECT row_pk, bad_value, action, row_data->>'parent_id' FROM fk_orphan_quarantine WHERE table_name='t_child'"
    ).one()
    assert tuple(q) == ("c2", "ghost", "nulled", "ghost")


def test_not_null_orphans_are_moved_with_full_row(conn) -> None:
    mod = _mod()
    conn.exec_driver_sql("CREATE TABLE t_parent (id varchar(36) PRIMARY KEY)")
    conn.exec_driver_sql("CREATE TABLE t_child (id varchar(36) PRIMARY KEY, parent_id varchar(36) NOT NULL, note text)")
    conn.exec_driver_sql("INSERT INTO t_parent VALUES ('p1')")
    conn.exec_driver_sql("INSERT INTO t_child VALUES ('c1','p1','ok'),('c2','ghost','keep me')")
    n, action = mod.quarantine_orphans(conn, "t_child", "parent_id", "t_parent")
    assert (n, action) == (1, "moved")
    assert [r[0] for r in conn.exec_driver_sql("SELECT id FROM t_child").all()] == ["c1"]
    data = conn.exec_driver_sql(
        "SELECT row_data FROM fk_orphan_quarantine WHERE table_name='t_child'"
    ).scalar_one()
    assert data == {"id": "c2", "parent_id": "ghost", "note": "keep me"}


def test_cascade_nullable_orphans_are_moved_not_nulled(conn) -> None:
    """Rehearsal finding: nulling pricing_fsa_rates.merchant_id turns a deleted merchant's
    private rate into a platform-wide rate. CASCADE children must be moved out instead."""
    mod = _mod()
    conn.exec_driver_sql("CREATE TABLE t_parent (id varchar(36) PRIMARY KEY)")
    conn.exec_driver_sql("CREATE TABLE t_child (id varchar(36) PRIMARY KEY, parent_id varchar(36) NULL)")
    conn.exec_driver_sql("INSERT INTO t_child VALUES ('c1','ghost'),('c2',NULL)")
    assert mod.quarantine_orphans(conn, "t_child", "parent_id", "t_parent", "CASCADE") == (1, "moved")
    assert [r[0] for r in conn.exec_driver_sql("SELECT id FROM t_child").all()] == ["c2"]


def test_restrict_orphans_are_only_reported(conn) -> None:
    mod = _mod()
    conn.exec_driver_sql("CREATE TABLE t_parent (id varchar(36) PRIMARY KEY)")
    conn.exec_driver_sql("CREATE TABLE t_child (id varchar(36) PRIMARY KEY, parent_id varchar(36) NULL)")
    conn.exec_driver_sql("INSERT INTO t_child VALUES ('c1','ghost')")
    assert mod.quarantine_orphans(conn, "t_child", "parent_id", "t_parent", "RESTRICT") == (1, "reported")
    assert conn.exec_driver_sql("SELECT parent_id FROM t_child").scalar_one() == "ghost"


def test_orphan_action_table() -> None:
    f = _mod().orphan_action
    assert f(False, "SET NULL") == "nulled"
    assert f(True, "SET NULL") == "moved"
    assert f(False, "CASCADE") == "moved"
    assert f(False, "RESTRICT") == f(True, "RESTRICT") == "reported"


def test_every_planned_fk_exists_with_its_on_delete_rule(conn) -> None:
    mod = _mod()
    rules = {"a": "NO ACTION", "r": "RESTRICT", "c": "CASCADE", "n": "SET NULL"}
    rows = conn.execute(
        sa.text(
            "SELECT conrelid::regclass::text, a.attname, confrelid::regclass::text, confdeltype "
            "FROM pg_constraint c JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = c.conkey[1] "
            "WHERE c.contype = 'f' AND c.convalidated"
        )
    ).all()
    have = {(t, col): (tgt, rules[d]) for t, col, tgt, d in rows}
    for table, column, target, ondelete in mod.FKS:
        assert have.get((table, column)) == (target, ondelete), (table, column)
