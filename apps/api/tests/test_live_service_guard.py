"""The pytest guard refuses settings that point at the live dev stack."""

from __future__ import annotations

from tests.conftest import (
    TEST_DATABASE_URL,
    TEST_REDIS_URL,
    TEST_SPICEDB_ENDPOINT,
    live_service_violations,
)


def test_test_container_defaults_are_allowed() -> None:
    env = {
        "DATABASE_URL": TEST_DATABASE_URL,
        "REDIS_URL": TEST_REDIS_URL,
        "SPICEDB_ENDPOINT": TEST_SPICEDB_ENDPOINT,
    }
    assert live_service_violations(env) == []


def test_live_ports_and_hosts_are_refused() -> None:
    env = {
        "DATABASE_URL": "postgresql+psycopg://porterchain:porterchain@localhost:5432/porterchain",
        "REDIS_URL": "redis://localhost:6379/0",
        "SPICEDB_ENDPOINT": "localhost:50051",
    }
    assert len(live_service_violations(env)) == 3
    assert live_service_violations({"REDIS_URL": "redis://porterchain-redis:56379/0"})
    assert live_service_violations({"REDIS_URL": "redis://localhost/0"})


def test_local_stack_and_other_ports_are_refused() -> None:
    # ~/pcd-local stack Postgres (55632) must never receive test rows.
    assert live_service_violations(
        {"DATABASE_URL": "postgresql+psycopg://porterchain:x@127.0.0.1:55632/porterchain"}
    )
    assert live_service_violations({"DATABASE_URL": "postgresql+psycopg://u:p@db.example.com:55432/x"})
    assert live_service_violations({"REDIS_URL": "redis://127.0.0.1:6380/0"})


def test_running_session_uses_test_containers() -> None:
    assert live_service_violations() == []
