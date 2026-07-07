"""Session and refresh token models — Clerk handles web sessions; Porterchain issues driver tokens."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class TokenPair:
    access_token: str
    refresh_token: str
    expires_at: datetime


@dataclass(frozen=True)
class SessionTokens:
    """JWT session envelope for Porterchain-issued tokens (driver API)."""

    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in_seconds: int = 3600
