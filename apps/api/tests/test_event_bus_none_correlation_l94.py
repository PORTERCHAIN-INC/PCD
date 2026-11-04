"""L94: a missing correlation_id must reach the router as None, not the string "None"."""
from porterchain_event_bus.bus import EventBus


def test_parse_treats_legacy_none_string_as_none() -> None:
    env = EventBus._parse_stream_fields({"event_type": "merchant.suspended", "correlation_id": "None", "actor_id": "None"})
    assert env["correlation_id"] is None


def test_parse_empty_is_none() -> None:
    assert EventBus._parse_stream_fields({"correlation_id": ""})["correlation_id"] is None


def test_publish_encodes_none_as_empty() -> None:
    sent: dict = {}

    class R:
        def xadd(self, key, fields, **kw):  # noqa: ANN001, ANN003
            sent.update(fields)

    bus = EventBus.__new__(EventBus)
    bus._redis_client = R()  # type: ignore[attr-defined]
    try:
        bus.publish({"event_id": "e1", "event_type": "merchant.suspended", "correlation_id": None, "payload": {}})
    except Exception:  # noqa: BLE001 - local dispatch parts are not under test
        pass
    assert sent.get("correlation_id") == ""
