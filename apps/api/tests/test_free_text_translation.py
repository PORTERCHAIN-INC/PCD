"""Merchant/customer free text is queued and translated to English for admin."""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime

import httpx
import pytest

from porterchain_api.admin_models import Claim  # noqa: F401
from porterchain_api.booking_models import Order
from porterchain_api.domain.states import OrderState
from porterchain_api.platform import free_text_translation as FT
from tests.test_collections_bl import _merchant


def _order(db, **kw) -> Order:
    m = _merchant(db)
    o = Order(merchant_id=m.id, state=OrderState.DISPATCH_READY.value, amount_cents=1000, currency="cad",
              order_number=f"TR-{uuid.uuid4().hex[:8].upper()}", tracking_number=f"TRK{uuid.uuid4().hex[:10]}",
              pickup=kw.pop("pickup", {"formatted": "a"}), dropoff=kw.pop("dropoff", {"formatted": "b"}),
              scheduled_at=datetime.now(UTC), **kw)
    db.add(o)
    db.flush()
    return o


def _rows(db, oid):
    return {r.field: r for r in db.query(FT.FreeTextTranslation).filter_by(entity_type="order", entity_id=oid)}


def test_order_free_text_is_queued_with_original(db) -> None:
    o = _order(db, special_instructions="Laisser au comptoir", dropoff={"formatted": "b", "notes": "Sonner deux fois"})
    rows = _rows(db, o.id)
    assert rows["special_instructions"].original == "Laisser au comptoir"
    assert rows["special_instructions"].status == "pending"
    assert rows["dropoff.notes"].original == "Sonner deux fois"
    # Editing the text re-queues it.
    o.special_instructions = "Appeler en arrivant"
    db.flush()
    r = _rows(db, o.id)["special_instructions"]
    assert r.original == "Appeler en arrivant" and r.status == "pending"


def test_empty_text_not_queued(db) -> None:
    o = _order(db, special_instructions="  ")
    assert _rows(db, o.id) == {}


def test_worker_translates_and_admin_label(db, monkeypatch) -> None:
    o = _order(db, special_instructions="Laisser au comptoir", dropoff={"formatted": "b", "notes": "Ring twice"})
    db.commit()

    def fake(url, text):
        return ("en", None) if text == "Ring twice" else ("fr", "Leave at the counter")

    monkeypatch.setattr(FT, "translate_text", fake)
    FT.translate_pending(db, "http://lt.invalid")
    items = {i["field"]: i for i in FT.for_entity(db, "order", o.id)}
    si = items["special_instructions"]
    assert si["original"] == "Laisser au comptoir"
    assert si["source_lang"] == "fr" and si["translated_en"] == "Leave at the counter"
    assert si["label"] == "Translated from French"
    assert items["dropoff.notes"]["status"] == "same" and items["dropoff.notes"]["label"] is None


def test_failures_retry_then_stop(db, monkeypatch) -> None:
    o = _order(db, special_instructions="Bonjour")
    db.commit()

    def boom(url, text):
        raise httpx.ConnectError("down")

    monkeypatch.setattr(FT, "translate_text", boom)
    for _ in range(FT.MAX_ATTEMPTS + 2):
        FT.translate_pending(db, "http://lt.invalid")
    r = _rows(db, o.id)["special_instructions"]
    assert r.status == "failed" and r.attempts == FT.MAX_ATTEMPTS and r.original == "Bonjour"


def test_no_url_skips(db) -> None:
    assert FT.translate_pending(db, "") == {"skipped": 1}


LT = os.environ.get("PCD_TEST_TRANSLATE_URL", "http://127.0.0.1:58090")


def _lt_up() -> bool:
    try:
        return httpx.get(LT + "/languages", timeout=2).status_code == 200
    except Exception:
        return False


@pytest.mark.skipif(not _lt_up(), reason="local LibreTranslate not running")
def test_real_libretranslate_fr_to_en() -> None:
    lang, en = FT.translate_text(LT, "Veuillez laisser le colis à la réception, merci.")
    assert lang == "fr"
    assert en and "reception" in en.lower()
    assert FT.translate_text(LT, "Please leave the parcel at reception.")[0] == "en"
