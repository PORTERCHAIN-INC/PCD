"""L124: webhook verification accepts any secret in a comma-separated rotation list."""

import hashlib
import hmac
import json
import time
from types import SimpleNamespace

import pytest

from porterchain_api.services.stripe_service import construct_webhook_event


def _sig(payload: bytes, secret: str) -> str:
    t = int(time.time())
    mac = hmac.new(secret.encode(), f"{t}.".encode() + payload, hashlib.sha256).hexdigest()
    return f"t={t},v1={mac}"


PAYLOAD = json.dumps({"id": "evt_test", "object": "event", "type": "ping", "data": {"object": {}}}).encode()


@pytest.mark.parametrize("which", ["whsec_new", "whsec_cli"])
def test_any_listed_secret_verifies(which):
    s = SimpleNamespace(stripe_webhook_secret="whsec_new, whsec_cli")
    ev = construct_webhook_event(PAYLOAD, _sig(PAYLOAD, which), s)
    assert ev["id"] == "evt_test"


def test_retired_secret_rejected():
    s = SimpleNamespace(stripe_webhook_secret="whsec_new")
    with pytest.raises(Exception) as ei:
        construct_webhook_event(PAYLOAD, _sig(PAYLOAD, "whsec_old"), s)
    assert "ignature" in type(ei.value).__name__ + str(ei.value)
