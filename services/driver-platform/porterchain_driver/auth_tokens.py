"""Driver JWT session issuance."""

from __future__ import annotations

import jwt  # PyJWT (python-jose removed: unmaintained, open CVE)

DRIVER_TOKEN_AUD = "porterchain-driver"


def decode_driver_token(token: str, *, secret: str, token_type: str = "access") -> dict:
    payload = jwt.decode(token, secret, algorithms=["HS256"], audience=DRIVER_TOKEN_AUD)
    if payload.get("type") != token_type:
        raise ValueError("invalid_token_type")
    return payload
