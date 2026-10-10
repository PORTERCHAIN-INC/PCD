"""Shared X-Ingest-Key verification for public website ingest routes."""

from fastapi import HTTPException

from porterchain_api.config import Settings
from porterchain_api.platform.secret_compare import secrets_match


def verify_public_ingest_key(settings: Settings, x_ingest_key: str | None) -> None:
    key = settings.public_ingest_api_key.strip()
    if not key:
        if settings.app_env == "local":
            return
        raise HTTPException(status_code=503, detail="ingest_not_configured")
    if not secrets_match(x_ingest_key, key):
        raise HTTPException(status_code=401, detail="invalid_ingest_key")
