"""Customer phone is released per tap, only for this driver's open order."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from porterchain_api.routers.driver import dispatch_route as dr


def _ctx():
    return SimpleNamespace(driver=SimpleNamespace(id="d1", status="approved"))


def _call(order, kind="drop"):
    with patch.object(dr, "require_approved_driver"), patch.object(
        dr.svc, "require_assigned_order", return_value=order
    ):
        return dr.dispatch_stop_contact("o1", _ctx(), db=None, kind=kind)


def test_open_order_returns_drop_phone_from_stop_list():
    order = SimpleNamespace(id="o1", state="IN_TRANSIT", pickup={"phone": "905-555-0100"},
                            dropoff={"stops": [{"contact_phone": "416 555 0199"}]})
    assert _call(order) == {"phone": "416 555 0199"}
    assert _call(order, kind="pickup") == {"phone": "905-555-0100"}


def test_closed_order_never_releases_the_number():
    order = SimpleNamespace(id="o1", state="DELIVERED", pickup={}, dropoff={"phone": "4165550199"})
    with pytest.raises(HTTPException) as e:
        _call(order)
    assert e.value.status_code == 409


def test_missing_phone_is_404():
    order = SimpleNamespace(id="o1", state="IN_TRANSIT", pickup={}, dropoff={"phone": "12"})
    with pytest.raises(HTTPException) as e:
        _call(order)
    assert e.value.status_code == 404
