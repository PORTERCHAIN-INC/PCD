"""Clerk JWT claims extracted after verification."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ClerkClaims:
    clerk_user_id: str
    email: str | None = None
    org_id: str | None = None
    org_role: str | None = None
    phone: str | None = None
    public_metadata: dict[str, Any] | None = None
    session_id: str | None = None
    clerk_app: str | None = None
    # Phase 3 — framework-neutral identity fields (still populated by Clerk adapter)
    issuer: str | None = None
    authorized_party: str | None = None
    auth_time: int | None = None

    @property
    def metadata_role(self) -> str | None:
        if not self.public_metadata:
            return None
        role = self.public_metadata.get("role") or self.public_metadata.get("porterchain_role")
        return str(role) if role else None
