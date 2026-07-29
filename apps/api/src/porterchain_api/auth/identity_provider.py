"""IdentityProvider protocol — PorterChain must not couple call sites to Clerk objects."""

from __future__ import annotations

from typing import Protocol

from porterchain_api.auth.identity import AuthenticatedIdentity
from porterchain_api.config import Settings


class IdentityProvider(Protocol):
    async def authenticate_bearer(self, token: str, settings: Settings) -> AuthenticatedIdentity:
        """Verify token and return a framework-neutral identity. Raises HTTPException on failure."""
        ...
