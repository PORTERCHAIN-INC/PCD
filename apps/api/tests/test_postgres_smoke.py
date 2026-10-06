"""PostgreSQL smoke tests — Alembic schema, connectivity, CRM JSON queries."""

from __future__ import annotations

import os

import pytest
from sqlalchemy import inspect, text

from porterchain_api.admin_engine.crm_sales_service import CrmSalesService
from porterchain_api.db import SessionLocal, engine, init_db


@pytest.fixture(scope="module")
def db_url() -> str:
    url = os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg://porterchain:porterchain@localhost:5432/porterchain",
    )
    if url.startswith("sqlite"):
        pytest.skip("SQLite is not supported")
    return url


def test_database_url_is_postgresql(db_url: str) -> None:
    assert db_url.startswith("postgresql")


def test_init_db_connectivity() -> None:
    init_db()


def test_core_tables_exist() -> None:
    names = set(inspect(engine).get_table_names())
    required = {
        "orders",
        "customers",
        "quotes",
        "booking_drafts",
        "merchants",
        "crm_leads",
        "crm_companies",
        "domain_events",
        "alembic_version",
    }
    missing = required - names
    assert not missing, f"Missing tables: {missing}"


def test_transaction_rollback() -> None:
    with SessionLocal() as db:
        db.execute(text("SELECT 1"))
        db.rollback()


def test_crm_json_query_postgresql() -> None:
    svc = CrmSalesService()
    with SessionLocal() as db:
        svc.list_companies(db, city="Toronto", limit=5)


def test_performance_indexes_present() -> None:
    indexes = {idx["name"] for idx in inspect(engine).get_indexes("crm_companies")}
    assert "ix_crm_companies_address_gin" in indexes
