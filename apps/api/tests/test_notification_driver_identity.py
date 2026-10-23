"""Audit day 4 #1: driver identity in the notification API comes from the token only.

A customer or merchant Clerk token with forged ``X-Porterchain-Portal: driver`` +
``X-Driver-Id`` must be rejected (403) for inbox read, preferences update and push
device registration. The real driver keeps working, and a driver cannot use the
header to reach another driver's inbox.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from porterchain_api.admin_models import AdminUser, Driver
from porterchain_api.auth.clerk import ClerkClaims
from porterchain_api.booking_models import Customer
from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db
from porterchain_api.merchant_models import Merchant, MerchantUser
from porterchain_api.routers import notifications

VICTIM_DRIVER_ID = "drv-victim"
OWN_DRIVER_ID = "drv-own"


def _rows() -> dict:
    return {
        Driver: [
            Driver(id=VICTIM_DRIVER_ID, clerk_user_id="clerk_victim", email="v@example.com", full_name="V"),
            Driver(id=OWN_DRIVER_ID, clerk_user_id="clerk_driver", email="d@example.com", full_name="D"),
        ],
        Customer: [Customer(id="cust-1", clerk_user_id="clerk_customer")],
        MerchantUser: [],
        Merchant: [],
        AdminUser: [],
    }


class _Query:
    def __init__(self, rows: list) -> None:
        self._rows = rows

    def filter(self, *conds):
        rows = self._rows
        for cond in conds:
            key = getattr(getattr(cond, "left", None), "key", None)
            value = getattr(getattr(cond, "right", None), "value", None)
            if key is not None:
                rows = [r for r in rows if getattr(r, key, None) == value]
        return _Query(rows)

    def order_by(self, *_a):
        return self

    def first(self):
        return self._rows[0] if self._rows else None

    def all(self):
        return list(self._rows)


class _FakeDb:
    def __init__(self) -> None:
        self.rows = _rows()

    def query(self, model):
        return _Query(self.rows.get(model, []))

    def commit(self) -> None: ...
    def rollback(self) -> None: ...


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(notifications.router)
    fake = _FakeDb()
    app.dependency_overrides[get_db] = lambda: fake
    app.dependency_overrides[get_settings] = lambda: Settings(app_env="local", clerk_dev_bypass=False, jwt_secret="test-jwt-secret-local")
    device = MagicMock(id="dev-1")
    pref = MagicMock(category="jobs", email_enabled=True, push_enabled=False, sms_enabled=False, in_app_enabled=True)
    with (
        patch(
            "porterchain_api.notification_engine.principal._notification_pre_sync",
            return_value=None,
        ),
        patch.object(notifications._engine, "inbox_payload", side_effect=lambda db, **kw: {"for": kw["user_id"], "role": kw["user_role"]}),
        patch.object(notifications._prefs, "upsert", return_value=pref) as upsert,
        patch.object(notifications._devices, "register", return_value=device) as register,
    ):
        c = TestClient(app)
        c.upsert = upsert
        c.register = register
        yield c


def _as(clerk_user_id: str):
    return patch(
        "porterchain_api.auth.clerk.verify_clerk_token",
        new_callable=AsyncMock,
        return_value=ClerkClaims(clerk_user_id=clerk_user_id, email=f"{clerk_user_id}@example.com"),
    )


def _forged(driver_id: str = VICTIM_DRIVER_ID) -> dict:
    return {
        "Authorization": "Bearer tok",
        "X-Porterchain-Portal": "driver",
        "X-Driver-Id": driver_id,
    }


CALLS = [
    ("get", "/v1/notifications/inbox", None),
    ("patch", "/v1/notifications/preferences", {"category": "jobs", "push_enabled": False}),
    ("post", "/v1/notifications/devices/register", {"fcm_token": "attacker-device-token", "platform": "ios"}),
]


@pytest.mark.parametrize("attacker", ["clerk_customer", "clerk_merchant_user"])
@pytest.mark.parametrize("method,path,body", CALLS)
def test_non_driver_with_forged_driver_header_is_403(client, attacker, method, path, body) -> None:
    with _as(attacker):
        res = client.request(method, path, headers=_forged(), json=body)
    assert res.status_code == 403
    client.upsert.assert_not_called()
    client.register.assert_not_called()


@pytest.mark.parametrize("method,path,body", CALLS)
def test_driver_cannot_target_another_driver(client, method, path, body) -> None:
    with _as("clerk_driver"):
        res = client.request(method, path, headers=_forged(VICTIM_DRIVER_ID), json=body)
    assert res.status_code == 403
    client.upsert.assert_not_called()
    client.register.assert_not_called()


@pytest.mark.parametrize("with_header", [True, False])
def test_real_driver_still_works(client, with_header) -> None:
    headers = _forged(OWN_DRIVER_ID) if with_header else {
        "Authorization": "Bearer tok",
        "X-Porterchain-Portal": "driver",
    }
    with _as("clerk_driver"):
        inbox = client.get("/v1/notifications/inbox", headers=headers)
        prefs = client.patch("/v1/notifications/preferences", headers=headers, json={"category": "jobs"})
        dev = client.post(
            "/v1/notifications/devices/register", headers=headers, json={"fcm_token": "driver-token"}
        )
    assert inbox.status_code == 200
    assert inbox.json() == {"for": OWN_DRIVER_ID, "role": "driver"}
    assert prefs.status_code == 200
    assert client.upsert.call_args.kwargs["user_id"] == OWN_DRIVER_ID
    assert dev.status_code == 200
    assert client.register.call_args.kwargs["user_id"] == OWN_DRIVER_ID
    assert client.register.call_args.kwargs["user_role"] == "driver"


def test_customer_without_driver_header_still_gets_own_inbox(client) -> None:
    with _as("clerk_customer"):
        res = client.get("/v1/notifications/inbox", headers={"Authorization": "Bearer tok"})
    assert res.status_code == 200
    assert res.json() == {"for": "cust-1", "role": "customer"}
