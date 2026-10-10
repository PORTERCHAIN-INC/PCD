"""FastAPI deps: SpiceDB Check as authorization SoT."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from porterchain_api.auth.current_principal import CurrentPrincipal
from porterchain_api.auth.dependencies import require_authenticated
from porterchain_api.authz.client import get_authz_client
from porterchain_api.db import get_db
from porterchain_api.unified_identity_models import AccessAuditLog

logger = logging.getLogger("porterchain.security")


def require_relation(
    resource_type: str,
    permission: str,
    *,
    resource_id: str | None = None,
    resource_id_param: str | None = None,
) -> Callable:
    """Dependency factory: SpiceDB Check(user, permission, resource)."""

    async def _dependency(
        principal: Annotated[CurrentPrincipal, Depends(require_authenticated)],
        db: Session = Depends(get_db),
    ) -> CurrentPrincipal:
        rid = resource_id
        if not rid and resource_type == "platform":
            rid = "porterchain"
        if not rid:
            raise HTTPException(status_code=500, detail="authz_resource_id_missing")
        client = get_authz_client()
        try:
            allowed = client.check(
                resource_type=resource_type,
                resource_id=rid,
                permission=permission,
                subject_id=principal.user_id,
            )
        except Exception as exc:
            logger.exception("spicedb_check_failed")
            settings_required = True
            try:
                from porterchain_api.config import get_settings

                settings_required = bool(get_settings().spicedb_required)
            except Exception:  # noqa: BLE001
                pass
            if settings_required:
                raise HTTPException(status_code=503, detail="authz_unavailable") from exc
            raise HTTPException(status_code=403, detail="forbidden") from exc

        if allowed:
            return principal

        try:
            db.add(
                AccessAuditLog(
                    actor_user_id=principal.user_id,
                    action="spicedb.check.denied",
                    resource_type=resource_type,
                    resource_id=rid,
                    outcome="denied",
                    detail={"permission": permission},
                )
            )
            db.commit()
        except Exception:
            logger.exception("access_audit_write_failed")
            try:
                db.rollback()
            except Exception:  # noqa: BLE001
                pass
        raise HTTPException(status_code=403, detail="forbidden")

    _ = resource_id_param
    return _dependency


def check_or_raise(
    principal: CurrentPrincipal,
    *,
    resource_type: str,
    resource_id: str,
    permission: str,
    db: Session | None = None,
) -> None:
    client = get_authz_client()
    allowed = client.check(
        resource_type=resource_type,
        resource_id=resource_id,
        permission=permission,
        subject_id=principal.user_id,
    )
    if allowed:
        return
    if db is not None:
        try:
            db.add(
                AccessAuditLog(
                    actor_user_id=principal.user_id,
                    action="spicedb.check.denied",
                    resource_type=resource_type,
                    resource_id=resource_id,
                    outcome="denied",
                    detail={"permission": permission},
                )
            )
            db.commit()
        except Exception:
            logger.exception("access_audit_write_failed")
    raise HTTPException(status_code=403, detail="forbidden")
