"""Shared pytest fixtures for API tests."""

from __future__ import annotations

import os

import pytest

from porterchain_api.db import SessionLocal, init_db


@pytest.fixture(scope="session")
def db_url() -> str:
    url = os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg://porterchain:porterchain@localhost:5432/porterchain",
    )
    if url.startswith("sqlite"):
        pytest.skip("SQLite is not supported for integration tests")
    return url


@pytest.fixture
def db(db_url: str):
    init_db()
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def settings():
    from porterchain_api.config import Settings

    return Settings(app_env="local", stripe_mock=True, jwt_secret="test-jwt-secret-local")
