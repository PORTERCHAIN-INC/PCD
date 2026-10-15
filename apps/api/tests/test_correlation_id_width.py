"""correlation_id must fit composite ids like "<uuid>:<hex>" (was VARCHAR(36))."""

import pytest
from fastapi import HTTPException

from porterchain_api.booking_models import DomainEvent, OrderEvent


def test_correlation_id_columns_fit_composite_ids() -> None:
    composite = "329464f5-6733-45cd-a4bc-da81c9c8d39e:38470f57"
    assert len(composite) > 36
    for model in (DomainEvent, OrderEvent):
        assert model.__table__.c.correlation_id.type.length >= len(composite)
        assert model.__table__.c.correlation_id.type.length == 128


def test_zeptomail_webhook_fails_closed_without_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    from porterchain_api.routers import zeptomail_webhook as wh

    class _S:
        zeptomail_webhook_secret = ""

    monkeypatch.setattr(wh, "get_settings", lambda: _S())
    with pytest.raises(HTTPException) as exc:
        wh.zeptomail_event({"event_name": ["hardbounce"]}, db=None, x_porterchain_mail_webhook=None)
    assert exc.value.status_code == 503


def test_zeptomail_webhook_rejects_wrong_key(monkeypatch: pytest.MonkeyPatch) -> None:
    from porterchain_api.routers import zeptomail_webhook as wh

    class _S:
        zeptomail_webhook_secret = "right-key"

    monkeypatch.setattr(wh, "get_settings", lambda: _S())
    with pytest.raises(HTTPException) as exc:
        wh.zeptomail_event({"event_name": ["hardbounce"]}, db=None, x_porterchain_mail_webhook="wrong")
    assert exc.value.status_code == 401
    # Right key + non-tracked event short-circuits before touching the DB.
    assert wh.zeptomail_event({"event_name": ["unknown"]}, db=None, x_porterchain_mail_webhook="right-key")["ok"]
