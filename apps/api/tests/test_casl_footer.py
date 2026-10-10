from types import SimpleNamespace

from porterchain_api.notification_engine.unsubscribe import casl_footer

S = SimpleNamespace(unsubscribe_mailbox="unsubscribe@porterchain.com")


def test_transactional_untouched():
    assert casl_footer(S, {"category": "order"}, "Your parcel", "<p>x</p>", {}) == ("Your parcel", "<p>x</p>")


def test_marketing_gets_identity_and_link_from_header():
    h = {"List-Unsubscribe": "<https://api/u?t=1>, <mailto:u@x>"}
    t, html = casl_footer(S, {"category": "marketing"}, "Spring promo", "<p>Promo</p>", h)
    assert "https://api/u?t=1" in t and "PorterChain Logistics Inc." in t
    assert 'href="https://api/u?t=1"' in html


def test_falls_back_to_mailto_and_is_idempotent():
    t, _ = casl_footer(S, {"category": "crm"}, "Hi", None, {})
    assert "mailto:unsubscribe@porterchain.com" in t
    assert casl_footer(S, {"category": "crm"}, t, None, {})[0] == t
