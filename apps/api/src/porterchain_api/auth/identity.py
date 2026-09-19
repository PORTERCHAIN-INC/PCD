"""Framework-neutral authenticated identity (IdP-agnostic)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AuthenticatedIdentity:
    """Minimum claims needed for PorterChain identity resolution — no Clerk types."""

    provider: str
    issuer: str | None
    subject: str
    session_id: str | None = None
    email: str | None = None
    email_verified: bool | None = None
    auth_time: int | None = None
    authorized_party: str | None = None
    # Opaque adapter hints (e.g. which Clerk app JWKS matched) — never used for authz
    adapter_context: dict[str, Any] | None = None
