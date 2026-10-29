"""G20 A-SHR-06 data: PCDC demo seed is idempotent, sandbox-only, and refuses live DBs."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location("seed_pcdc", Path(__file__).resolve().parents[1] / "scripts/seed_pcdc_demo.py")
seed_pcdc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(seed_pcdc)  # type: ignore[union-attr]


@pytest.mark.parametrize("url", [
    "postgresql+psycopg://u:p@127.0.0.1:5432/porterchain",
    "postgresql+psycopg://u:p@db.example.com:55432/x",
    "",
])
def test_guard_refuses_live_or_remote(url: str) -> None:
    with pytest.raises(SystemExit):
        seed_pcdc.guard(url)


def test_guard_allows_test_container() -> None:
    seed_pcdc.guard("postgresql+psycopg://u:p@127.0.0.1:55432/porterchain_test")


def test_seed_is_idempotent_and_sandbox(db) -> None:
    from porterchain_api.booking_models import Order

    a = seed_pcdc.seed(db)
    b = seed_pcdc.seed(db)
    assert a["merchant_id"] == b["merchant_id"] and b["demo_orders"] == 3
    orders = db.query(Order).filter(Order.merchant_id == b["merchant_id"]).all()
    assert len(orders) == 3 and all(o.is_sandbox for o in orders)
