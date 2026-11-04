"""G11 (doc 60 §1, R9): merchants pay by Interac only; card checkout is retail only."""

from __future__ import annotations

import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from porterchain_api.booking_engine import payment_service as ps

REPO = Path(__file__).resolve().parents[3]
API = REPO / "apps/api/src/porterchain_api"
CARD = re.compile("st" + "ripe", re.I)

MERCHANT_PATHS = [
    API / "routers/merchant",
    API / "routers/merchant_api.py",
    API / "routers/merchant_ops.py",
    API / "routers/merchants.py",
    API / "routers/merchants_integrations.py",
    API / "merchant_engine",
    API / "schemas_merchant.py",
    API / "billing_engine/merchant_service.py",
    API / "admin_engine/merchant_org.py",
    API / "platform/merchant_billing.py",
    REPO / "apps/merchant-portal/src",
]


def _files(p: Path):
    if p.is_file():
        yield p
        return
    for f in p.rglob("*"):
        if f.is_file() and f.suffix in {".py", ".ts", ".tsx"} and "node_modules" not in f.parts:
            yield f


def test_no_card_processor_reference_in_merchant_paths() -> None:
    hits = [str(f.relative_to(REPO)) for p in MERCHANT_PATHS for f in _files(p) if CARD.search(f.read_text())]
    assert hits == []


class _Q:
    def __init__(self, row):
        self._row = row

    def filter(self, *a, **k):
        return self

    def first(self):
        return self._row


class _DB:
    def __init__(self, order, invoice=None):
        self._rows = [order, invoice]

    def query(self, *a):
        return _Q(self._rows.pop(0))


def test_merchant_quote_detected() -> None:
    q = SimpleNamespace(id="q1")
    assert ps._is_merchant_quote(_DB(SimpleNamespace(id="o1", merchant_id="m1")), q) is True
    assert ps._is_merchant_quote(_DB(SimpleNamespace(id="o1", merchant_id=None), ("inv",)), q) is True
    assert ps._is_merchant_quote(_DB(SimpleNamespace(id="o1", merchant_id=None), None), q) is False
    assert ps._is_merchant_quote(_DB(None), q) is False


def test_start_payment_refuses_merchant_quote(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ps, "_is_merchant_quote", lambda db, quote: True)
    with pytest.raises(ValueError, match="merchant_pays_by_interac"):
        ps.PaymentService().start_payment(None, None, SimpleNamespace(id="q"), SimpleNamespace(id="c"))  # type: ignore[arg-type]
