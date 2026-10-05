"""Zepto bounce webhook parsing."""

from porterchain_api.notification_engine.bounce import extract_bounced_addresses, is_bounce_event


def test_zepto_hard_bounce_address() -> None:
    body = {
        "event_name": ["hardbounce"],
        "event_message": [
            {"email_info": {"to": [{"email_address": {"address": "Door@Example.com"}}]}}
        ],
    }
    assert is_bounce_event(body)
    assert extract_bounced_addresses(body) == ["door@example.com"]


def test_delivered_event_is_not_a_bounce() -> None:
    assert is_bounce_event({"event_name": ["delivered"], "email": "a@b.com"}) is False
