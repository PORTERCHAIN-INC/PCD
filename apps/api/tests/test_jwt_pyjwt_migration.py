"""PyJWT migration (python-jose removed): driver HS256 tokens. Bearer RS256 verify → test_keycloak_auth.py."""

from __future__ import annotations

import time

import jwt
import pytest

from porterchain_driver.auth_tokens import DRIVER_TOKEN_AUD, decode_driver_token


def test_driver_token_roundtrip_and_audience():
    secret = "s" * 48
    now = int(time.time())
    good = jwt.encode({"driver_id": "d1", "type": "access", "aud": DRIVER_TOKEN_AUD, "exp": now + 60}, secret, algorithm="HS256")
    assert decode_driver_token(good, secret=secret)["driver_id"] == "d1"
    wrong_aud = jwt.encode({"driver_id": "d1", "type": "access", "aud": "x", "exp": now + 60}, secret, algorithm="HS256")
    with pytest.raises(jwt.PyJWTError):
        decode_driver_token(wrong_aud, secret=secret)
    refresh = jwt.encode({"driver_id": "d1", "type": "refresh", "aud": DRIVER_TOKEN_AUD, "exp": now + 60}, secret, algorithm="HS256")
    with pytest.raises(ValueError):
        decode_driver_token(refresh, secret=secret)
