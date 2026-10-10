"""Mobile security audit events — client telemetry (no secrets)."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from porterchain_api.auth.driver import _driver_id_from_token
from porterchain_api.auth.dev import allow_auth_dev_bypass
from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db
from porterchain_api.schemas_public import SecurityAuditBatch, SecurityAuditEvent

logger = logging.getLogger("porterchain.security.audit")

router = APIRouter(prefix="/v1/security", tags=["security"])


def _resolve_actor(
  db: Session,
  settings: Settings,
  authorization: str | None,
) -> tuple[str, str | None]:
    if authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()
        try:
            driver_id = _driver_id_from_token(token, settings)
            return "driver", driver_id
        except Exception:
            pass
        if token == "dev" and allow_auth_dev_bypass(settings):
            return "clerk", "dev_clerk_user"
    return "anonymous", None


@router.post("/audit-events")
def ingest_audit_events(
    body: SecurityAuditBatch,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    authorization: Annotated[str | None, Header()] = None,
):
    actor_type, actor_id = _resolve_actor(db, settings, authorization)

    accepted = 0
    for event in body.events:
        logger.info(
            "mobile_security_event",
            extra={
                "event_type": event.event_type,
                "app_kind": event.app_kind,
                "actor_type": actor_type,
                "actor_id": actor_id,
                "occurred_at": event.occurred_at or datetime.now(UTC).isoformat(),
                "metadata": _sanitize(event.metadata),
            },
        )
        accepted += 1

    return {"accepted": accepted}


def _sanitize(metadata: dict[str, Any]) -> dict[str, Any]:
    blocked = {"token", "access_token", "refresh_token", "password", "pin", "secret"}
    return {k: v for k, v in metadata.items() if k.lower() not in blocked}

# Re-exports kept for existing importers (integration).
from porterchain_api.schemas_public import SecurityAuditEvent  # noqa: E402, F401
