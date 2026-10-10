"""Interac e-Transfer email parsing + sender authenticity (pure, no DB)."""

from __future__ import annotations

import email
from email import policy
from pathlib import Path

import pytest

from porterchain_api.billing_engine.interac.auth import verify_interac_sender
from porterchain_api.billing_engine.interac.matcher import normalize_name
from porterchain_api.billing_engine.interac.parser import NotInteracEmail, parse_interac_email
from porterchain_api.billing_engine.invoice_numbering import new_reference_code, normalize_reference

FIX = Path(__file__).parent / "fixtures" / "interac"
AUTHSERV = "mx.zohomail.com"


def load(name: str, **subs: str):
    raw = (FIX / name).read_text(encoding="utf-8")
    defaults = {
        "MSGID": "msg-1",
        "SENDER": "ACME WIDGETS INC.",
        "AMOUNT": "1,130.00",
        "AMOUNT_FR": "1 130,00",
        "MEMO": "PC-4F7K2 thanks",
        "IREF": "CA1MRf8Gk2Lp",
    }
    defaults.update(subs)
    for k, v in defaults.items():
        raw = raw.replace("{" + k + "}", v)
    return email.message_from_bytes(raw.encode("utf-8"), policy=policy.compat32)


def test_autodeposit_english():
    p = parse_interac_email(load("autodeposit_en.eml"))
    assert p.kind == "autodeposit"
    assert p.amount_cents == 113000
    assert p.currency == "cad"
    assert p.sender_name == "ACME WIDGETS INC"
    assert p.memo == "PC-4F7K2 thanks"
    assert p.interac_reference == "CA1MRf8Gk2Lp"
    assert p.message_id == "<msg-1@payments.interac.ca>"
    assert p.received_at is not None


def test_notification_english_not_yet_deposited():
    p = parse_interac_email(load("notification_en.eml", AMOUNT="250.00", MEMO="invoice"))
    assert p.kind == "notification"
    assert p.amount_cents == 25000
    assert p.memo == "invoice"


def test_autodeposit_french():
    p = parse_interac_email(load("autodeposit_fr.eml", SENDER="BOULANGERIE ST-DENIS"))
    assert p.kind == "autodeposit"
    assert p.amount_cents == 113000
    assert p.sender_name == "BOULANGERIE ST-DENIS"
    assert p.interac_reference == "CA1MRf8Gk2Lp"
    assert normalize_reference(p.memo) == "PC-4F7K2"


def test_not_interac_is_ignored():
    with pytest.raises(NotInteracEmail):
        parse_interac_email(load("not_interac.eml"))


def test_genuine_interac_passes_auth():
    for name in ("autodeposit_en.eml", "notification_en.eml", "autodeposit_fr.eml"):
        verdict = verify_interac_sender(load(name), authserv_id=AUTHSERV)
        assert verdict.ok, (name, verdict.detail)


def test_spoofed_header_from_other_server_is_rejected():
    verdict = verify_interac_sender(load("spoofed.eml"), authserv_id=AUTHSERV)
    assert not verdict.ok


def test_lookalike_domain_is_rejected():
    verdict = verify_interac_sender(load("lookalike_domain.eml"), authserv_id=AUTHSERV)
    assert not verdict.ok
    assert verdict.detail.startswith("from_not_interac")


def test_wrong_authserv_id_is_untrusted():
    verdict = verify_interac_sender(load("autodeposit_en.eml"), authserv_id="mx.other.example")
    assert not verdict.ok
    assert verdict.detail == "no_trusted_auth_results"


@pytest.mark.parametrize(
    "memo,expected",
    [
        ("PC-4F7K2", "PC-4F7K2"),
        ("pc 4f7k2 oct invoice", "PC-4F7K2"),
        ("Payment for PC4F7K2", "PC-4F7K2"),
        ("INV-2026-000123", None),
        ("PC-20261009-ABC123", None),  # tracking number, not a payment reference
        (None, None),
    ],
)
def test_normalize_reference(memo, expected):
    assert normalize_reference(memo) == expected


def test_reference_codes_are_unambiguous():
    for _ in range(200):
        code = new_reference_code()
        assert code.startswith("PC-") and len(code) == 8
        assert not set(code[3:]) & set("01ILO")
        assert normalize_reference(code) == code


def test_normalize_name_strips_corporate_suffixes():
    assert normalize_name("ACME Widgets Inc.") == normalize_name("acme widgets")
    assert normalize_name("Boulangerie St-Denis Ltée") == "boulangerie st denis"
