"""GAP-08 / driver PushService — FCM register/unregister (no emulator required)."""

from __future__ import annotations

import pytest

from porterchain_api.notification_engine.device_service import InvalidFcmToken


def _valid_fcm(suffix: str = "drv") -> str:
    return f"430248198034:APA91{suffix}" + ("z" * 120)


def test_gap08_push_service_rejects_expo_token(db, driver) -> None:
    from porterchain_driver.push import PushService

    with pytest.raises(InvalidFcmToken):
        PushService().register_device(
            db,
            driver,
            device_token="ExponentPushToken[xxxxxxxxxxxxxxxxxxxxxx]",
            platform="expo",
        )
    db.rollback()


def test_gap08_push_service_register_and_unregister(db, driver) -> None:
    from porterchain_driver.push import PushService

    svc = PushService()
    token = _valid_fcm()
    registered = svc.register_device(db, driver, device_token=token, platform="android")
    assert registered["registered"] is True
    assert registered["device_id"]
    assert registered["device_count"] >= 1

    unreg = svc.unregister_device(db, driver, device_token=token)
    assert unreg["unregistered"] is True
    assert unreg["scope"] == "token"

    unreg_all = svc.unregister_device(db, driver, device_token=None)
    assert unreg_all["unregistered"] is True
    db.rollback()
