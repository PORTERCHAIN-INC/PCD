"""Driver JWT session issuance."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from jose import jwt

from porterchain_shared.auth.session import SessionTokens

DRIVER_TOKEN_AUD = "porterchain-driver"
ACCESS_TTL_SECONDS = 3600
REFRESH_TTL_SECONDS = 86400 * 30


def issue_driver_session(driver_id: str, *, secret: str, email: str | None = None) -> SessionTokens:
    now = datetime.now(UTC)
    access_payload = {
        "sub": driver_id,
        "aud": DRIVER_TOKEN_AUD,
        "type": "access",
        "driver_id": driver_id,
        "email": email,
        "iat": now,
        "exp": now + timedelta(seconds=ACCESS_TTL_SECONDS),
    }
    refresh_payload = {
        "sub": driver_id,
        "aud": DRIVER_TOKEN_AUD,
        "type": "refresh",
        "driver_id": driver_id,
        "iat": now,
        "exp": now + timedelta(seconds=REFRESH_TTL_SECONDS),
    }
    return SessionTokens(
        access_token=jwt.encode(access_payload, secret, algorithm="HS256"),
        refresh_token=jwt.encode(refresh_payload, secret, algorithm="HS256"),
        expires_in_seconds=ACCESS_TTL_SECONDS,
    )


def decode_driver_token(token: str, *, secret: str, token_type: str = "access") -> dict:
    payload = jwt.decode(token, secret, algorithms=["HS256"], audience=DRIVER_TOKEN_AUD)
    if payload.get("type") != token_type:
        raise ValueError("invalid_token_type")
    return payload
