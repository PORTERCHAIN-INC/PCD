"""Shopify orders with ambiguous/failed shipping addresses are held, not booked on a guess."""

from __future__ import annotations

import pytest

from porterchain_api.merchant_engine import shopify_address_review as rev
from porterchain_api.merchant_engine import shopify_order_sync as sync


class _Res:
    def __init__(self, status: str):
        self.status = status

    def to_dict(self):
        return {
            "status": self.status,
            "candidates": [{"formatted": "x", "lat": 43.7, "lng": -79.4}] * 2,
        }


ADDR = {"address1": "100 Main St", "city": "Toronto", "zip": "", "country_code": "CA"}


@pytest.fixture
def on(monkeypatch):
    monkeypatch.setenv("GEO_RESOLVE_SHOPIFY", "1")


@pytest.mark.parametrize(
    "status,held",
    [
        ("ambiguous", True),
        ("failed", True),
        ("confident", False),
        ("approximate", False),
    ],
)
def test_needs_review_by_status(on, monkeypatch, status, held):
    monkeypatch.setattr(
        "porterchain_api.geo_resolve.resolve_address", lambda *a, **k: _Res(status)
    )
    assert (rev.needs_review(dict(ADDR)) is not None) is held


def test_shopify_coords_trusted(on, monkeypatch):
    monkeypatch.setattr(
        "porterchain_api.geo_resolve.resolve_address", lambda *a, **k: _Res("ambiguous")
    )
    assert rev.needs_review({**ADDR, "latitude": 43.7, "longitude": -79.4}) is None


def test_kill_switch(monkeypatch):
    monkeypatch.setenv("GEO_RESOLVE_SHOPIFY", "0")
    monkeypatch.setattr(
        "porterchain_api.geo_resolve.resolve_address", lambda *a, **k: _Res("ambiguous")
    )
    assert rev.needs_review(dict(ADDR)) is None


def test_resolver_crash_does_not_hold(on, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("photon down")

    monkeypatch.setattr("porterchain_api.geo_resolve.resolve_address", boom)
    assert rev.needs_review(dict(ADDR)) is None


def test_apply_choice_pins_point():
    out = rev.apply_choice({"shipping_address": dict(ADDR)}, lat=43.8, lng=-79.3)
    assert out["shipping_address"]["latitude"] == 43.8
    assert rev.needs_review(out["shipping_address"]) is None


def test_ledger_reason_and_flag():
    status, reason, _ = sync.classify({"ok": True, "skipped": rev.HOLD_REASON})
    assert (status, reason) == ("not_booked", "address_needs_review")
    assert "address_needs_review" in sync.REASON_TEXT


def test_book_now_pins_picked_point(monkeypatch):
    class Row:
        source = "webhook"

    class Shop:
        shop_domain = "x.myshopify.com"

    seen = {}
    monkeypatch.setattr(
        sync,
        "_fetch_payload",
        lambda *a: (Row(), Shop(), {"shipping_address": dict(ADDR)}),
    )

    def fake_process(db, settings, **kw):
        seen.update(kw)
        return {"ok": True}

    monkeypatch.setattr(
        "porterchain_api.merchant_engine.shopify_webhooks.process_order_payload",
        fake_process,
    )
    sync.book_now(None, None, "m1", "s1", lat=43.8, lng=-79.3)
    body = seen["body"]
    assert body["_force_book"] is True
    assert body["shipping_address"]["latitude"] == 43.8
